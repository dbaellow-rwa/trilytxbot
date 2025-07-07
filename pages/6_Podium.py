import streamlit as st
st.set_page_config(page_title="Trilytx Race Podiums",
    page_icon="https://github.com/dbaellow-rwa/trilytxbot/blob/fe681401e506fd4deccca9fa7c0c751c2cbbf070/assets/logo.png?raw=true",
    initial_sidebar_state="expanded",
    layout="wide")
st.title("🏁 Race Podiums")
st.markdown("""
Welcome to the **Trilytx Race Podiums** dashboard.  
Here you’ll find the top 3 segment performers (Swim, Bike, Run, and Overall) for each gender and distance group based on race results.

Use the filters in the sidebar to view podiums for a specific race distance and gender.  
Each segment podium displays athletes ranked by time, along with their country and race name.
""")
# Cookie management for user authentication
from streamlit_cookies_manager import EncryptedCookieManager
import os
cookies = EncryptedCookieManager(prefix="trilytx_", password=os.environ["COOKIE_SECRET_TRILYTXBOT"])
if not cookies.ready():
    st.stop()
import pandas as pd
from google.cloud import bigquery
from utils.bq_utils import load_credentials
from config.app_config import USE_LOCAL
from utils.streamlit_utils import make_race_link, make_athlete_link, get_flag

# ──────────────────────────────────────────────────────────────────────────────
# Setup
# ──────────────────────────────────────────────────────────────────────────────

if "filters_initialized" not in st.session_state:
    st.session_state.time_range = "Last 365 Days"
    st.session_state.selected_distance = None
    st.session_state.selected_gender = "All"
    st.session_state.selected_organizer = "All"
    st.session_state.selected_country = "All"
    st.session_state.selected_yob = "All"
    st.session_state.num_rows = 3
    st.session_state.search_triggered = False
    st.session_state.filters_initialized = True





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
# Sidebar filters + Submit Button
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("🎛️ Filter Podium Search")

    # Reset Button


    # Time range selection
    st.session_state.time_range = st.selectbox(
        "Select Time Range:",
        [
            "Last Week",
            "Current Calendar Month",
            "Current Calendar Year",
            "Last 365 Days",
            "Last 30 Days",
            "Last 90 Days",
            "Last 180 Days"
        ],
        index=[
            "Last Week",
            "Current Calendar Month",
            "Current Calendar Year",
            "Last 365 Days",
            "Last 30 Days",
            "Last 90 Days",
            "Last 180 Days"
        ].index(st.session_state.time_range)
    )

    dummy_df = get_race_podiums("Last 365 Days")
    distances = sorted(dummy_df["race_distance"].dropna().unique())
    genders = sorted(dummy_df["race_gender"].dropna().unique())
    organizers = sorted(dummy_df["organizer"].dropna().unique())
    country_options = sorted(dummy_df["athlete_country"].dropna().unique())
    birth_year_options = sorted(dummy_df["athlete_year_of_birth"].dropna().unique(), reverse=True)

    # Set default index for distance if value exists
    default_distance_idx = distances.index(st.session_state.selected_distance) if st.session_state.selected_distance in distances else 0

    st.session_state.selected_distance = st.selectbox("Select Race Distance:", distances, index=default_distance_idx)
    st.session_state.selected_gender = st.selectbox("Select Athlete Gender:", ["All"] + genders, index=(["All"] + genders).index(st.session_state.selected_gender))
    st.session_state.selected_organizer = st.selectbox("Select Race Organizer:", ["All"] + organizers, index=(["All"] + organizers).index(st.session_state.selected_organizer))
    st.session_state.selected_country = st.selectbox("Select Athlete Country", ["All"] + country_options, index=(["All"] + country_options).index(st.session_state.selected_country))
    st.session_state.selected_yob = st.selectbox("Select Athlete Birth Year", ["All"] + birth_year_options, index=(["All"] + birth_year_options).index(st.session_state.selected_yob))
    st.session_state.num_rows = st.selectbox("How many top athletes to show?", options=[3, 5, 10, 15, 20], index=[3, 5, 10, 15, 20].index(st.session_state.num_rows))

    st.session_state.search_triggered = st.button("🔍 Search Podium")
    if st.button("🔄 Reset Filters"):
        st.session_state.time_range = "Last 365 Days"
        st.session_state.selected_distance = None
        st.session_state.selected_gender = "All"
        st.session_state.selected_organizer = "All"
        st.session_state.selected_country = "All"
        st.session_state.selected_yob = "All"
        st.session_state.num_rows = 3
        st.session_state.search_triggered = False
        st.rerun()


# ─────────────────────────────────────────────
# Load + Filter Data Only After Button Press
# ─────────────────────────────────────────────
if st.session_state.search_triggered:
    podium_df = get_race_podiums(st.session_state.time_range)

    # Apply filters
    filtered_df = podium_df[podium_df["race_distance"] == st.session_state.selected_distance]

    if st.session_state.selected_organizer != "All":
        filtered_df = filtered_df[filtered_df["organizer"] == st.session_state.selected_organizer]
    if st.session_state.selected_country != "All":
        filtered_df = filtered_df[filtered_df["athlete_country"] == st.session_state.selected_country]
    if st.session_state.selected_gender != "All":
        filtered_df = filtered_df[filtered_df["race_gender"] == st.session_state.selected_gender]
    if st.session_state.selected_yob != "All":
        filtered_df = filtered_df[filtered_df["athlete_year_of_birth"] == st.session_state.selected_yob]

    if filtered_df.empty:
        st.warning("📭 No race podium data found for the selected filters.")
        st.stop()

    segment_map = {
        "swim_seconds": ("🏊 Swim", "swim_time"),
        "bike_seconds": ("🚴 Bike", "bike_time"),
        "run_seconds": ("🏃 Run", "run_time"),
        "overall_seconds": ("🏁 Overall", "overall_time")
    }

    for segment_col, (label, time_col) in segment_map.items():
        top_df = filtered_df.sort_values(segment_col).head(st.session_state.num_rows).copy()
        top_df.insert(0, "Rank", range(1, len(top_df) + 1))


        display_df = top_df[[
            "Rank", "athlete_slug", "unique_race_id", "athlete_name", "athlete_country", "race_date",  "organizer", "cleaned_race_name", time_col
        ]].rename(columns={
            "athlete_name": "Athlete",
            "athlete_country": "Country",
            "race_date": "Race Date",
            "organizer": "Organizer",
            "cleaned_race_name": "Race",
            time_col: "Time"
        })
        if "athlete_slug" in display_df.columns:
            display_df["athlete_slug"] = display_df["athlete_slug"]
            display_df["Athlete"] = display_df.apply(
                lambda row: make_athlete_link(row["Athlete"], row["athlete_slug"]),
                axis=1
            )
            display_df.drop(columns=["athlete_slug"], inplace=True)
        display_df["Race"] = display_df.apply(
                lambda row: make_race_link(row["Race"], row["unique_race_id"]),
                axis=1
            )
        display_df.drop(columns=["unique_race_id"], inplace=True)
        if "Country" in display_df.columns:
            display_df["Country"] = display_df["Country"].apply(get_flag)

        st.markdown(f"### {label} Podium")
        st.markdown(display_df.to_markdown(index=False), unsafe_allow_html=True)

