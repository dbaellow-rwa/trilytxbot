# cd "C:\Users\dusti\OneDrive\Documents\GitHub\trilytxbot"
# streamlit run app.py
import os
import json
import pandas as pd
import streamlit as st
import altair as alt
from openai import OpenAI
from google.cloud import bigquery
from google.oauth2 import service_account
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from sources_of_truth.secret_manager_utils import get_secret

# ──────────────────────────────────────────────────────────────────────────────
# Load Credentials
# ──────────────────────────────────────────────────────────────────────────────



# def load_credentials():
#     from sources_of_truth.secret_manager_utils import get_secret
#     json_key_str = get_secret(secret_id="service-account-trilytx-key", project_id="trilytx")
#     json_key = json.loads(json_key_str)

#     credentials = service_account.Credentials.from_service_account_info(json_key)
#     openai_key = get_secret("openai_rwa_1", project_id="906828770740")
#     return credentials, json_key["project_id"], openai_key

def load_credentials():

    json_key_str = os.environ["GOOGLE_APPLICATION_CREDENTIALS_TRILYTX"]
    json_key = json.loads(json_key_str)
    credentials = service_account.Credentials.from_service_account_info(json_key)
    openai_key = os.environ["OPENAI_API_KEY"]
    return credentials, json_key["project_id"], openai_key

# ──────────────────────────────────────────────────────────────────────────────
# BigQuery Schema Loader
# ──────────────────────────────────────────────────────────────────────────────
def extract_table_schema(client, dataset_id: str, table_id: str) -> dict:
    table = client.get_table(f"{dataset_id}.{table_id}")
    return {
        "description": table.description or "",
        "fields": {field.name: field.description or str(field.field_type) for field in table.schema}
    }

# ──────────────────────────────────────────────────────────────────────────────
# SQL Generator using OpenAI
# ──────────────────────────────────────────────────────────────────────────────
def generate_sql_from_question(question: str, schema: dict, openai_key: str) -> str:
    client = OpenAI(api_key=openai_key)
    prompt = f"""
You are a SQL assistant for triathlon race data in BigQuery. Use standard SQL syntax compatible with Google BigQuery. Always use fully qualified table names (`project.dataset.table`) if not specified, and prefer `SAFE_CAST`, `DATE_DIFF`, `DATE_TRUNC`, and `QUALIFY` where appropriate.



Use the following BigQuery tables:

1. `trilytx_core.core_race_results`
Contains race-day performance results for individual athletes.

Important columns:
- athlete: Athlete’s full name (e.g., “LIONEL SANDERS”)
- athlete_slug: Lowercase, hyphenated version of the athlete's name
- place: Athlete’s finish position in the race (1, 2, 3, etc.)
- overall_seconds, overall_time: Total race time (in seconds and as HH:MM:SS)
- swim_time, bike_time, run_time: Segment times in string format
- swim_seconds, bike_seconds, run_seconds: Segment times in seconds
- distance: Full race distance label (e.g., "Half-Iron (70.3 miles)")
- category, gender: Gender classification
- race_name: lowercase-hyphenated version of the race name (e.g., nice-world-championships)
- unique_race_id, year, date: Race-level identifiers and timing
- tier: Tier classification (e.g., “Gold Tier”)
- sof: Strength of Field (numeric)
- organizer: Race organizer
- location: city/country (e.g. Miami, FL, United States, Buenos Aires, Argentina )

2. `trilytx_fct.fct_pto_scores_weekly`
Contains weekly PTO segment scores for each athlete by distance group and overall. The higher the score, the better the athlete..

Important columns:
- athlete_id: Unique identifier for the athlete
- athlete: Athlete’s full name (e.g., “LIONEL SANDERS”)
- athlete_slug: Lowercase, hyphenated version of the athlete's name (e.g., "lionel-sanders")
- gender: Athlete gender (e.g., "men")
- country: Country the athlete represents (e.g., "Canada")
- weight: Athlete weight (e.g., "73kg")
- height: Athlete height in meters (e.g., "1.77")
- age: Athlete age at the time of the report
- born: Athlete birth year
- reporting_week: Date of the week this score is reporting on (e.g., "2023-09-10") - Assume the user is asking for an up-to-date week if they do not specify. up-to-date means reporting_week = date_trunc(current_date(), week)
- distance_group: Race category (e.g., "Iron (140.6 miles)", "Half-Iron (70.3 miles)", "100 km", "Overall")
- swim_pto_score, bike_pto_score, run_pto_score, overall_pto_score: PTO segment scores. Higher is better.
- t1_pto_score, t2_pto_score: Transition segment scores
- rank_*: Ranking columns that compare this athlete’s score across different groupings (e.g., by distance, gender, country, birth year). These are useful for relative performance analysis.

You may join the two tables using `athlete_slug`. For time-based analysis, use `reporting_week` (weekly scores) or `date` (race day).

If a user references a location (like “Oceanside”), assume it refers to the full known location name such as “Oceanside, CA, United States” as found in the `location` or `race_name` columns. Prefer searching with `LIKE '%Oceanside%'` or matching known values like “Oceanside, CA, United States” from historical data.

If multiple races occurred there, include them all unless the user specifies a year or date.

When asking about race results, include information like the race name, gender, location, date, distance, organizer, overall time, etc. 
When returning information about an athlete, include name, year, country, and gender. 

If a question is asked about "half" or "70.3", use distance = 'Half-Iron (70.3 miles)', if they say "full" or "140.6" or "ironman", use distance = "Iron (140.6 miles)"


Your job:
Given the user question below, generate **only a valid BigQuery SQL query** using the table and columns above. Do **not** include explanations or comments.

User question:
{question}
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    sql = response.choices[0].message.content.strip()
    if "```sql" in sql:
        sql = sql.split("```sql")[-1].split("```")[0].strip()
    return sql

# ──────────────────────────────────────────────────────────────────────────────
# Execute SQL in BigQuery
# ──────────────────────────────────────────────────────────────────────────────
def run_bigquery(query: str, client: bigquery.Client) -> pd.DataFrame:
    return client.query(query).to_dataframe()

# ──────────────────────────────────────────────────────────────────────────────
# LLM-Based Result Summarizer
# ──────────────────────────────────────────────────────────────────────────────
def summarize_results(df: pd.DataFrame, openai_key: str, question: str) -> str:
    client = OpenAI(api_key=openai_key)
    prompt = f"""A user asked: \"{question}\".
Here are the results:

{df.to_markdown(index=False)}

Write a 2-4 sentence summary in plain English."""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
    )
    return response.choices[0].message.content.strip()

# ──────────────────────────────────────────────────────────────────────────────
# Streamlit App
# ──────────────────────────────────────────────────────────────────────────────


def main():
    st.set_page_config(page_title="Trilytx SQL Chatbot", layout="wide")
    st.title("🤖 Trilytx Chatbot")
    st.markdown("Ask a question about triathlon race data.")

    credentials, project_id, openai_key = load_credentials()
    bq_client = bigquery.Client(credentials=credentials, project=project_id)

    if not openai_key:
        st.error("Missing OpenAI API key.")
        return

    if "schema" not in st.session_state:
        st.session_state.schema = extract_table_schema(bq_client, "trilytx_core", "core_race_results")

    if "history" not in st.session_state:
        st.session_state.history = []

    if "votes" not in st.session_state:
        st.session_state.votes = []

    if "example_question" not in st.session_state:
        st.session_state.example_question = ""

    # ──────────────────────────────────────────────────────────────────────────────
    # Sidebar Filters
    # ──────────────────────────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("⚙️ Optional Filters")
        athlete_name = st.text_input("Filter by athlete", value="")
        distance_filter = st.selectbox("Distance type", ["", "Half-Iron (70.3 miles)", "Iron (140.6 miles)", "Olympic", "Sprint", "100 km"])

        st.markdown("---")
        st.subheader("💡 Try an Example")
        if st.button("How many wins does Lionel Sanders have in Oceanside?"):
            st.session_state.example_question = "How many wins does Lionel Sanders have in Oceanside?"
        if st.button("Who won the 70.3 world championship in 2024?"):
            st.session_state.example_question = "Who won the 70.3 world championship in 2024?"
        if st.button("Who is the top female cyclist today?"):
            st.session_state.example_question = "Who is the top female cyclist today?"

    # ──────────────────────────────────────────────────────────────────────────────
    # Main Input
    # ──────────────────────────────────────────────────────────────────────────────
    question = st.text_input("Ask your question", value=st.session_state.example_question)

    if st.button("Submit") and question:
        try:
            with st.spinner("Generating SQL and fetching results..."):
                filters_context = ""
                if athlete_name:
                    filters_context += f"\n- Athlete: {athlete_name}"
                if distance_filter:
                    filters_context += f"\n- Distance: {distance_filter}"

                augmented_question = f"{question}\n\n[Contextual Filters Applied]{filters_context if filters_context else ' None'}\n\nNote: The `athlete` column is stored in UPPERCASE."

                sql = generate_sql_from_question(augmented_question, st.session_state.schema, openai_key)
                df = run_bigquery(sql, bq_client)
                summary = summarize_results(df, openai_key, question)

                st.session_state.history.append((question, summary))

                tab1, tab2, tab3, tab4 = st.tabs(["🧠 Answer", "🧾 SQL", "📊 Results", "📈 Chart"])

                with tab1:
                    st.markdown("### 🧠 Answer")
                    st.write(summary)
                    st.metric("Rows Returned", len(df))
                    if "overall_seconds" in df.columns:
                        st.metric("Fastest Time (sec)", int(df["overall_seconds"].min()))
                    st.markdown("#### Was this answer helpful?")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("👍 Yes", key=f"up_{len(st.session_state.history)}"):
                            st.session_state.votes.append(("👍", question, summary))
                            st.success("Thanks for your feedback!")
                    with col2:
                        if st.button("👎 No", key=f"down_{len(st.session_state.history)}"):
                            st.session_state.votes.append(("👎", question, summary))
                            st.warning("Thanks for your feedback!")

                with tab2:
                    st.markdown("### 🧾 Generated SQL")
                    st.code(sql, language="sql")

                with tab3:
                    st.markdown("### 📊 Results")
                    st.dataframe(df)

                with tab4:
                    if "athlete" in df.columns and "overall_seconds" in df.columns:
                        st.markdown("### 📈 Chart: Athlete vs. Time")
                        chart = alt.Chart(df).mark_bar().encode(
                            x=alt.X("athlete:N", sort="-y"),
                            y="overall_seconds:Q",
                            tooltip=["athlete", "overall_seconds"]
                        ).properties(height=400)
                        st.altair_chart(chart, use_container_width=True)
                    else:
                        st.info("No chartable data in result.")
        except Exception as e:
            st.error(f"❌ Error: {e}")

    # ──────────────────────────────────────────────────────────────────────────────
    # History Viewer
    # ──────────────────────────────────────────────────────────────────────────────
    with st.expander("📜 Previous Questions"):
        for q, a in reversed(st.session_state.history):
            st.markdown(f"**Q:** {q}\n\n**A:** {a}")
    with st.expander("🗳️ Feedback Log"):
        if not st.session_state.votes:
            st.write("No feedback yet.")
        else:
            for vote, q, a in reversed(st.session_state.votes):
                st.markdown(f"{vote} on **Q:** _{q}_\n> {a[:200]}...")

if __name__ == "__main__":
    main()