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
            WITH base AS (
            SELECT * FROM `trilytx.trilytx_fct.fct_pto_scores_weekly`
            WHERE distance_group IN ('Half-Iron (70.3 miles)', 'Iron (140.6 miles)', '100 km', 'Overall')
            ),
            weeks AS (
            SELECT
                DATE_SUB(DATE_TRUNC(CURRENT_DATE(), WEEK), INTERVAL 1 WEEK) AS this_week,
                DATE_SUB(DATE_TRUNC(CURRENT_DATE(), WEEK), INTERVAL 2 WEEK) AS last_week,
                DATE_SUB(DATE_TRUNC(CURRENT_DATE(), WEEK), INTERVAL 26 WEEK) AS week_6mo_ago
            )
            SELECT 'this_week' AS week_name, b.*
            FROM base b JOIN weeks w ON b.reporting_week = w.this_week

            UNION ALL

            SELECT 'last_week' AS week_name, b.*
            FROM base b JOIN weeks w ON b.reporting_week = w.last_week

            UNION ALL

            SELECT '6mo_ago' AS week_name, b.*
            FROM base b JOIN weeks w ON b.reporting_week = w.week_6mo_ago

    """
    return bq_client.query(query).to_dataframe()

leaderboard = get_leaderboard()

# ──────────────────────────────────────────────────────────────────────────────
# Sidebar Filters
# ──────────────────────────────────────────────────────────────────────────────
distance_options = leaderboard["distance_group"].dropna().unique().tolist()
gender_options = leaderboard["athlete_gender"].dropna().unique().tolist()
country_options = leaderboard["athlete_country"].dropna().unique().tolist()
birth_year_options = sorted(leaderboard["athlete_year_of_birth"].dropna().unique(), reverse=True)

st.sidebar.header("Filter Leaderboard")

distance_default_index = distance_options.index("Overall") if "Overall" in distance_options else 0
distance_filter = st.sidebar.selectbox("Distance Group", distance_options, index=distance_default_index)
gender_filter = st.sidebar.selectbox("Gender", options=["All"] + gender_options, index=0)
country_filter = st.sidebar.selectbox("Country", options=["All"] + sorted(country_options), index=0)
yob_filter = st.sidebar.selectbox("Year of Birth", options=["All"] + sorted(birth_year_options), index=0)

num_rows = st.sidebar.selectbox(
    "How many top athletes to show?", 
    options=[3, 5, 10, 15, 20], 
    index=0
)


# ──────────────────────────────────────────────────────────────────────────────
# Filtered View
# ──────────────────────────────────────────────────────────────────────────────
this_week = leaderboard[leaderboard["week_name"] == "this_week"].copy()
last_week = leaderboard[leaderboard["week_name"] == "last_week"].copy()
six_months_ago = leaderboard[leaderboard["week_name"] == "6mo_ago"].copy()

this_week = this_week[this_week["distance_group"] == distance_filter]
last_week = last_week[last_week["distance_group"] == distance_filter]
six_months_ago = six_months_ago[six_months_ago["distance_group"] == distance_filter]

if gender_filter != "All":
    this_week = this_week[this_week["athlete_gender"] == gender_filter]
    last_week = last_week[last_week["athlete_gender"] == gender_filter]
    six_months_ago = six_months_ago[six_months_ago["athlete_gender"] == gender_filter]

if country_filter != "All":
    this_week = this_week[this_week["athlete_country"] == country_filter]
    last_week = last_week[last_week["athlete_country"] == country_filter]
    six_months_ago = six_months_ago[six_months_ago["athlete_country"] == country_filter]

if yob_filter != "All":
    this_week = this_week[this_week["athlete_year_of_birth"] == yob_filter]
    last_week = last_week[last_week["athlete_year_of_birth"] == yob_filter]
    six_months_ago = six_months_ago[six_months_ago["athlete_year_of_birth"] == yob_filter]

# ──────────────────────────────────────────────────────────────────────────────
# Movement Helper
# ──────────────────────────────────────────────────────────────────────────────
def get_rank(df, score_col):
    return df.sort_values(score_col, ascending=False).reset_index(drop=True).assign(rank=lambda d: d.index + 1)

def get_movement(athlete, gender, distance_group, score_col, current_df, comparison_df):
    cur_rank = get_rank(
        current_df[(current_df["distance_group"] == distance_group) & (current_df["athlete_gender"] == gender)],
        score_col
    )
    cmp_rank = get_rank(
        comparison_df[(comparison_df["distance_group"] == distance_group) & (comparison_df["athlete_gender"] == gender)],
        score_col
    )
    cur = cur_rank[cur_rank["athlete_name"] == athlete]["rank"].values
    cmp = cmp_rank[cmp_rank["athlete_name"] == athlete]["rank"].values
    if len(cur) == 0 or len(cmp) == 0:
        return "🆕"
    delta = cmp[0] - cur[0]
    if delta > 0:
        return f"🟩↑ {delta}"
    elif delta < 0:
        return f"🟥↓ {abs(delta)}"
    else:
        return "⬜–"



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

    top_df["Rank Movement (1W)"] = top_df.apply(
        lambda row: get_movement(
            row['athlete_name'],
            row['athlete_gender'],
            row['distance_group'],
            segment,
            this_week,
            last_week
        ),
        axis=1
    )

    top_df["Rank Movement (6M)"] = top_df.apply(
        lambda row: get_movement(
            row['athlete_name'],
            row['athlete_gender'],
            row['distance_group'],
            segment,
            this_week,
            six_months_ago
        ),
        axis=1
)


    # Rename for display
    display_df = top_df[[
        "Rank", "athlete_slug", "athlete_name", "athlete_country", segment, "Rank Movement (1W)", "Rank Movement (6M)"
    ]].rename(columns={
        "athlete_name": "Athlete",
        "athlete_country": "Country",
        segment: "PTO Score",
        "Rank Movement (1W)": "Movement (vs Last Week)",
        "Rank Movement (6M)": "Movement (vs 6 Months Ago)"
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
