# cd "C:\Users\dusti\OneDrive\Documents\GitHub\trilytxbot"
# streamlit run app.py
import os
import json
import pandas as pd
import streamlit as st

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
- race_name, unique_race_id, year, date: Race-level identifiers and timing
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

    st.markdown("---")
    st.subheader("Optional filters (used for context only)")
    athlete_name = st.text_input("Filter by athlete (e.g., Lionel Sanders)")
    distance_filter = st.selectbox("Distance type", options=["", "Half-Iron (70.3 miles)", "Iron (140.6 miles)", "Olympic", "Sprint", "100 km"])

    question = st.text_input("Ask your question")
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
                st.code(sql, language="sql")
                df = run_bigquery(sql, bq_client)
                st.dataframe(df)
                summary = summarize_results(df, openai_key, question)
                st.markdown("### 🧠 Answer")
                st.write(summary)
        except Exception as e:
            st.error(f"❌ Error: {e}")


if __name__ == "__main__":
    main()