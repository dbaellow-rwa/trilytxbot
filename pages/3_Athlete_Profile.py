import streamlit as st
st.set_page_config(page_title="🏃 Athlete Profile Viewer",
    page_icon="https://github.com/dbaellow-rwa/trilytxbot/blob/fe681401e506fd4deccca9fa7c0c751c2cbbf070/assets/logo.png?raw=true",
    initial_sidebar_state="expanded",
    layout="wide")
st.title("🏃 Athlete Profile Viewer")

# Initialize session state
if "athlete_results_df" not in st.session_state:
    st.session_state.athlete_results_df = None

# ──────────────────────────────────────────────────────────────────────────────
# Cookie management for user authentication
from streamlit_cookies_manager import EncryptedCookieManager
import os
cookies = EncryptedCookieManager(prefix="trilytx_", password=os.environ["COOKIE_SECRET_TRILYTXBOT"])
if not cookies.ready():
    st.stop()
import pandas as pd
from google.cloud import bigquery
from utils.bq_utils import load_credentials
from config.app_config import USE_LOCAL, BQ_ATHLETE_SEARCH_LOG
from utils.streamlit_utils import render_login_block, get_oauth, log_athlete_search, make_race_link
from utils.generate_athlete_summary import generate_athlete_summary_for_athlete
import os
import json
oauth2, redirect_uri = get_oauth()


if "user" not in st.session_state and "user" in cookies:
    try:
        st.session_state["user"] = json.loads(cookies["user"])
    except Exception:
        st.warning("❌ Failed to decode user info.")


# Load credentials and BigQuery client
credentials, project_id, _ = load_credentials(USE_LOCAL)
bq_client = bigquery.Client(credentials=credentials, project=project_id)

# Support loading directly from ?athlete_name= query
# Sidebar: athlete search
from difflib import get_close_matches

@st.cache_data(ttl=3600)
def get_athlete_name_slug_map():
    query = """
        SELECT DISTINCT athlete_name, athlete_slug
        FROM `trilytx.trilytx_fct.fct_race_results`
        WHERE athlete_slug IS NOT NULL
        ORDER BY athlete_name
    """
    df = bq_client.query(query).to_dataframe()
    name_slug_map = {row["athlete_name"].lower(): (row["athlete_name"], row["athlete_slug"]) for _, row in df.iterrows()}
    return name_slug_map

query_params = st.query_params
if "athlete_slug" in query_params:
    st.session_state.selected_athlete_slug = query_params["athlete_slug"]
    # Reverse lookup for display name
    name_slug_map = get_athlete_name_slug_map()
    for name_lc, (display, slug) in name_slug_map.items():
        if slug == st.session_state.selected_athlete_slug:
            st.session_state.selected_athlete = display
            break




def get_athlete_race_results(client, athlete_slug: str) -> pd.DataFrame:
    query = """
    SELECT
        athlete_name, athlete_slug, athlete_country, athlete_gender, race_date, organizer,
        cleaned_race_name, unique_race_id, race_location, race_distance, race_tier, sof,
        athlete_finishing_place, swim_time, bike_time, run_time, overall_time
    FROM `trilytx.trilytx_fct.fct_race_results`
    WHERE athlete_slug = @slug
    ORDER BY race_date DESC
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("slug", "STRING", athlete_slug)]
    )
    return client.query(query, job_config=job_config).to_dataframe()


def get_athlete_pto_score_trend(bq_client, athlete_slug: str) -> pd.DataFrame:
    query = """
    WITH scores AS (
  SELECT * FROM `trilytx.trilytx_fct.fct_pto_scores_weekly`
  WHERE athlete_slug = @athlete_slug
    AND distance_group = 'Overall'
    and reporting_week <= CURRENT_DATE()
),
weeks AS (
  SELECT DISTINCT DATE(reporting_week) AS reporting_week FROM scores
),
reference_weeks AS (
  SELECT MAX(reporting_week) AS most_recent_week FROM weeks
),
target_weeks AS (
  SELECT 
    most_recent_week,
    DATE_SUB(most_recent_week, INTERVAL 6 MONTH) AS week_6mo_ago,
    DATE_SUB(most_recent_week, INTERVAL 12 MONTH) AS week_12mo_ago,
    DATE_SUB(most_recent_week, INTERVAL 24 MONTH) AS week_24mo_ago
  FROM reference_weeks
),
filtered_targets AS (
  SELECT MAX(reporting_week) AS reporting_week, '6 Months Ago' AS week_type
  FROM weeks, target_weeks WHERE reporting_week <= week_6mo_ago
  UNION ALL
  SELECT MAX(reporting_week), '12 Months Ago'
  FROM weeks, target_weeks WHERE reporting_week <= week_12mo_ago
  UNION ALL
  SELECT MAX(reporting_week), '24 Months Ago'
  FROM weeks, target_weeks WHERE reporting_week <= week_24mo_ago
  UNION ALL
  SELECT most_recent_week, 'Current' FROM target_weeks
),
filtered AS (
  SELECT t.*, f.week_type
  FROM scores t
  JOIN filtered_targets f ON DATE(t.reporting_week) = f.reporting_week
)
SELECT * FROM filtered
ORDER BY reporting_week DESC
"""
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("athlete_slug", "STRING", athlete_slug)
        ]
    )
    df = bq_client.query(query, job_config=job_config).to_dataframe()
    return df




# Sidebar: athlete search
with st.sidebar:
    st.markdown("### 🔍 Find an Athlete")

    name_slug_map = get_athlete_name_slug_map()
    athlete_names_lower = list(name_slug_map.keys())

    search_input = st.text_input("Enter athlete name:", "")

    if search_input:
        search_input_lc = search_input.lower()
        close_matches_lc = get_close_matches(search_input_lc, athlete_names_lower, n=10, cutoff=0.5)

        if close_matches_lc:
            # recover original casing from the mapping
            display_names = [name_slug_map[name][0] for name in close_matches_lc]
            selected_name_display = st.selectbox("Select a matching athlete", display_names)

            if st.button("🔍 Search Athlete"):
                # recover the slug from the display name (reverse lookup)
                for name_lc, (display, slug) in name_slug_map.items():
                    if display == selected_name_display:
                        st.session_state.selected_athlete = display
                        st.session_state.selected_athlete_slug = slug
                        st.query_params.clear()
                        break
        else:
            st.warning("No close matches found. Try refining your input.")
    else:
        st.markdown("💡 Try selecting from example athletes:")
        example_athletes = {
            "🌊 Ashleigh Gentle": "Ashleigh Gentle",
            "🔥 Gustav Iden": "Gustav Iden",
            "⚡ Lionel Sanders": "Lionel Sanders",
            "🌍 Taylor Knibb": "Taylor Knibb",
            "🚴 Sam Long": "Sam Long"
        }
        for button_text, athlete_name in example_athletes.items():
            if st.button(button_text, key=f"example_{hash(athlete_name)}"):
                st.session_state.selected_athlete = athlete_name
                entry = name_slug_map.get(athlete_name.lower())
                if entry:
                    st.session_state.selected_athlete = entry[0]  # original name
                    st.session_state.selected_athlete_slug = entry[1]  # slug
                    st.query_params.clear()
                    st.rerun()
    if st.button("🔁 Reset Search"):
        for key in ["selected_athlete", "selected_athlete_slug", "athlete_results_df"]:
            if key in st.session_state:
                del st.session_state[key]
        st.query_params.clear()  # 👈 Clear the URL query string    
        st.rerun()
    def render_login_block(oauth2, redirect_uri, cookies))


if "selected_athlete" in st.session_state and "selected_athlete_slug" in st.session_state:
    athlete_name = st.session_state.selected_athlete
    athlete_slug = st.session_state.selected_athlete_slug

    log_athlete_search(bq_client, athlete_slug, BQ_ATHLETE_SEARCH_LOG)

    race_results_df = get_athlete_race_results(bq_client, athlete_slug)
    trend_df = get_athlete_pto_score_trend(bq_client, athlete_slug)

    if race_results_df.empty:
        st.warning(f"No race results found for **{athlete_name.title()}**.")
    else:
        athlete_country = race_results_df["athlete_country"].iloc[0]
        athlete_gender = race_results_df["athlete_gender"].iloc[0]
        athlete_overall_rank = trend_df["rank_overall_pto_score_by_distance_group_athlete_gender_reporting_week_desc"].iloc[0]
        athlete_overall_swim_rank = trend_df["rank_swim_pto_score_by_distance_group_athlete_gender_reporting_week_desc"].iloc[0]
        athlete_overall_bike_rank = trend_df["rank_bike_pto_score_by_distance_group_athlete_gender_reporting_week_desc"].iloc[0]
        athlete_overall_run_rank = trend_df["rank_run_pto_score_by_distance_group_athlete_gender_reporting_week_desc"].iloc[0]

        athlete_national_rank = trend_df["rank_overall_pto_score_by_distance_group_athlete_gender_athlete_country_reporting_week_desc"].iloc[0]
        athlete_national_swim_rank = trend_df["rank_swim_pto_score_by_distance_group_athlete_gender_athlete_country_reporting_week_desc"].iloc[0]
        athlete_national_bike_rank = trend_df["rank_bike_pto_score_by_distance_group_athlete_gender_athlete_country_reporting_week_desc"].iloc[0]
        athlete_national_run_rank = trend_df["rank_run_pto_score_by_distance_group_athlete_gender_athlete_country_reporting_week_desc"].iloc[0]



        st.header(f"{athlete_name.title()}")
        st.markdown(f"**Country:** {athlete_country}  |  **Gender:** {athlete_gender}")
        st.markdown(f"**Overall PTO Rank:** {athlete_overall_rank}  |  **Overall Swim Rank:** {athlete_overall_swim_rank} |  **Overall Bike Rank:** {athlete_overall_bike_rank}  |  **Overall Run Rank:** {athlete_overall_run_rank}")
        st.markdown(f"**National PTO Rank:** {athlete_national_rank}  |  **National Swim Rank:** {athlete_national_swim_rank} |  **National Bike Rank:** {athlete_national_bike_rank}  |  **National Run Rank:** {athlete_national_run_rank}")
        # Summary
        st.markdown("### 🧠 LLM Generated Athlete Summary")

        if st.session_state.get("user") is not None:
            instructions = st.text_area("Optional LLM prompt instructions:")
            
            if st.button("🧠 Generate Athlete Recap"):
                with st.spinner("Generating summary - This might take 10–15 seconds..."):
                    summary = generate_athlete_summary_for_athlete(athlete_name, instructions)
                    st.markdown(summary)
        else:
            st.warning("🔒 Please log in on the home page to generate summaries.")


        st.markdown("### 📈 Race History")
        display_df = race_results_df.rename(columns={
            "race_date": "Date",
            "organizer": "Organizer",
            "cleaned_race_name": "Race",
            "race_distance": "Distance",
            "race_location": "Location",
            "race_tier": "Race Tier",
            "sof": "Strength of Field",
            
            "athlete_finishing_place": "Place",
            "swim_time": "Swim",
            "bike_time": "Bike",
            "run_time": "Run",
            "overall_time": "Finish Time"
        })
        display_df["Race"] = display_df.apply(
            lambda row: make_race_link(row["Race"], row["unique_race_id"]),
            axis=1
        )
        display_df.drop(columns=["athlete_slug", "unique_race_id", "athlete_name", "athlete_country", "athlete_gender"], inplace=True)
        # Add medal emojis for top 3 places
        if "Place" in display_df.columns:
            # Convert to numeric, coercing errors to NaN.
            display_df["Place_numeric"] = pd.to_numeric(display_df["Place"], errors='coerce')

            # Apply emojis based on numeric place, handling NaN gracefully
            display_df["Place"] = display_df.apply(lambda row: 
                f"🥇 {int(row['Place_numeric'])}" if pd.notna(row['Place_numeric']) and row['Place_numeric'] == 1 else
                f"🥈 {int(row['Place_numeric'])}" if pd.notna(row['Place_numeric']) and row['Place_numeric'] == 2 else
                f"🥉 {int(row['Place_numeric'])}" if pd.notna(row['Place_numeric']) and row['Place_numeric'] == 3 else
                "❌ DNF" if pd.isna(row['Place_numeric']) else str(row["Place"])
            , axis=1)
            
            # Drop the temporary numeric column
            display_df.drop(columns=["Place_numeric"], inplace=True)

        st.markdown(display_df.to_markdown(index=False), unsafe_allow_html=True)
        if trend_df.empty:
            st.warning("No PTO score trend data found.")
        else:
            st.subheader("📈 PTO Score Trend")
            st.dataframe(trend_df[[
                "reporting_week",
                "week_type",
                "swim_pto_score",
                "rank_swim_pto_score_by_distance_group_athlete_gender_reporting_week_desc",
                "bike_pto_score",
                "rank_bike_pto_score_by_distance_group_athlete_gender_reporting_week_desc",
                "run_pto_score",
                "rank_run_pto_score_by_distance_group_athlete_gender_reporting_week_desc",
                "overall_pto_score",
                "rank_overall_pto_score_by_distance_group_athlete_gender_reporting_week_desc"
            ]].rename(columns={
                "reporting_week": "Week",
                "week_type": "Period",
                "swim_pto_score": "Swim Score",
                "rank_swim_pto_score_by_distance_group_athlete_gender_reporting_week_desc": "Swim Rank (Same Gender)",
                "bike_pto_score": "Bike Score",
                "rank_bike_pto_score_by_distance_group_athlete_gender_reporting_week_desc": "Bike Rank (Same Gender)",  
                "run_pto_score": "Run Score",
                "rank_run_pto_score_by_distance_group_athlete_gender_reporting_week_desc": "Run Rank (Same Gender)",
                "overall_pto_score": "PTO Score",
                "rank_overall_pto_score_by_distance_group_athlete_gender_reporting_week_desc": "Overall Rank (Same Gender)"
            }), hide_index=True)
        
else:
    st.info("🔍 Use the sidebar to search for an athlete.")
