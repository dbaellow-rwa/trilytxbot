import os
import sys
import time
import uuid
import pandas as pd
import streamlit as st
st.set_page_config(page_title="Trilytx SQL Chatbot",
    page_icon="https://github.com/dbaellow-rwa/trilytxbot/blob/fe681401e506fd4deccca9fa7c0c751c2cbbf070/assets/logo.png?raw=true",
    initial_sidebar_state="expanded",
    layout="wide")
st.title("🤖 Trilytx Chatbot")


import altair as alt
import datetime

# Add the project root directory ('trilytxbot') to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import google.cloud.bigquery as bigquery

from config.app_config import USE_LOCAL, BQ_CHATBOT_ERROR_LOG, BQ_CHATBOT_ZERO_RESULT_LOG, BQ_CHATBOT_QUESTION_LOG, BQ_CHATBOT_VOTE_FEEDBACK
from utils.bq_utils import load_credentials, run_bigquery, extract_table_schema
from utils.llm_utils import generate_sql_from_question_modular, summarize_results
from utils.streamlit_utils import log_vote_to_bq, log_interaction_to_bq, log_error_to_bq, log_zero_result_to_bq, get_oauth,init_cookies_and_restore_user
cookies = init_cookies_and_restore_user()
from utils.security_utils import is_safe_sql
from utils.about_the_chatbot import render_about

oauth2, redirect_uri = get_oauth()
render_about()


# --- Function to handle the core query processing logic ---
# This function is called by both initial and follow-up submission buttons
def process_question(question_text: str, is_follow_up: bool, bq_client: bigquery.Client, openai_key: str,
                     athlete_name: str, distance_filter: str, gender_filter: str, organizer_filter: str):
    """
    Handles the entire process of generating SQL, running BigQuery, summarizing results,
    and updating session state. This function now includes multi-turn conversational context.
    """
    st.session_state.query_attempts_count = 0
    start_time = time.time()
    filters_context = ""

    # Build filters context from sidebar
    if athlete_name: filters_context += f"\n- athlete_name: {athlete_name}"
    if distance_filter: filters_context += f"\n- race_distance: {distance_filter}"
    if gender_filter: filters_context += f"\n- athlete_gender: {gender_filter}"
    if organizer_filter: filters_context += f"\n- organizer: {organizer_filter}"

    llm_base_context = ""
    # Define how many previous Q&A turns to include in the LLM's context.
    # For example, 2 means include the last 2 (Q,A,SQL) tuples from history.
    max_previous_qa_pairs_for_llm = 2

    # Build conversational history for LLM
    conversation_context_parts = []
    if is_follow_up and st.session_state.history:
        # Get the slice of history for context.
        # history[-max_previous_qa_pairs_for_llm:] gets up to N previous items.
        # We use max(0, ...) to avoid negative indices if history is shorter than max_previous_qa_pairs_for_llm.
        start_index = max(0, len(st.session_state.history) - max_previous_qa_pairs_for_llm)
        context_history_slice = st.session_state.history[start_index:]

        for q_prev, a_prev, df_result, sql_prev in context_history_slice:
            conversation_context_parts.append(f"Previous user query: '{q_prev}'")
            conversation_context_parts.append(f"Assistant's previous answer: '{a_prev}'")
            conversation_context_parts.append(f"Assistant's previous SQL: ```sql\n{sql_prev}\n```")
            
            # Include top few rows from prior result
            if isinstance(df_result, pd.DataFrame) and not df_result.empty:
                preview_rows = df_result.head(5)
                rows_as_sentences = "\n".join(
                    f"{', '.join(f'{col}: {row[col]}' for col in preview_rows.columns)}"
                    for _, row in preview_rows.iterrows()
                )
                conversation_context_parts.append("Previous results (structured):\n" + rows_as_sentences)
    
    conversation_context_parts.append("---")  # Separator

    if conversation_context_parts:
        llm_base_context += "\n".join(conversation_context_parts)
        llm_base_context += "\n" # Add a newline after previous turns if any

    llm_base_context += f"The user's CURRENT question: '{question_text}'\n\n"
    llm_base_context += "Please generate SQL to answer this question. "
    if is_follow_up: # Add explicit instruction for follow-ups
        llm_base_context += "Consider the preceding conversation history to provide a contextually relevant answer. "
        llm_base_context += "Do not repeat information already provided by previous SQL/answers unless specifically asked. "

    llm_base_context += f"[Contextual Filters Applied]{filters_context if filters_context else ' None'}\n\nNote: The `athlete` column is stored in UPPERCASE."

    max_attempts = 5
    error_history = []
    zero_result_history = []
    sql = ""
    summary = ""
    df = pd.DataFrame()

    while st.session_state.query_attempts_count < max_attempts:
        st.session_state.query_attempts_count += 1
        current_context_for_llm = llm_base_context

        # Add error/zero-result history to context for retries
        if error_history or zero_result_history:
            current_context_for_llm += (
                f"\n\n[NOTE] Previous attempt(s) returned 0 results:\n" + "\n".join(zero_result_history) + "\n\n" if zero_result_history else ""
            )
            current_context_for_llm += (
                f"[ERROR LOG] Previous attempt(s) returned BigQuery errors:\n" + "\n".join(error_history) + "\n\n" if error_history else ""
            )
            current_context_for_llm += "Please revise the SQL to avoid these issues. Do not use columns or aliases not listed in the 'Important columns' section of the prompt, and ensure joins and filters are valid given the context."

        try:
            sql = generate_sql_from_question_modular(current_context_for_llm, openai_key)

            if not is_safe_sql(sql):
                error_str = "Unsafe SQL detected. Execution blocked."
                st.error(f"🚫 {error_str}")
                log_error_to_bq(bq_client, BQ_CHATBOT_ERROR_LOG, question_text, sql, error_str, st.session_state.query_attempts_count)
                summary = f"🚫 **Query blocked for safety**\n\n**Your question:** {question_text}\n\n**Reason:** Unsafe SQL detected."
                df = pd.DataFrame()
                break

            df = run_bigquery(sql, bq_client)

            if df.empty:
                zero_result_history.append(f"[Attempt {st.session_state.query_attempts_count}] {sql}")
                log_zero_result_to_bq(bq_client, BQ_CHATBOT_ZERO_RESULT_LOG, question_text, sql, st.session_state.query_attempts_count)
                st.warning(f"Attempt {st.session_state.query_attempts_count} returned no results. Retrying...")
                if st.session_state.query_attempts_count == max_attempts:
                    summary = (
                        f"### ⚠️ No results found for your question after {max_attempts} attempts:\n"
                        f"> **{question_text}**\n\n"
                        f"Try:\n"
                        f"- Relaxing filters like country, gender, or birth year\n"
                    )
                    break
                continue
            break # Exit loop on success with results

        except Exception as bq_error:
            error_str = str(bq_error)
            error_history.append(
                f"[Attempt {st.session_state.query_attempts_count}]\nSQL:\n{sql}\nError:\n{error_str}"
            )
            st.warning(f"Attempt {st.session_state.query_attempts_count} failed: {error_str}. Retrying...")
            log_error_to_bq(bq_client, BQ_CHATBOT_ERROR_LOG, question_text, sql, error_str, st.session_state.query_attempts_count)

            if st.session_state.query_attempts_count == max_attempts:
                summary = (
                    f"❌ **Query failed after {max_attempts} attempts.**\n\n"
                    f"**Your question:** {question_text}\n\n"
                    f"**Error details:**\n" +
                    "\n".join(error_history)
                )
                df = pd.DataFrame()
                break
            continue

    # Final summary generation if not already set by a failure condition
    if not summary:
        if df.empty:
             summary = (
                    f"### ⚠️ No results found for your question:\n"
                    f"> **{question_text}**\n\n"
                    f"Try:\n"
                    f"- Relaxing filters like country, gender, or birth year\n"
                )
        else:
            summary = summarize_results(df, openai_key, question_text,
                            conversational_history=st.session_state.history[-2:],  # last 2 turns (Q, A, SQL),
                            generated_sql=sql)

    # Update session state with the result of the current processing
    st.session_state.last_duration_seconds = round(time.time() - start_time)
    st.session_state.history.append((question_text, summary,df.copy(), sql)) # Add to history
    st.session_state.last_question = question_text
    st.session_state.last_summary = summary
    st.session_state.last_df = df
    st.session_state.last_sql = sql
    st.session_state.last_question_was_follow_up = is_follow_up # Track if this question was a follow-up

    # Log interaction
    if "Query blocked for safety" not in summary:
        log_interaction_to_bq(bq_client, BQ_CHATBOT_QUESTION_LOG, question_text, sql, summary)

    # Reset UI state and trigger rerun to reflect changes
    st.session_state.show_follow_up_input = False # Hide follow-up box after any submission
    st.session_state.follow_up_question_text = "" # Clear its content
    st.session_state.example_question = "" # Clear example text area too after submission
    st.rerun()


def main():

    if "user" not in st.session_state or st.session_state.user is None:
        st.warning("🔒 Please log in on the home page first.")
        st.stop()

    st.markdown("Ask a question about triathlon race data.")
    # st.write(f"DEBUG: Streamlit Version: {st.__version__}") # <--- ADD THIS LINE HERE

    credentials, project_id, openai_key = load_credentials(USE_LOCAL)
    bq_client = bigquery.Client(credentials=credentials, project=project_id)

    # ───────────────────────────────
    # Session State Initialization
    # ───────────────────────────────
    if not openai_key:
        st.error("Missing OpenAI API key. Please check your credentials.")
        return
    if "schema" not in st.session_state: st.session_state.schema = extract_table_schema(bq_client, "trilytx_fct", "fct_race_results")
    if "history" not in st.session_state: st.session_state.history = []
    if "votes" not in st.session_state: st.session_state.votes = []
    if "example_question" not in st.session_state: st.session_state.example_question = ""
    if "last_question" not in st.session_state: st.session_state.last_question = ""
    if "last_summary" not in st.session_state: st.session_state.last_summary = ""
    if "last_df" not in st.session_state: st.session_state.last_df = pd.DataFrame()
    if "query_attempts_count" not in st.session_state: st.session_state.query_attempts_count = 0
    if "last_duration_seconds" not in st.session_state: st.session_state.last_duration_seconds = 0
    if "last_sql" not in st.session_state: st.session_state.last_sql = ""
    if "show_follow_up_input" not in st.session_state: st.session_state.show_follow_up_input = False
    if "follow_up_question_text" not in st.session_state: st.session_state.follow_up_question_text = ""
    if "last_question_was_follow_up" not in st.session_state: st.session_state.last_question_was_follow_up = False # Added this

    # ───────────────────────────────
    # Sidebar Filters
    # ───────────────────────────────
    with st.sidebar:
        with st.expander("⚙️ Optional Filters"):
            athlete_name = st.text_input("Filter by athlete", value="")
            distance_filter = st.selectbox("Distance type", ["", "Half-Iron (70.3 miles)", "Iron (140.6 miles)", "Other middle distances", "Other long distances", "100 km"])
            gender_filter = st.selectbox("Gender", ["", "men", "women"])
            organizer_filter = st.selectbox("Organizer", ["", "challenge", "t100", "ironman", "itu", "pto", "wtcs"])

        with st.expander("💡 Try an Example"):
            st.subheader("Quick Example Questions")
            st.markdown("Click any question below to autofill the input box with a smart example. You can edit it or run it as-is.")
            example_questions = {
                "🏆 How many wins does Lionel Sanders have in Oceanside?": "How many wins does Lionel Sanders have in Oceanside?",
                "🌍 Who won the 70.3 world championship in 2024?": "Who won the 70.3 world championship in 2024?",
                "🚴‍♀️ Who are the top 3 female cyclists today in the 70.3 distance?": "Who are the top 3 female cyclists today in the 70.3 distance?",
                "🧠 What were the rankings after the bike section at the most recent women's T100 event?": "What were the rankings after the bike section at the most recent women's T100 event?"
            }
            for button_text, q_text in example_questions.items():
                if st.button(button_text, key=f"ex_{hash(q_text)}"): # Use hash for unique key
                    st.session_state.example_question = q_text
                    st.session_state.show_follow_up_input = False # Always clear follow-up mode on example click
                    st.session_state.last_question = "" # Clear previous context
                    st.session_state.follow_up_question_text = ""
                    st.rerun()

    # ────────────────────────────────────────────────────────────────────────
    # Input Area: Dynamically show initial or follow-up question input
    # ────────────────────────────────────────────────────────────────────────

    # Display Initial Question Input if not in follow-up mode
    if not st.session_state.show_follow_up_input:
        question_initial = st.text_area("Ask your question",
                                        value=st.session_state.example_question,
                                        height=150,
                                        key="main_question_input")

        if st.button("Submit Initial Question", key="submit_initial_button"):
            if question_initial:
                st.session_state.question_id = str(uuid.uuid4())
                with st.spinner("Processing initial question..."):
                    process_question(
                        question_initial, False, bq_client, openai_key,
                        athlete_name, distance_filter, gender_filter, organizer_filter
                    )
            else:
                st.warning("Please enter a question.")
    # Display Follow-up Question Input if in follow-up mode
    else: # st.session_state.show_follow_up_input is True
        st.markdown("---") # Visual separator
        st.subheader("💬 Ask a Follow-up Question")
        st.markdown(f"Regarding: _'{st.session_state.last_question}'_") # Context for the user
        follow_up_question = st.text_area("Your follow-up:",
                                           value=st.session_state.follow_up_question_text,
                                           height=100,
                                           key="follow_up_question_input_display")

        if st.button("Submit Follow-up Question", key="submit_follow_up_button"):
            if follow_up_question:
                st.session_state.question_id = str(uuid.uuid4())  # <-- HERE
                with st.spinner("Processing follow-up question..."):
                    process_question(
                        follow_up_question, True, bq_client, openai_key,
                        athlete_name, distance_filter, gender_filter, organizer_filter
                    )
            else:
                st.warning("Please enter a follow-up question.")


    # ────────────────────────────────────────────────────────────────────────
    # Display Results and Interaction Controls (only if a question has been processed)
    # ────────────────────────────────────────────────────────────────────────

    # Only show info if nothing has happened yet and no follow-up box is visible
    if not st.session_state.last_question and not st.session_state.show_follow_up_input:
        st.info("Ask a question to begin.")
        return # Exit main() if no question yet

    tab1, tab2, tab3, tab4 = st.tabs(["🧠 Answer", "🧾 SQL", "📊 Results", "📈 Chart"])

    with tab1:
        # Display the main answer details FIRST if a question has been processed
        if not st.session_state.history: # Should not happen if we reach this point, but for safety
            st.info("No questions asked yet.")
        else:
            # Display the CURRENT (latest) question and answer prominently
            st.markdown("### 🧠 Current Question & Answer")
            st.markdown(f"**QUESTION:** {st.session_state.last_question}")
            st.write(st.session_state.last_summary)

            query_attempts_display = st.session_state.query_attempts_count
            duration_display = st.session_state.last_duration_seconds
            st.caption(f"🕒 Answer generated in {query_attempts_display} query attempt{'s' if query_attempts_display > 1 else ''} and {duration_display} seconds.")

            if not st.session_state.last_df.empty and len(st.session_state.last_df) > 7:
                st.warning(f"Displaying {len(st.session_state.last_df)} rows. This table is large - Trilytx sometimes has trouble parsing larger datasets. Please consider refining your question.")
            st.markdown(f"**Rows Returned:** {len(st.session_state.last_df)}")
            # Display the IMMEDIATELY PREVIOUS question and answer if available AND this was a follow-up
            # This ensures "Previous Turn" only shows when the current Q is a follow-up.
            if st.session_state.last_question_was_follow_up and len(st.session_state.history) > 1:
                st.markdown("### Previous Turn (Context for this answer)")
                # history[-2] would be the second to last item (the one before current)
                prev_q, prev_a,df_result, s_sql = st.session_state.history[-2] # Access the previous Q&A
                st.markdown(f"**Q:** {prev_q}")
                st.markdown(f"**A:** {prev_a}")
                st.markdown("---") # Separator


            # ───────────────────────────────
            # Ask Follow-up Button (activator)
            # ───────────────────────────────
            # Only show this button if there's a last question (i.e., we have something to follow up on)
            # AND we are NOT already showing the follow-up input box
            if st.session_state.last_question and not st.session_state.show_follow_up_input:
                if st.button("💬 Ask Follow-up Question", key="activate_follow_up_button"):
                    st.session_state.show_follow_up_input = True
                    st.session_state.follow_up_question_text = "" # Clear previous text in case it was re-filled
                    st.rerun() # rerun to display the new input box above the tabs

            st.markdown("---") # Separator before feedback section
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

    with tab4:
        if not st.session_state.last_df.empty and "athlete_name" in st.session_state.last_df.columns and "overall_seconds" in st.session_state.last_df.columns:
            st.markdown("### 📈 Chart: Athlete vs. Time")
            chart = alt.Chart(st.session_state.last_df).mark_bar().encode(
                x=alt.X("athlete_name:N", sort="-y", title="Athlete"),
                y=alt.Y("overall_seconds:Q", title="Overall Seconds"),
                tooltip=["athlete_name", "overall_seconds"]
            ).properties(height=400)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No chartable data (missing 'athlete_name' or 'overall_seconds' columns, or empty results).")

    # ───────────────────────────────
    # Previous Questions Log (expanded by default now)
    # ───────────────────────────────
    with st.expander("📜 Full Conversation History", expanded=True):
        if not st.session_state.history:
            st.write("No conversation history yet.")
        else:
            # Display history in reverse chronological order within this expander
            for i, (q, a,  df_result,s_sql) in enumerate(reversed(st.session_state.history)):
                st.markdown(f"**Turn {len(st.session_state.history) - i}**")
                st.markdown(f"**Q:** {q}")
                st.markdown(f"**A:** {a}")
                # TEMPORARY FIX: Remove 'key' if it's causing TypeError despite version 1.46.0
                # st.markdown("**Generated SQL:**") # Add a header for the SQL
                # st.code(s_sql, language="sql") # <--- NO INNER EXPANDER HERE
                st.markdown("---")


    with st.expander("🗳️ Feedback Log"):
        if not st.session_state.votes:
            st.write("No feedback yet.")
        else:
            for vote, q, a in reversed(st.session_state.votes):
                st.markdown(f"{vote} on **Q:** _{q}_\n> {a[:200]}...")



if __name__ == "__main__":
    main()