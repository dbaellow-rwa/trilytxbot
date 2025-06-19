# cd "C:\Users\dusti\OneDrive\Documents\GitHub\trilytxbot\pages"
# streamlit run Home_2.py

import os
import sys
import json # You might not need this if json.loads is only in bq_utils
import time
import pandas as pd
import streamlit as st
import altair as alt
import datetime

# Add the project root directory ('trilytxbot') to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import BigQuery module itself for client instantiation
import google.cloud.bigquery as bigquery # <--- ADD THIS LINE

# Import from your new utility and config files
from config.app_config import USE_LOCAL, BQ_CHATBOT_ERROR_LOG, BQ_CHATBOT_ZERO_RESULT_LOG, BQ_CHATBOT_QUESTION_LOG, BQ_CHATBOT_VOTE_FEEDBACK
from utils.bq_utils import load_credentials, run_bigquery, extract_table_schema
from utils.llm_utils import generate_sql_from_question_modular, summarize_results
from utils.streamlit_utils import log_vote_to_bq, log_interaction_to_bq, log_error_to_bq, log_zero_result_to_bq
from utils.security_utils import is_safe_sql


# ──────────────────────────────────────────────────────────────────────────────
# Streamlit App
# ──────────────────────────────────────────────────────────────────────────────
def main():
    st.set_page_config(page_title="Trilytx SQL Chatbot", layout="wide")
    st.title("🤖 Trilytx Chatbot")
    st.markdown("Ask a question about triathlon race data.")

    # Load credentials and initialize BigQuery client once
    # USE_LOCAL comes from config.app_config
    credentials, project_id, openai_key = load_credentials(USE_LOCAL)
    bq_client = bigquery.Client(credentials=credentials, project=project_id) # This line now has 'bigquery' defined

    # ───────────────────────────────
    # Session State Initialization
    # ───────────────────────────────
    if not openai_key:
        st.error("Missing OpenAI API key. Please check your credentials.")
        return

    # Schema is still useful to have in session state, extracted once
    if "schema" not in st.session_state:
        # Changed to fct_race_results as it's more central for initial schema load
        st.session_state.schema = extract_table_schema(bq_client, "trilytx_fct", "fct_race_results")

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

    if "query_attempts_count" not in st.session_state:
        st.session_state.query_attempts_count = 0

    if "last_duration_seconds" not in st.session_state:
        st.session_state.last_duration_seconds = 0

    if "last_sql" not in st.session_state:
        st.session_state.last_sql = "" # Initialize this as it's referenced in tab2

    # ───────────────────────────────
    # Sidebar Filters
    # ───────────────────────────────
    with st.sidebar:
        st.header("⚙️ Optional Filters")
        athlete_name = st.text_input("Filter by athlete", value="")
        distance_filter = st.selectbox("Distance type", ["", "Half-Iron (70.3 miles)", "Iron (140.6 miles)", "Other middle distances", "Other long distances", "100 km"])
        gender_filter = st.selectbox("Gender", ["", "men", "women"])
        organizer_filter = st.selectbox("Organizer", ["", "challenge", "t100", "ironman", "itu", "pto", "wtcs"])

        with st.expander("💡 Try an Example"):
            st.subheader("Quick Example Questions")
            st.markdown("Click any question below to autofill the input box with a smart example. You can edit it or run it as-is.")

            # Using st.session_state to update the text_area's value via the key
            if st.button("🏆 How many wins does Lionel Sanders have in Oceanside?", key="ex1"):
                st.session_state.example_question = "How many wins does Lionel Sanders have in Oceanside?"
                st.session_state.last_question = "" # Clear previous result on example click
            if st.button("🌍 Who won the 70.3 world championship in 2024?", key="ex2"):
                st.session_state.example_question = "Who won the 70.3 world championship in 2024?"
                st.session_state.last_question = ""
            if st.button("🚴‍♀️ Who are the top 3 female cyclists today in the 70.3 distance?", key="ex3"):
                st.session_state.example_question = "Who are the top 3 female cyclists today in the 70.3 distance?"
                st.session_state.last_question = ""
            if st.button("🧠 What were the rankings after the bike section at the most recent women's T100 event?", key="ex4"):
                st.session_state.example_question = "What were the rankings after the bike section at the most recent women's T100 event?"
                st.session_state.last_question = ""


    # ───────────────────────────────
    # Main Input
    # ───────────────────────────────
    # Use key to ensure text_area updates when example_question changes
    question = st.text_area("Ask your question", value=st.session_state.example_question, height=150, key="main_question_input")

    if st.button("Submit", key="submit_button") and question: # Add a unique key here
        # Reset example_question after submission to prevent re-filling on subsequent runs
        st.session_state.example_question = ""
        st.session_state.query_attempts_count = 0 # Reset attempts for new question

        try:
            with st.spinner("Generating SQL and fetching results..."):
                start_time = time.time()
                filters_context = ""

                if athlete_name:
                    filters_context += f"\n- athlete_name: {athlete_name}"
                if distance_filter:
                    filters_context += f"\n- race_distance: {distance_filter}"
                if gender_filter == "men":
                    filters_context += "\n- athlete_gender: men"
                if gender_filter == "women":
                    filters_context += "\n- athlete_gender: women"
                if organizer_filter:
                    filters_context += f"\n- organizer: {organizer_filter}"

                base_context = f"{question}\n\n[Contextual Filters Applied]{filters_context if filters_context else ' None'}\n\nNote: The `athlete` column is stored in UPPERCASE."
                max_attempts = 5
                error_history = []
                zero_result_history = []
                sql = ""
                summary = ""
                df = pd.DataFrame() # Ensure df is initialized

                while st.session_state.query_attempts_count < max_attempts:
                    st.session_state.query_attempts_count += 1
                    current_context = base_context
                    if error_history or zero_result_history:
                        current_context += (
                            f"\n\n[NOTE] Previous attempts returned 0 results:\n" + "\n".join(zero_result_history) + "\n\n" if zero_result_history else ""
                        )
                        current_context += (
                            f"[ERROR LOG] Previous attempts returned BigQuery errors:\n" + "\n".join(error_history) + "\n\n" if error_history else ""
                        )
                        current_context += "Please revise the SQL to avoid these issues. Do not use columns or aliases not listed in the 'Important columns' section of the prompt, and ensure joins and filters are valid given the context."

                    try:
                        sql = generate_sql_from_question_modular(current_context, openai_key)

                        if not is_safe_sql(sql):
                            error_str = "Unsafe SQL detected. Execution blocked."
                            st.error(f"🚫 {error_str}")
                            log_error_to_bq(bq_client, BQ_CHATBOT_ERROR_LOG, question, sql, error_str, st.session_state.query_attempts_count)
                            summary = f"🚫 **Query blocked for safety**\n\n**Your question:** {question}\n\n**Reason:** Unsafe SQL detected."
                            df = pd.DataFrame()
                            break # Exit loop as it's a critical safety block

                        df = run_bigquery(sql, bq_client)

                        if df.empty:
                            zero_result_history.append(f"[Attempt {st.session_state.query_attempts_count}] {sql}")
                            log_zero_result_to_bq(bq_client, BQ_CHATBOT_ZERO_RESULT_LOG, question, sql, st.session_state.query_attempts_count)
                            st.warning(f"Attempt {st.session_state.query_attempts_count} returned no results. Retrying...")
                            if st.session_state.query_attempts_count == max_attempts:
                                summary = (
                                    f"### ⚠️ No results found for your question after {max_attempts} attempts:\n"
                                    f"> **{question}**\n\n"
                                    f"Try:\n"
                                    f"- Relaxing filters like country, gender, or birth year\n"
                                )
                                break # No more retries for zero results
                            continue # Retry with updated context

                        # Success path
                        break

                    except Exception as bq_error:
                        error_str = str(bq_error)
                        error_history.append(
                            f"[Attempt {st.session_state.query_attempts_count}]\nSQL:\n{sql}\nError:\n{error_str}"
                        )
                        st.warning(f"Attempt {st.session_state.query_attempts_count} failed: {error_str}. Retrying...")
                        log_error_to_bq(bq_client, BQ_CHATBOT_ERROR_LOG, question, sql, error_str, st.session_state.query_attempts_count)

                        if st.session_state.query_attempts_count == max_attempts:
                            summary = (
                                f"❌ **Query failed after {max_attempts} attempts.**\n\n"
                                f"**Your question:** {question}\n\n"
                                f"**Error details:**\n" +
                                "\n".join(error_history)
                            )
                            df = pd.DataFrame()
                            break # No more retries for errors

                        continue # Retry with updated context

                # After the loop, if no summary was generated by a terminal failure state, generate it now.
                if not summary:
                    if df.empty:
                         summary = (
                                f"### ⚠️ No results found for your question:\n"
                                f"> **{question}**\n\n"
                                f"Try:\n"
                                f"- Relaxing filters like country, gender, or birth year\n"
                            )
                    else:
                        summary = summarize_results(df, openai_key, question)

                st.session_state.last_duration_seconds = round(time.time() - start_time)
                st.session_state.history.append((question, summary))
                st.session_state.last_question = question
                st.session_state.last_summary = summary
                st.session_state.last_df = df
                st.session_state.last_sql = sql

                # Log interaction only if a valid SQL was generated and processed (even if df was empty).
                # Only log if it's not a safety blocked query (where summary is already set to error message).
                if "Query blocked for safety" not in summary:
                    log_interaction_to_bq(bq_client, BQ_CHATBOT_QUESTION_LOG, question, sql, summary)

        except Exception as e:
            st.error(f"❌ An unexpected internal error occurred: {e}")
            # Log the unexpected error as well
            log_error_to_bq(bq_client, BQ_CHATBOT_ERROR_LOG, question, st.session_state.get("last_sql", "N/A"), str(e), -1)


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


        st.markdown("#### Was this answer helpful?")
        vote_col1, vote_col2 = st.columns(2)
        with vote_col1:
            if st.button("👍 Yes", key="vote_up"):
                vote_record = ("👍", st.session_state.last_question, st.session_state.last_summary)
                st.session_state.votes.append(vote_record)
                log_vote_to_bq(bq_client, BQ_CHATBOT_VOTE_FEEDBACK, "UP", st.session_state.last_question, st.session_state.last_summary)
                st.success("Thanks for your feedback!")
        with vote_col2:
            if st.button("👎 No", key="vote_down"):
                vote_record = ("👎", st.session_state.last_question, st.session_state.last_summary)
                st.session_state.votes.append(vote_record)
                log_vote_to_bq(bq_client, BQ_CHATBOT_VOTE_FEEDBACK, "DOWN", st.session_state.last_question, st.session_state.last_summary)
                st.warning("Thanks for your feedback!")

    with tab2:
        st.markdown("### 🧾 Generated SQL")
        st.code(st.session_state.last_sql, language="sql")

    with tab3:
        st.markdown("### 📊 Results")
        st.dataframe(st.session_state.last_df)
        # if not st.session_state.last_df.empty:
        #     if st.button("🔬 Analyze in new page"):
        #         st.session_state.selected_df = st.session_state.last_df
if __name__ == "__main__":
    main()