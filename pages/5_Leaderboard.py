import streamlit as st
import pandas as pd
from google.cloud import bigquery
from utils.bq_utils import load_credentials
from config.app_config import USE_LOCAL
from utils.streamlit_utils import get_flag, render_login_block, get_oauth, make_athlete_link

# ──────────────────────────────────────────────────────────────────────────────
# Setup
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Leaderboard", layout="wide")
st.title("🏆 Current Leaderboard")
st.markdown("""
Welcome to the **Trilytx Race Leaderboard** 🏆  
This page highlights the fastest athletes across the **Swim**, **Bike**, **Run**, and **Overall** segments from recent triathlon races.

Use the filters in the sidebar to explore rankings by **distance** and **gender**.  
For each segment, you’ll see the top performers ranked by time, along with their country and race.

Whether you're scouting top talent or tracking trends, this is your podium view into the latest race data.
""")

credentials, project_id, _ = load_credentials(USE_LOCAL)
bq_client = bigquery.Client(credentials=credentials, project=project_id)

# ──────────────────────────────────────────────────────────────────────────────
# Load Leaderboard Data
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_leaderboard():
    query = """
        SELECT 'this_week' as week_name, * FROM `trilytx.trilytx_fct.fct_pto_scores_weekly` 
        WHERE reporting_week = DATE_SUB(DATE_TRUNC(CURRENT_DATE(), WEEK), INTERVAL 1 WEEK)
        AND distance_group IN ('Half-Iron (70.3 miles)', 'Iron (140.6 miles)', '100 km', 'Overall')
        UNION ALL
        SELECT 'last_week' as week_name, * FROM `trilytx.trilytx_fct.fct_pto_scores_weekly` 
        WHERE reporting_week = DATE_SUB(DATE_TRUNC(CURRENT_DATE(), WEEK), INTERVAL 2 WEEK)
        AND distance_group IN ('Half-Iron (70.3 miles)', 'Iron (140.6 miles)', '100 km', 'Overall')
    """
    return bq_client.query(query).to_dataframe()

leaderboard = get_leaderboard()

# ──────────────────────────────────────────────────────────────────────────────
# Sidebar Filters
# ──────────────────────────────────────────────────────────────────────────────
distance_options = leaderboard["distance_group"].dropna().unique().tolist()
gender_options = leaderboard["athlete_gender"].dropna().unique().tolist()

st.sidebar.header("Filter Leaderboard")
distance_filter = st.sidebar.selectbox("Distance Group", distance_options)
gender_filter = st.sidebar.selectbox("Gender", options=["All"] + gender_options)
num_rows = st.selectbox(
    "How many top athletes to show?", 
    options=[3, 5, 10, 15, 20], 
    index=0  # Default is top 3
)

# ──────────────────────────────────────────────────────────────────────────────
# Filtered View
# ──────────────────────────────────────────────────────────────────────────────
this_week = leaderboard[leaderboard["week_name"] == "this_week"].copy()
last_week = leaderboard[leaderboard["week_name"] == "last_week"].copy()


this_week = this_week[this_week["distance_group"] == distance_filter]
last_week = last_week[last_week["distance_group"] == distance_filter]

if gender_filter != "All":
    this_week = this_week[this_week["athlete_gender"] == gender_filter]
    last_week = last_week[last_week["athlete_gender"] == gender_filter]

# ──────────────────────────────────────────────────────────────────────────────
# Movement Helper
# ──────────────────────────────────────────────────────────────────────────────
def get_rank(df, col):
    return df.sort_values(col, ascending=False).reset_index(drop=True).assign(rank=lambda d: d.index + 1)

def get_movement(athlete, distance_group, gender, score_col, this_df, last_df):
    cur_rank = get_rank(
        this_df[(this_df["distance_group"] == distance_group) & (this_df["athlete_gender"] == gender)],
        score_col
    )
    prev_rank = get_rank(
        last_df[(last_df["distance_group"] == distance_group) & (last_df["athlete_gender"] == gender)],
        score_col
    )
    cur = cur_rank[cur_rank["athlete_name"] == athlete]["rank"].values
    prev = prev_rank[prev_rank["athlete_name"] == athlete]["rank"].values
    if len(cur) == 0 or len(prev) == 0:
        return "–"
    delta = prev[0] - cur[0]
    return f"↑{delta}" if delta > 0 else (f"↓{abs(delta)}" if delta < 0 else "–")

# ──────────────────────────────────────────────────────────────────────────────
# Display Leaderboards
# ──────────────────────────────────────────────────────────────────────────────
st.subheader(f"Top {num_rows} by Segment")

segment_emojis = {
    "swim_pto_score": "🏊",
    "bike_pto_score": "🚴",
    "run_pto_score": "🏃",
    "overall_pto_score": "🏆"
}

for segment in ["swim_pto_score", "bike_pto_score", "run_pto_score", "overall_pto_score"]:
    top_df = this_week.sort_values(segment, ascending=False).head(num_rows).copy()

    # Add rank as column
    top_df.insert(0, "Rank", range(1, len(top_df) + 1))

    # Add movement
    top_df["Rank Movement"] = top_df.apply(
        lambda row: get_movement(
            row['athlete_name'],
            row['distance_group'],
            row['athlete_gender'],
            segment,
            this_week,
            last_week
        ),
        axis=1
    )

    # Rename for display
    display_df = top_df[[
        "Rank", "athlete_slug", "athlete_name", "athlete_country", segment, "Rank Movement"
    ]].rename(columns={
        "athlete_name": "Athlete",
        "athlete_country": "Country",
        segment: "PTO Score",
         "Rank Movement": "Movement (vs Last Week)"
    })
            # Add hyperlinks (make sure 'athlete_slug' is still present)
    if "athlete_slug" in display_df.columns:
        display_df["athlete_slug"] = display_df["athlete_slug"]
        display_df["Athlete"] = display_df.apply(
            lambda row: make_athlete_link(row["Athlete"], row["athlete_slug"]),
            axis=1
        )
        display_df.drop(columns=["athlete_slug"], inplace=True)
            # Add country flags safely
    if "Country" in display_df.columns:
        display_df["Country"] = display_df["Country"].apply(get_flag)
    emoji = segment_emojis.get(segment, "📊")
    label = segment.replace("_pto_score", "").capitalize()

    st.markdown(f"#### {emoji} {label}")
    st.markdown(display_df.to_markdown(index=False), unsafe_allow_html=True)
