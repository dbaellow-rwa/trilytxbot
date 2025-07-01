import streamlit as st
import pandas as pd
from google.cloud import bigquery
from utils.bq_utils import load_credentials
from config.app_config import USE_LOCAL
from utils.streamlit_utils import render_login_block, get_oauth, make_athlete_link, get_flag

# ──────────────────────────────────────────────────────────────────────────────
# Setup
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Trilytx Race Podiums", layout="wide")
st.title("🏁 Race Race Podiums")
st.markdown("""
Welcome to the **Trilytx Race Podiums** dashboard.  
Here you’ll find the top 3 segment performers (Swim, Bike, Run, and Overall) for each gender and distance group based on race results.

Use the filters in the sidebar to view podiums for a specific race distance and gender.  
Each segment podium displays athletes ranked by time, along with their country and race name.
""")
credentials, project_id, _ = load_credentials(USE_LOCAL)
bq_client = bigquery.Client(credentials=credentials, project=project_id)

@st.cache_data(ttl=3600)
def get_race_podiums(time_range: str):
    if time_range == "Last Week":
        date_filter = "DATE_TRUNC(race_date, WEEK(SUNDAY)) = DATE_TRUNC(CURRENT_DATE(), WEEK(SUNDAY))"
    elif time_range == "Current Calendar Month":
        date_filter = "DATE_TRUNC(race_date, MONTH) = DATE_TRUNC(CURRENT_DATE(), MONTH)"
    elif time_range == "Current Calendar Year":
        date_filter = "DATE_TRUNC(race_date, YEAR) = DATE_TRUNC(CURRENT_DATE(), YEAR)"
    elif time_range == "Last 365 Days":
        date_filter = "race_date >= date_sub(CURRENT_DATE(), interval 365 day)"
    elif time_range == "Last 30 Days":
        date_filter = "race_date >= date_sub(CURRENT_DATE(), interval 30 day)"
    elif time_range == "Last 90 Days":
        date_filter = "race_date >= date_sub(CURRENT_DATE(), interval 90 day)"
    elif time_range == "Last 180 Days":
        date_filter = "race_date >= date_sub(CURRENT_DATE(), interval 90 day)"
    else:
        raise ValueError("Invalid time_range")

    query = f"""
        
            SELECT * replace(
              CASE 
    WHEN swim_seconds IS  NULL or bike_seconds IS  NULL or run_seconds IS  NULL 
    THEN NULL 
    ELSE overall_seconds 
  END AS overall_seconds
  ) FROM `trilytx.trilytx_fct.fct_race_results`
            WHERE {date_filter}
              AND race_name IS NOT NULL
              and race_distance IS NOT NULL
              and race_distance != ''

    """
    return bq_client.query(query).to_dataframe()

# ─────────────────────────────────────────────
# Tab selector for Weekly / Monthly / Yearly
# ─────────────────────────────────────────────
time_range = st.selectbox("Select Time Range:", [
    "Last Week",
    "Current Calendar Month",
    "Current Calendar Year",
    "Last 365 Days",
    "Last 30 Days",
    "Last 90 Days",
    "Last 180 Days"
], index=0)
podium_df = get_race_podiums(time_range)

if podium_df.empty:
    st.warning(f"📭 No race podium data available for the selected time period: {time_range}.")
    st.stop()

# ─────────────────────────────────────────────
# Sidebar filters
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("🎛️ Filter Leaderboard")
    distances = sorted(podium_df["race_distance"].dropna().unique())
    genders = sorted(podium_df["race_gender"].dropna().unique())
    organizers = sorted(podium_df["organizer"].dropna().unique())

    selected_distance = st.selectbox("Select Distance:", distances, index=0)
    selected_gender = st.selectbox("Select Gender:", genders, index=0)
    selected_organizer = st.selectbox("Select Organizer:", ["All"] + organizers, index=0)
    num_rows = st.selectbox(
        "How many top athletes to show?", 
        options=[3, 5, 10, 15, 20], 
        index=0  # Default is top 3
    )

filtered_df = podium_df[
    (podium_df["race_distance"] == selected_distance) &
    (podium_df["race_gender"] == selected_gender)
]

if selected_organizer != "All":
    filtered_df = filtered_df[filtered_df["organizer"] == selected_organizer]

if filtered_df.empty:
    st.info("No data for selected distance and gender.")
    st.stop()

segment_map = {
    "swim_seconds": ("🏊 Swim", "swim_time"),
    "bike_seconds": ("🚴 Bike", "bike_time"),
    "run_seconds": ("🏃 Run", "run_time"),
    "overall_seconds": ("🏁 Overall", "overall_time")
}

for segment_col, (label, time_col) in segment_map.items():
    top_df = filtered_df.sort_values(segment_col).head(num_rows).copy()
    top_df.insert(0, "Rank", range(1, len(top_df) + 1))


    display_df = top_df[[
        "Rank", "athlete_slug", "athlete_name", "athlete_country", "race_date", time_col, "organizer", "cleaned_race_name"
    ]].rename(columns={
        "athlete_name": "Athlete",
        "athlete_country": "Country",
        "race_date": "Race Date",
        time_col: "Time",
        "organizer": "Organizer",
        "cleaned_race_name": "Race"
    })
    if "athlete_slug" in display_df.columns:
        display_df["athlete_slug"] = display_df["athlete_slug"]
        display_df["Athlete"] = display_df.apply(
            lambda row: make_athlete_link(row["Athlete"], row["athlete_slug"]),
            axis=1
        )
        display_df.drop(columns=["athlete_slug"], inplace=True)
    if "Country" in display_df.columns:
        display_df["Country"] = display_df["Country"].apply(get_flag)

    st.markdown(f"### {label} Podium")
    st.markdown(display_df.to_markdown(index=False), unsafe_allow_html=True)

