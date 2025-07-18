import datetime
import streamlit as st
import pandas as pd
from google.cloud import bigquery
import requests as pyrequests
import os
import json
import requests as pyrequests  # rename to avoid conflict with google.auth.transport.requests
from streamlit_oauth import OAuth2Component
from config.app_config import USE_LOCAL
import requests as pyrequests
import os
import json
import requests as pyrequests  # rename to avoid conflict with google.auth.transport.requests
from streamlit_oauth import OAuth2Component
from config.app_config import USE_LOCAL

def log_athlete_search(bq_client: bigquery.Client,  athlete_slug: str, full_table_path: str,):
    user_email = st.session_state.get("user", {}).get("email", "unknown")

    row = {
        "athlete_slug": athlete_slug,
        "user_email": user_email,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    errors = bq_client.insert_rows_json(full_table_path, [row])
    if errors:
        st.error(f"Failed logging search: {errors}")

def log_race_search(bq_client: bigquery.Client,  race_id: str, full_table_path: str,):
    user_email = st.session_state.get("user", {}).get("email", "unknown")

    row = {
        "unique_race_id": race_id,
        "user_email": user_email,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    errors = bq_client.insert_rows_json(full_table_path, [row])
    if errors:
        st.error(f"Failed logging search: {errors}")
def log_race_recap_generate(bq_client: bigquery.Client,  race_id: str, full_table_path: str,):
    user_email = st.session_state.get("user", {}).get("email", "unknown")

    row = {
        "unique_race_id": race_id,
        "user_email": user_email,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    errors = bq_client.insert_rows_json(full_table_path, [row])
    if errors:
        st.error(f"Failed logging recap: {errors}")
def log_vote_to_bq(client: bigquery.Client, full_table_path: str, vote_type: str, question: str, summary: str):
    """
    Logs user feedback (upvote/downvote) to a specified BigQuery table.

    Args:
        client (bigquery.Client): An initialized BigQuery client.
        full_table_path (str): The full BigQuery table path (e.g., "project.dataset.table").
        vote_type (str): The type of vote ("UP" for 👍, "DOWN" for 👎).
        question (str): The original question asked by the user.
        summary (str): The summary provided by the chatbot.
    """
    user_email = st.session_state.get("user", {}).get("email", "unknown")
    question_id = st.session_state.get("question_id", "unknown")
    rows = [{
        "vote_type": vote_type,
        "question_id": question_id,
        "user_email": user_email,
        "question_id": question_id,
        "user_email": user_email,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }]
    errors = client.insert_rows_json(full_table_path, rows)
    if errors:
        st.error(f"🔴 Error logging vote to BigQuery: {errors}")

def log_chatbot_question_to_bq(client: bigquery.Client, full_table_path: str, question: str, sql: str, summary: str, is_follow_up=False, previous_question=None, context_history=None):
    """
    Logs a user interaction (question, generated SQL, and summary) to a specified BigQuery table.

    Args:
        client (bigquery.Client): An initialized BigQuery client.
        full_table_path (str): The full BigQuery table path (e.g., "project.dataset.table").
        question (str): The original question asked by the user.
        sql (str): The SQL query generated by the chatbot.
        summary (str): The natural language summary provided by the chatbot.
    """
    question_id = st.session_state.get("question_id", "unknown")
    user_email = st.session_state.get("user", {}).get("email", "unknown")
    question_id = st.session_state.get("question_id", "unknown")
    user_email = st.session_state.get("user", {}).get("email", "unknown")
    rows = [{
        "question": question,
        "question_id": question_id,
        "user_email": user_email,
        "question_id": question_id,
        "user_email": user_email,
        "generated_sql": sql,
        "summary": summary,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "is_follow_up": str(is_follow_up).lower(),
        "previous_question": previous_question or "",
        "context_history": context_history or ""
    }]
    errors = client.insert_rows_json(full_table_path, rows)
    if errors:
        st.error(f"🔴 Error logging interaction to BigQuery: {errors}")


def log_error_to_bq(client: bigquery.Client, full_table_path: str, question: str, sql: str, error_msg: str, attempt: int):
    """
    Logs an error that occurred during SQL generation or BigQuery execution to a specified table.

    Args:
        client (bigquery.Client): An initialized BigQuery client.
        full_table_path (str): The full BigQuery table path (e.g., "project.dataset.table").
        question (str): The original question asked by the user.
        sql (str): The SQL query (if any) that caused the error.
        error_msg (str): The error message.
        attempt (int): The attempt number at which the error occurred.
    """
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

def log_zero_result_to_bq(bq_client: bigquery.Client, table_name: str, question: str, sql: str, attempt_number: int):
    """
    Logs instances where a generated SQL query returned no results to a specified table.

    Args:
        bq_client (bigquery.Client): An initialized BigQuery client.
        table_name (str): The full BigQuery table path (e.g., "project.dataset.table").
        question (str): The original question asked by the user.
        sql (str): The SQL query that returned no results.
        attempt_number (int): The attempt number at which zero results were returned.
    """
    rows_to_insert = [{
        "question": question,
        "sql": sql,
        "attempt_number": attempt_number,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }]
    errors = bq_client.insert_rows_json(table_name, rows_to_insert)
    if errors:
        st.error(f"🔴 Failed to log zero result to BigQuery: {errors}")



# config.py or streamlit_utils.py
def get_oauth():
    oauth2 = OAuth2Component(
        client_id=os.environ.get("GOOGLE_CLIENT_ID_TRILYTXBOT"),
        client_secret=os.environ.get("GOOGLE_CLIENT_SECRET_TRILYTXBOT"),
        authorize_endpoint="https://accounts.google.com/o/oauth2/auth",
        token_endpoint="https://oauth2.googleapis.com/token",
        # redirect_uri="https://www.trilytx.com" if not USE_LOCAL else "http://localhost:8501/",
        scope="openid email profile",
        user_info_endpoint="https://openidconnect.googleapis.com/v1/userinfo"
    )
    return oauth2

import streamlit as st
import streamlit.components.v1 as components
import json

from streamlit_cookies_manager import EncryptedCookieManager

# Setup cookie manager
# cookies = EncryptedCookieManager(prefix="trilytx_", password=os.environ["COOKIE_SECRET_TRILYTXBOT"])
# if not cookies.ready():
#     st.stop()  # Wait until cookies are ready

def render_login_block(oauth2, redirect_uri, cookies):
    # This block tries to load user from cookie if not in session state
    # This is fine for initial load or new page, but the main app.py also has this logic.
    # It's better to have this single source of truth for loading from cookies:
    # `if "user" not in st.session_state and "user" in cookies:` in your main app.py
    # so we don't duplicate cookie loading logic.
    # Let's assume the main app.py handles the initial cookie load into session_state.
    # So, we'll focus on saving to cookie after successful login here.

    if "user" in st.session_state:
        user_info = st.session_state["user"]
        st.success(f"Welcome, {user_info.get('name', 'triathlete')} 👋")
        st.image(user_info.get("picture", ""), width=80)
        st.markdown(f"**Email:** {user_info.get('email')}")

        if st.button("Logout"):
            st.session_state.pop("user", None)
            cookies["user"] = ""  # This effectively deletes it
            cookies.save()
            st.rerun()
    else:
        # User not in session_state, display login button
        token = oauth2.authorize_button(
            name="🟢 Login with Google",
            redirect_uri=redirect_uri,
            scope="openid email profile"
        )

        if token:
            raw_token = token.get("token")
            if raw_token and "access_token" in raw_token:
                import requests as pyrequests
                response = pyrequests.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {raw_token['access_token']}"}
                )
                if response.status_code == 200:
                    user_info = response.json()
                    st.session_state["user"] = user_info
                    cookies["user"] = json.dumps(user_info)
                    cookies.save()
                    st.rerun()

        st.markdown("""
        <div style="background-color:#e0f0ff;padding:10px;border-radius:10px;text-align:center;">
            👆 <strong style="color:black;">Please log in with Google to access full features.</strong>
        </div>
        """, unsafe_allow_html=True)

# config.py or streamlit_utils.py (this part is fine)
def get_oauth():
    # Make sure OAuth2Component is imported globally in this file or passed in
    from streamlit_oauth import OAuth2Component # Added for clarity, assuming it's from this library

    oauth2 = OAuth2Component(
        client_id=os.environ.get("GOOGLE_CLIENT_ID_TRILYTXBOT"),
        client_secret=os.environ.get("GOOGLE_CLIENT_SECRET_TRILYTXBOT"),
        authorize_endpoint="https://accounts.google.com/o/oauth2/auth",
        token_endpoint="https://oauth2.googleapis.com/token"
    )

    # Ensure USE_LOCAL is accessible here (imported or passed in)
    # This might be defined in app_config.py, so ensure it's imported or globally available
    # For now, assuming it's available.
    redirect_uri = "https://www.trilytx.com" if not USE_LOCAL else "http://localhost:8501"

    return oauth2, redirect_uri
import urllib.parse

def make_athlete_link(name: str, slug: str) -> str:
    import urllib.parse
    encoded_slug = urllib.parse.quote(slug)
    return f'<a href="/Athlete_Profile?athlete_slug={encoded_slug}" target="_self">{name}</a>'

def make_race_link(name: str, race_id: str) -> str:
    import urllib.parse
    encoded_id = urllib.parse.quote(race_id)
    return f'<a href="/Race_Results?unique_race_id={encoded_id}" target="_self">{name}</a>'

import pycountry

def get_flag(country_value):
    try:
        country = pycountry.countries.lookup(country_value)
        code = country.alpha_2.lower()

        # Build emoji flag from country code
        return f"<img src='https://flagicons.lipis.dev/flags/4x3/{code}.svg' height='16' style='vertical-align:middle; margin-right:4px;'> {country_value}"
    except:
        pass


def init_cookies_and_restore_user():
    from streamlit_cookies_manager import EncryptedCookieManager

    cookies = EncryptedCookieManager(prefix="trilytx_", password=os.environ["COOKIE_SECRET_TRILYTXBOT"])
    if not cookies.ready():
        st.stop()

    if "user" not in st.session_state and "user" in cookies:
        try:
            cookie_value = cookies["user"]
            if cookie_value:
                st.session_state["user"] = json.loads(cookie_value)
        except Exception:
            cookies["user"] = ""  # Clear corrupted value
            cookies.save()
            st.warning("❌ Failed to decode user info from cookie.")

    return cookies
