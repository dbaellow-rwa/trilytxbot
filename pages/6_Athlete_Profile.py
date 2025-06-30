import streamlit as st
import pandas as pd
from google.cloud import bigquery
from utils.bq_utils import load_credentials
from config.app_config import USE_LOCAL, BQ_ATHLETE_SEARCH_LOG
from utils.streamlit_utils import render_login_block, get_oauth, log_athlete_search
from utils.generate_athlete_summary import generate_athlete_summary_for_athlete
oauth2, redirect_uri = get_oauth()

# Load credentials and BigQuery client
credentials, project_id, _ = load_credentials(USE_LOCAL)
bq_client = bigquery.Client(credentials=credentials, project=project_id)

st.set_page_config(page_title="🏃 Athlete Profile Viewer", layout="wide")
st.title("🏃 Athlete Profile Viewer")

# Initialize session state
if "athlete_results_df" not in st.session_state:
    st.session_state.athlete_results_df = None



def get_athlete_race_results(client, athlete_name: str) -> pd.DataFrame:
    query = """
    SELECT
        athlete_name, athlete_country, athlete_gender, race_date, organizer,
        cleaned_race_name, race_location, race_distance, race_tier, sof,
        athlete_finishing_place, swim_time, bike_time, run_time, overall_time
    FROM `trilytx.trilytx_fct.fct_race_results`
    WHERE LOWER(athlete_name) = LOWER(@athlete)
    ORDER BY race_date DESC
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("athlete", "STRING", athlete_name)]
    )
    return client.query(query, job_config=job_config).to_dataframe()


def get_athlete_pto_score_trend(bq_client, athlete_name: str) -> pd.DataFrame:
    query = """
    WITH scores AS (
  SELECT * FROM `trilytx.trilytx_fct.fct_pto_scores_weekly`
  WHERE LOWER(athlete_name) = LOWER(@athlete_name)
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
            bigquery.ScalarQueryParameter("athlete_name", "STRING", athlete_name)
        ]
    )
    df = bq_client.query(query, job_config=job_config).to_dataframe()
    return df



# Sidebar: athlete search
with st.sidebar:
    st.markdown("### 🔍 Find an Athlete")

    athlete_query = st.text_input("Enter athlete name:", "")
    if st.button("🔍 Search Athlete"):
        if athlete_query:
            st.session_state.selected_athlete = athlete_query.strip()
        else:
            st.warning("Please enter an athlete name.")


    render_login_block(oauth2, redirect_uri)

if "selected_athlete" in st.session_state:
    log_athlete_search(bq_client, st.session_state.selected_athlete, BQ_ATHLETE_SEARCH_LOG)

    athlete_name = st.session_state.selected_athlete
    race_results_df = get_athlete_race_results(bq_client, athlete_name)
    trend_df = get_athlete_pto_score_trend(bq_client, athlete_name)

    if race_results_df.empty:
        st.warning(f"No race results found for **{athlete_name.title()}**.")
    else:
        athlete_country = race_results_df["athlete_country"].iloc[0]
        athlete_gender = race_results_df["athlete_gender"].iloc[0]
        athlete_overall_rank = trend_df["rank_overall_pto_score_by_distance_group_athlete_gender_reporting_week_desc"].iloc[0]
        athlete_national_rank = trend_df["rank_overall_pto_score_by_distance_group_athlete_gender_athlete_country_reporting_week_desc"].iloc[0]
        athlete_swim_rank = trend_df["rank_swim_pto_score_by_distance_group_athlete_gender_reporting_week_desc"].iloc[0]
        athlete_bike_rank = trend_df["rank_bike_pto_score_by_distance_group_athlete_gender_reporting_week_desc"].iloc[0]
        athlete_run_rank = trend_df["rank_run_pto_score_by_distance_group_athlete_gender_reporting_week_desc"].iloc[0]



        st.header(f"👤 Profile: {athlete_name.title()}")
        st.markdown(f"**Country:** {athlete_country}  |  **Gender:** {athlete_gender}")
        st.markdown(f"**Overall PTO Rank:** {athlete_overall_rank}  |  **National PTO Rank:** {athlete_national_rank}")
        st.markdown(f"**Swim Rank:** {athlete_swim_rank} |  **Bike Rank:** {athlete_bike_rank}  |  **Run Rank:** {athlete_run_rank}")
        # Summary
        st.markdown("### 🧠 LLM Generated Athlete Summary")
        if "user" in st.session_state:
            instructions = st.text_area("Optional LLM prompt instructions:")
            if st.button("🧠 Generate Athlete Recap"):
                with st.spinner("Generating summary - This might take 10-15 seconds..."):
                    summary = generate_athlete_summary_for_athlete(athlete_name, instructions)
                    st.markdown(summary)
        else:
            st.warning("🔒 Please log in to generate summaries.")

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
        st.dataframe(display_df.drop(columns=["athlete_name", "athlete_country", "athlete_gender"]), hide_index=True)
        trend_df = get_athlete_pto_score_trend(bq_client, athlete_name)

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
