# cd "C:\Users\dusti\OneDrive\Documents\GitHub\trilytxbot"
# streamlit run app.py
import os
import json
import pandas as pd
import streamlit as st
import altair as alt
import datetime
from openai import OpenAI
from google.cloud import bigquery
from google.oauth2 import service_account
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from sources_of_truth.secret_manager_utils import get_secret

# ──────────────────────────────────────────────────────────────────────────────
# Load Credentials
# ──────────────────────────────────────────────────────────────────────────────



USE_LOCAL = 1  # Set to 0 for pushing to production, 1 for local development

def load_credentials():
    if USE_LOCAL:
        from sources_of_truth.secret_manager_utils import get_secret
        json_key_str = get_secret(secret_id="service-account-trilytx-key", project_id="trilytx")
        json_key = json.loads(json_key_str)
        credentials = service_account.Credentials.from_service_account_info(json_key)
        openai_key = get_secret("openai_rwa_1", project_id="906828770740")
    else:
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
def generate_sql_from_question(question: str,  openai_key: str) -> str:
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
- distance: Full race distance label (e.g., "Half-Iron (70.3 miles)", "Iron (140.6 miles)", "Short course", "Other middle distances", "Other long distances", "100 km")
- category: race category
- gender: Athlete gender (e.g., "men" and "women")
- race_name: lowercase-hyphenated version of the race name (e.g., nice-world-championships, )
- unique_race_id, year, date: Race-level identifiers and timing
- tier: Tier classification (e.g., “Gold Tier”)
- sof: Strength of Field (numeric)
- organizer: Race organizer
- location: city/country (e.g. Miami, FL, United States, Buenos Aires, Argentina )


2. `trilytx_fct.fct_race_results_vs_predict`
Contains model-predicted triathlon race outcomes compared to actual race-day results, one row per athlete per race.

Important columns:
- unique_race_id: Unique identifier for the race
- race_name: Lowercase-hyphenated race name (e.g., "san-francisco-t100-2025-women")
- cleaned_race_name: Cleaned version of the race name (e.g., "San Francisco T100 2025 Women").
- athlete: Athlete’s full name, uppercased (e.g., "ASHLEIGH GENTLE")
- athlete_slug: Lowercase, hyphenated version of the athlete's name (e.g., "ashleigh-gentle")
- gender: Athlete gender (e.g., "women", "men')
- organizer: Race organizer (e.g., "t100", "ironman")
- distance: Race distance (e.g., "100 km", "Half-Iron (70.3 miles)", "Iron (140.6 miles)")
- location: City and country (e.g., "San Francisco, CA, United States")
- race_date: Race date

Prediction columns:
- swim_pto_rank/bike_pto_rank/run_pto_rank/overall_pto_rank: The athlete's predicted finishing position in the disciplines relative to the rest of the field
- swim_actual_rank/bike_actual_rank/run_actual_rank/overall_actual_rank: The athlete's actual finishing position in the disciplines relative to the rest of the field
- swim_delta/bike_delta/run_delta/overall_delta: Difference between predicted and actual rank (positive means better than predicted i.e. they overperformed, negative means worse than predicted i.e. they underperformed)

Result columns:
- place: The actual finishing position
- swim_time/bike_time/run_time/overall_time: The athlete's actual finish time in HH:MM:SS format
- swim_seconds/bike_seconds/run_seconds/overall_seconds: The actual finish time in seconds


This table is used to compare how closely the athletes's race predictions matched the actual outcomes. You can calculate accuracy, identify over- or under-performing athletes, or summarize over/under performance by race, gender, or athlete.


3. `trilytx_fct.fct_pto_scores_weekly`
Contains weekly PTO segment scores for each athlete by distance group and overall. The higher the score, the better the athlete..

Important columns:
- athlete_id: Unique identifier for the athlete
- athlete: Athlete’s full name (e.g., “LIONEL SANDERS”)
- athlete_slug: Lowercase, hyphenated version of the athlete's name (e.g., "lionel-sanders")
- gender: Athlete gender (e.g., "men" and "women")
- country: Country the athlete represents (e.g., "Canada")
- weight: Athlete weight (e.g., "73kg")
- height: Athlete height in meters (e.g., "1.77")
- age: Athlete age at the time of the report
- born: Athlete birth year
- reporting_week: Date of the week this score is reporting on (e.g., "2023-09-10") - Assume the user is asking for an up-to-date week if they do not specify. up-to-date means reporting_week = date_trunc(current_date(), week)
- distance_group: Race category (e.g., "Iron (140.6 miles)", "Half-Iron (70.3 miles)", "100 km", "Overall"). If the user does not define a distance, default to distance_group = 'Overall'
- swim_pto_score, bike_pto_score, run_pto_score, overall_pto_score: PTO segment scores. Higher is better.
- t1_pto_score, t2_pto_score: Transition segment scores
- rank_*: Ranking columns that compare this athlete’s score across different groupings (e.g., by distance, gender, country, birth year). These are useful for relative performance analysis.


4. `trilytx_fct.fct_race_segment_positions`
Contains athlete-level rank and cumulative time tracking throughout each segment of a race. This table is used to analyze how athlete position changes after each leg and transition within a race.

Important columns:
- race_results_id: Unique identifier for each athlete's race result record.
- unique_race_id: Unique identifier for the race event.
- athlete: Athlete’s full name UPPERCASE (e.g., “LIONEL SANDERS”).
- athlete_slug: Lowercase, hyphenated version of the athlete's name (e.g., “lionel-sanders”).
- gender: Athlete gender (e.g., “men” or “women”).
- race_name: Lowercase-hyphenated race name (e.g., "san-francisco-t100-2025-women").
- cleaned_race_name: Cleaned version of the race name (e.g., "San Francisco T100 2025 Women").
- year: Year the race occurred.
- race_date: Date of the race (e.g., “2025-06-01”).
- tier: Tier classification of the race (e.g., “Gold Tier”).
- country: Country the athlete represents (e.g., “Canada”).
- distance: Race distance category (e.g., "Iron (140.6 miles)", "Half-Iron (70.3 miles)", "100 km", "Overall").
- location: City and country of the race (e.g., "San Francisco, CA, United States").

Cumulative time tracking (in seconds):
- cumulative_seconds_after_swim: Time after swim segment.
- t1_cumulative_seconds_after_t1: Time after T1 transition.
- bike_cumulative_seconds_after_bike: Time after bike segment.
- t2_cumulative_seconds_after_t2: Time after T2 transition.
- run_cumulative_seconds_after_run: Final time after the run.

Rank tracking:
- rank_after_swim: Athlete’s rank immediately after swim.
- rank_after_t1: Rank after T1.
- rank_after_bike: Rank after bike.
- rank_after_t2: Rank after T2.
- rank_after_run: Final rank after run.

Position change metrics (relative movement):
- position_change_in_t1: Rank change during T1 transition.
- position_change_on_bike: Rank change during the bike leg.
- position_change_in_t2: Rank change during T2 transition.
- position_change_on_run: Rank change during the run leg.


Use this table to analyze mid-race dynamics, such as who moved up or down in rankings during specific legs or transitions.



You may join the two tables using `athlete_slug`. For time-based analysis, use `reporting_week` (weekly scores) or `date` (race day).


Helpful tips:
- If a question is asked about "half" or "70.3", use `distance = 'Half-Iron (70.3 miles)'`, and for "full" or "140.6", use `distance = 'Iron (140.6 miles)'`.
- T100 is a reference to `organizer = 't100'`.
- If the user says "female", replace it with `gender = 'women'`; "male" becomes `gender = 'men'`.
- If filtering by the latest race date, use a subquery: `WHERE date = (SELECT MAX(date) FROM ...)`.
- Only join `trilytx_fct.fct_pto_scores_weekly` if the user explicitly references segment scores (not results) or ranking data.
- Do **not** use `QUALIFY` unless using a window function like `RANK()` or `ROW_NUMBER()`.
- when looking at race results, remove athletes who did not finish (overall_seconds IS NOT NULL).
- the olympic games are in where unique_race_id like  '%olympic-games%'
- when possible, search in the lower(cleaned_race_name) for the race name rather than the hyphenated version. For example, if the user asks about Eagleman, search for `lower(cleaned_race_name) like '%eagleman%'`.
- If a user references a location (like “Oceanside”), assume it refers to the full known location name such as “Oceanside, CA, United States” as found in the `location` or `race_name` columns. Prefer searching with `LIKE '%Oceanside%'` or matching known values like “Oceanside, CA, United States” from historical data.If multiple races occurred there, include them all unless the user specifies a year or date.
- When asking about race results, include information like the race name, gender, location, date, distance, organizer, overall time, place, etc. 
- When returning information about an athlete, include name, year, country, and gender. 
- when returning information about the latest (or most recent) race, use qualify 1 = row number() over (partition by ... order by date desc) to get the latest

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

Write a 2-4 sentence summary in in a plain analytical tone. if the answer is 1 word or a number, 1 sentance is fine.

**Bold** the following when they appear:
- Athlete names
- Finish times (e.g., '1:25:30' or similar)
- Country names
- Finishing places (e.g., 1st, 2nd, 3rd)
Use Markdown formatting (e.g., `**name**`) in your summary.

"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
    )
    return response.choices[0].message.content.strip()

# ──────────────────────────────────────────────────────────────────────────────
# Streamlit App
# ──────────────────────────────────────────────────────────────────────────────
def log_vote_to_bq(client, full_table_path: str, vote_type: str, question: str, summary: str):
    rows = [{
        "vote_type": vote_type,
        "question": question,
        "summary": summary,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }]
    errors = client.insert_rows_json(full_table_path, rows)
    if errors:
        st.error(f"🔴 Error logging vote: {errors}")

def log_interaction_to_bq(client, full_table_path: str, question: str, sql: str, summary: str):
    rows = [{
        "question": question,
        "generated_sql": sql,
        "summary": summary,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }]
    errors = client.insert_rows_json(full_table_path, rows)
    if errors:
        st.error(f"🔴 Error logging interaction: {errors}")
def log_error_to_bq(client, full_table_path: str, question: str, sql: str, error_msg: str, attempt: int):
    rows = [{
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "question": question,
        "generated_sql": sql,
        "error_message": error_msg,
        "attempt": attempt
    }]
    errors = client.insert_rows_json(full_table_path, rows)
    if errors:
        st.error(f"🔴 Failed to log error to BigQuery: {errors}")

def main():
    st.set_page_config(page_title="Trilytx SQL Chatbot", layout="wide")
    st.title("🤖 Trilytx Chatbot")
    st.markdown("Ask a question about triathlon race data.")

    credentials, project_id, openai_key = load_credentials()
    bq_client = bigquery.Client(credentials=credentials, project=project_id)

    # ───────────────────────────────
    # Session State Initialization
    # ───────────────────────────────
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

    if "last_question" not in st.session_state:
        st.session_state.last_question = ""

    if "last_summary" not in st.session_state:
        st.session_state.last_summary = ""

    if "last_df" not in st.session_state:
        st.session_state.last_df = pd.DataFrame()

    # ───────────────────────────────
    # Sidebar Filters
    # ───────────────────────────────
    with st.sidebar:
        st.header("⚙️ Optional Filters")
        athlete_name = st.text_input("Filter by athlete", value="")
        distance_filter = st.selectbox("Distance type", ["", "Half-Iron (70.3 miles)", "Iron (140.6 miles)", "Other middle distances", "Other long distances", "100 km"])
        gender_filter = st.selectbox("Gender", ["", "men", "women"])

        st.markdown("---")
        st.subheader("💡 Try an Example")
        if st.button("How many wins does Lionel Sanders have in Oceanside?"):
            st.session_state.example_question = "How many wins does Lionel Sanders have in Oceanside?"
        if st.button("Who won the 70.3 world championship in 2024?"):
            st.session_state.example_question = "Who won the 70.3 world championship in 2024?"
        if st.button("Who are the top 3 female cyclists today in the 70.3 distance?"):
            st.session_state.example_question = "Who are the top 3 female cyclists today in the 70.3 distance?"

    # ───────────────────────────────
    # Main Input
    # ───────────────────────────────
    question = st.text_input("Ask your question", value=st.session_state.example_question)

    if st.button("Submit") and question:
        try:
            with st.spinner("Generating SQL and fetching results..."):
                filters_context = ""
                if athlete_name:
                    filters_context += f"\n- Athlete: {athlete_name}"
                if distance_filter:
                    filters_context += f"\n- Distance: {distance_filter}"
                if gender_filter == "men":
                    filters_context += "\n- Gender: men"
                elif gender_filter == "women":
                    filters_context += "\n- Gender: women"
                # If it's "men and women", you likely want to skip filtering

                base_context = f"{question}\n\n[Contextual Filters Applied]{filters_context if filters_context else ' None'}\n\nNote: The `athlete` column is stored in UPPERCASE."

                max_attempts = 5
                attempt = 1
                error_history = []

                sql = generate_sql_from_question(base_context, openai_key)
                # st.code(sql, language="sql")

                while attempt <= max_attempts:
                    try:
                        df = run_bigquery(sql, bq_client)
                        break  # ✅ Success
                    except Exception as bq_error:
                        error_str = str(bq_error)
                        error_history.append(f"Attempt {attempt}: {error_str}")
                        st.warning(f"Attempt {attempt} failed: {error_str}")
                        log_error_to_bq(
                            bq_client,
                            "trilytx.trilytx.chatbot_error_log",
                            question,
                            sql,
                            error_str,
                            attempt
                        )

                        if attempt == max_attempts:
                            summary = (
                                f"❌ **Query failed after {max_attempts} attempts.**\n\n"
                                f"**Your question:** {question}\n\n"
                                f"**Error details:**\n" +
                                "\n".join(error_history)
                            )
                            df = pd.DataFrame()  # ensure df is defined so the rest of the logic still works
                            break

                        retry_context = (
                            f"{base_context}\n\n[ERROR LOG]\n" +
                            "\n".join(error_history) +
                            "\n\nPlease revise the SQL to avoid these issues. Do not use columns or aliases not listed in the Important columns: section of the prompt."
                        )
                        sql = generate_sql_from_question(retry_context,  openai_key)
                        # st.code(sql, language="sql")
                        attempt += 1
                if df.empty:
                    summary = (
                        f"### ⚠️ No results found for your question:\n"
                        f"> **{question}**\n\n"
                        f"Try:\n"
                        f"- Relaxing filters like country, gender, or birth year\n"
                    )

                else:
                    summary = summarize_results(df, openai_key, question)

                st.session_state.history.append((question, summary))
                st.session_state.last_question = question
                st.session_state.last_summary = summary
                st.session_state.last_df = df
                st.session_state.last_sql = sql

                log_interaction_to_bq(
                    bq_client,
                    "trilytx.trilytx.chatbot_question_log",
                    question,
                    sql,
                    summary
                )

        except Exception as e:
            st.error(f"❌ Unexpected error (caught at top level): {e}")

    # ───────────────────────────────
    # Display Tabs
    # ───────────────────────────────
    if not st.session_state.last_question:
        st.info("Ask a question to begin.")
        return

    tab1, tab2, tab3, tab4 = st.tabs(["🧠 Answer", "🧾 SQL", "📊 Results", "📈 Chart"])

    with tab1:
        st.markdown("### 🧠 Answer")
        st.write(st.session_state.last_summary)
        st.metric("Rows Returned", len(st.session_state.last_df))
        if "overall_seconds" in st.session_state.last_df.columns:
            st.metric("Fastest Time (sec)", int(st.session_state.last_df["overall_seconds"].min()))

        st.markdown("#### Was this answer helpful?")
        vote_col1, vote_col2 = st.columns(2)
        with vote_col1:
            if st.button("👍 Yes", key="vote_up"):
                vote_record = ("👍", st.session_state.last_question, st.session_state.last_summary)
                st.session_state.votes.append(vote_record)
                log_vote_to_bq(bq_client, "trilytx.trilytx.chatbot_vote_feedback", "UP", st.session_state.last_question, st.session_state.last_summary)
                st.success("Thanks for your feedback!")
        with vote_col2:
            if st.button("👎 No", key="vote_down"):
                vote_record = ("👎", st.session_state.last_question, st.session_state.last_summary)
                st.session_state.votes.append(vote_record)
                log_vote_to_bq(bq_client, "trilytx.trilytx.chatbot_vote_feedback", "DOWN", st.session_state.last_question, st.session_state.last_summary)
                st.warning("Thanks for your feedback!")

    with tab2:
        st.markdown("### 🧾 Generated SQL")
        st.code(st.session_state.last_sql, language="sql")

    with tab3:
        st.markdown("### 📊 Results")
        st.dataframe(st.session_state.last_df)

    with tab4:
        if "athlete" in st.session_state.last_df.columns and "overall_seconds" in st.session_state.last_df.columns:
            st.markdown("### 📈 Chart: Athlete vs. Time")
            chart = alt.Chart(st.session_state.last_df).mark_bar().encode(
                x=alt.X("athlete:N", sort="-y"),
                y="overall_seconds:Q",
                tooltip=["athlete", "overall_seconds"]
            ).properties(height=400)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No chartable data in result.")

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