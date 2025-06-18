# cd "C:\Users\dusti\OneDrive\Documents\GitHub\trilytxbot"
# streamlit run app.py
import os
import json
import time
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



USE_LOCAL = 0 # Set to 0 for pushing to production, 1 for local development

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

1. `trilytx_fct.fct_race_results`
Contains race-day performance results for individual athletes.

Important columns:
- athlete: Athlete’s full name (e.g., “LIONEL SANDERS”)
- athlete_slug: Lowercase, hyphenated version of the athlete's name
- place: Athlete’s finish position in the race (1, 2, 3, etc.) 
- overall_seconds: total race time in seconds. when using aggregations, use this column to calculate the fastest time, average time, etc
- overall_time: Total race time (in seconds and as HH:MM:SS). Use this for display purposes.
- swim_time, bike_time, run_time: Segment times in string format.  Use this for display purposes.
- swim_seconds, bike_seconds, run_seconds: Segment times in seconds.  when using aggregations, use this column to calculate the fastest time, average time, etc
- swim_pto_score, bike_pto_score, run_pto_score, overall_pto_score: PTO segment scores for the race. Higher is better.


- distance: Full race distance label (e.g., "Half-Iron (70.3 miles)", "Iron (140.6 miles)", "Short course", "Other middle distances", "Other long distances", "100 km")
- category: race category
- gender: Athlete gender (e.g., "men" and "women")
- country: Country the athlete represents (e.g., "Canada")
- year: Year
- race_name: Lowercase-hyphenated race name (e.g., "san-francisco-t100-2025-women")
- cleaned_race_name: Cleaned version of the race name (e.g., "San Francisco T100 2025 Women").
- race_date: Race date
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
- reporting_week: Date of the week this score is reporting on (e.g., "2023-09-10") - Assume the user is asking for an up-to-date week if they do not specify. up-to-date means reporting_week = date_trunc(current_date(), week). If the user asks for a specific date, use date_trunc(specific_date, week) to find the reporting week.
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



You may join the tables using `athlete_slug` and 'unique_race_id'. For time-based analysis, use `reporting_week` (weekly scores) or `race_date` (race day).
Do not join on cleaned_race_name as it is not unique across race years or race genders. 

Helpful SQL Tips for Query Generation

General Structure
- Use CTEs (WITH clauses) to modularize and simplify logic.
- Filter for relevant data early in the CTE chain to improve performance.
- In the final SELECT, only return the columns needed to answer the question.
- If possible, return a single row summarizing the results.

Keyword Mapping for Filters
- "Half" or "70.3" → distance = 'Half-Iron (70.3 miles)'
- "Full" or "140.6" → distance = 'Iron (140.6 miles)'
- "Female" → gender = 'women', "Male" → gender = 'men'
- "T100" → organizer = 't100'
- "DNF" or "Did Not Finish" → overall_seconds IS NULL

Data Recency
- Use: WHERE date = (SELECT MAX(date) FROM ...)
  or QUALIFY ROW_NUMBER() OVER (...) = 1
- Use QUALIFY only with window functions (RANK(), ROW_NUMBER()).

Filtering Rules
- Exclude non-finishers with: overall_seconds IS NOT NULL
- For Olympic races: unique_race_id LIKE '%olympic-games%'
- Assume “latest” = most recent race_date or reporting_week if unspecified.

Fuzzy Matching
- Race name: LOWER(cleaned_race_name) LIKE '%eagleman%'
- Location: location LIKE '%Oceanside%' or race_name LIKE '%Oceanside%'

Include the Following When Relevant
- Race Summaries: race name, gender, location, date, distance, organizer, overall time, place
- Athlete Info: name, year, country, gender
- provider 1 row of context when able:
    - question: When was the last time athlete x was on the podium? 
    - answer: include race name, date, location, distance, place, overall time

Conditional Joins
- Only join fct_pto_scores_weekly if segment scores or rankings are explicitly referenced.

Head-to-Head Comparisons
- Avoid self-joins—use QUALIFY with ROW_NUMBER() to isolate rows per athlete.
- Alias as a and b, then:
    a.place AS athlete_a_place,
    b.place AS athlete_b_place,
    CASE WHEN a.place < b.place THEN a.athlete ELSE b.athlete END AS better_athlete
- Group by unique_race_id, race_date, cleaned_race_name, location, both athlete names, and places.
- Use QUALIFY to de-duplicate when needed.

Your Task:
Based on the user question below, generate only a valid BigQuery SQL query using the columns stated above.
Do not include explanations, comments, or markdown. Return SQL only.
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
    # Convert rows to natural language sentences
def row_to_sentence(row: pd.Series) -> str:
    return ". ".join([f"{col}: {row[col]}" for col in row.index]) + "."

def summarize_results(df: pd.DataFrame, openai_key: str, question: str) -> str:
    client = OpenAI(api_key=openai_key)
    
    rows_as_sentences = "\n".join(row_to_sentence(row) for _, row in df.iterrows())

    prompt = f"""A user asked: \"{question}\".
Here are the results, described as plain language statements:

{rows_as_sentences}




Write a 1-3 sentence summary in in a plain analytical tone. if the answer is 1 word or a number, 1 sentance is fine.

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

        # ADD THESE TWO LINES:
    if "query_attempts_count" not in st.session_state:
        st.session_state.query_attempts_count = 0 # Initialize with 0 attempts

    if "last_duration_seconds" not in st.session_state:
        st.session_state.last_duration_seconds = 0 # Initialize with 0 seconds

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
    question = st.text_area("Ask your question", value=st.session_state.example_question, height=150)

    if st.button("Submit") and question:
        try:
            with st.spinner("Generating SQL and fetching results..."):
                start_time = time.time()
                filters_context = ""
                # Building filters_context based on sidebar selections (athlete_name, distance_filter, gender_filter)
                if athlete_name:
                    filters_context += f"\n- Athlete: {athlete_name}"
                if distance_filter:
                    filters_context += f"\n- Distance: {distance_filter}"
                if gender_filter == "men":
                    filters_context += "\n- Gender: men"
                elif gender_filter == "women":
                    filters_context += "\n- Gender: women"

                # base_context is defined on this line:
                base_context = f"{question}\n\n[Contextual Filters Applied]{filters_context if filters_context else ' None'}\n\nNote: The `athlete` column is stored in UPPERCASE."
                max_attempts = 5
                st.session_state.query_attempts_count = 1
                error_history = []
                sql = "" # Initialize sql here as well, just in case

                # Initialize summary here with a default value
                summary = "" # <--- ADD THIS LINE

                while st.session_state.query_attempts_count <= max_attempts:
                    try:
                        sql = generate_sql_from_question(base_context, openai_key) # SQL generation here
                        df = run_bigquery(sql, bq_client)
                        break  # ✅ Success
                    except Exception as bq_error:
                        error_str = str(bq_error)
                        error_history.append(f"Attempt {st.session_state.query_attempts_count}: {error_str}")
                        st.warning(f"Attempt {st.session_state.query_attempts_count} failed: {error_str}")
                        log_error_to_bq(
                            bq_client,
                            "trilytx.trilytx.chatbot_error_log",
                            question,
                            sql, # Use the latest generated SQL
                            error_str,
                            st.session_state.query_attempts_count
                        )

                        if st.session_state.query_attempts_count == max_attempts:
                            summary = ( # <--- summary is assigned here
                                f"❌ **Query failed after {max_attempts} attempts.**\n\n"
                                f"**Your question:** {question}\n\n"
                                f"**Error details:**\n" +
                                "\n".join(error_history)
                            )
                            df = pd.DataFrame()
                            break

                        retry_context = (
                            f"{base_context}\n\n[ERROR LOG]\n" +
                            "\n".join(error_history) +
                            "\n\nPlease revise the SQL to avoid these issues. Do not use columns or aliases not listed in the Important columns: section of the prompt."
                        )
                        sql = generate_sql_from_question(retry_context, openai_key) # This line is usually re-generated in the loop start
                        st.session_state.query_attempts_count += 1

                # After the loop, check if df is empty or if an error led to no results
                if df.empty and not summary: # Only assign if summary hasn't been set by a max_attempts failure
                    summary = ( # <--- summary is assigned here
                        f"### ⚠️ No results found for your question:\n"
                        f"> **{question}**\n\n"
                        f"Try:\n"
                        f"- Relaxing filters like country, gender, or birth year\n"
                    )
                elif not summary: # If df is not empty AND summary hasn't been set (i.e., no max_attempts failure)
                    summary = summarize_results(df, openai_key, question) # <--- summary is assigned here

                st.session_state.last_duration_seconds = round(time.time() - start_time) # Store in session state
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
                    summary # summary is guaranteed to have a value here
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
        query_attempts_display = st.session_state.query_attempts_count
        duration_display = st.session_state.last_duration_seconds

        st.caption(f"🕒 Answer generated in {query_attempts_display} query attempt{'s' if query_attempts_display > 1 else ''} and {duration_display} seconds.")
        if not st.session_state.last_df.empty and len(st.session_state.last_df) > 7:
            st.warning(f"Displaying {len(st.session_state.last_df)} rows. This table is large - Trilytx sometimes has trouble parsing larger datasets. Please consider refining your question.")
        st.markdown("### 🧠 Answer")
        st.write(st.session_state.last_summary)
        st.markdown(f"**Rows Returned:** {len(st.session_state.last_df)}")
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
        # if not st.session_state.last_df.empty:
        #     # This is the crucial part that sends the DataFrame to the other page
        #     if st.button("🔬 Analyze in new page"):
        #         st.session_state.selected_df = st.session_state.last_df
        #         st.switch_page("pages/3_🔬_Explore_Selected_Columns.py") # Ensure this path is correct

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