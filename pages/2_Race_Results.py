import streamlit as st
import pandas as pd
from google.cloud import bigquery
from utils.bq_utils import load_credentials
from config.app_config import USE_LOCAL, BQ_RACE_SEARCH_LOG, BQ_RACE_RECAP_LOG
from utils.generate_race_recaps import generate_race_recap_for_id
from utils.streamlit_utils import log_race_search, log_race_recap_generate, make_athlete_link, render_login_block,get_oauth, get_flag, cookies
import json
oauth2, redirect_uri = get_oauth()

# st.set_page_config(page_title="🏁 Race Results Viewer", layout="wide")
st.title("🏁 Race Results Viewer")

# Load credentials and BigQuery client
credentials, project_id, _ = load_credentials(USE_LOCAL)
bq_client = bigquery.Client(credentials=credentials, project=project_id)
# Handle incoming ?unique_race_id=... query param
query_params = st.query_params
if "unique_race_id" in query_params:
    st.session_state.selected_race_id = query_params["unique_race_id"]

    # Optional: lookup label for display
    @st.cache_data(ttl=3600)
    def get_race_label_map():
        query = """
        SELECT DISTINCT unique_race_id,
            CONCAT(initcap(organizer), ' ', cleaned_race_name, ' ', initcap(race_gender), ' (', CAST(race_date AS STRING), ')') AS label
        FROM `trilytx.trilytx_fct.fct_race_results`
        """
        df = bq_client.query(query).to_dataframe()
        return {row["unique_race_id"]: row["label"] for _, row in df.iterrows()}

    race_label_map = get_race_label_map()
    st.session_state.selected_race_label = race_label_map.get(st.session_state.selected_race_id, "Selected Race")
    st.session_state.load_results_clicked = True




if "user" not in st.session_state and "user" in cookies:
    try:
        st.session_state["user"] = json.loads(cookies["user"])
    except Exception:
        st.warning("❌ Failed to decode user info.")

# Initialize session state
for key in ["selected_race_id", "filters_applied", "races_df"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ────────────────
# Sidebar Filters
# ────────────────
with st.sidebar:
    st.markdown("### Filter Races")

    organizer_filter = st.selectbox("Organizer", ["All", "challenge", "t100", "ironman", "itu", "pto", "wtcs"])
    gender_filter = st.selectbox("Gender", ["All", "men", "women"])
    distance_filter = st.selectbox("Distance", ["All", "Half-Iron (70.3 miles)", "Iron (140.6 miles)", "100 km", "Other middle distances", "Other long distances"])
    race_year_filter = st.selectbox("Year", ["All"] + [str(y) for y in range(2025, 2015, -1)])


    if st.button("🧹 Reset Filters"):
        st.session_state.load_results_clicked = False
        st.session_state.selected_race_id = None
        st.session_state.selected_race_label = None
        st.rerun()

    if st.button("❌ Clear Results"):
        st.session_state.load_results_clicked = False
        st.session_state.selected_race_id = None
        st.session_state.selected_race_label = None
        st.rerun()
        
    if st.button("🔍 Search Races"):
        st.session_state.selected_race_id = None  # reset race when filters change
        st.session_state.selected_race_label = None
        st.session_state.load_results_clicked = False  # ✅ Reset this to False


        st.session_state.filters_applied = {
            "organizer": None if organizer_filter == "All" else organizer_filter,
            "gender": None if gender_filter == "All" else gender_filter,
            "distance": None if distance_filter == "All" else distance_filter,
            "year": None if race_year_filter == "All" else race_year_filter
        }

        # Fetch races only when Search is clicked
        query = """
        SELECT DISTINCT
            unique_race_id,
            initcap(organizer) as organizer,
            cleaned_race_name,
            race_date,
            DATE_TRUNC(race_date, YEAR) AS race_year,
            initcap(race_gender) as race_gender,
            race_distance
        FROM `trilytx.trilytx_fct.fct_race_results`
        WHERE unique_race_id IS NOT NULL
        """
        filters = []
        params = []

        if st.session_state.filters_applied["organizer"]:
            filters.append("organizer = @organizer")
            params.append(bigquery.ScalarQueryParameter("organizer", "STRING", st.session_state.filters_applied["organizer"]))
        if st.session_state.filters_applied["gender"]:
            filters.append("race_gender = @gender")
            params.append(bigquery.ScalarQueryParameter("gender", "STRING", st.session_state.filters_applied["gender"]))
        if st.session_state.filters_applied["distance"]:
            filters.append("race_distance = @distance")
            params.append(bigquery.ScalarQueryParameter("distance", "STRING", st.session_state.filters_applied["distance"]))
        if st.session_state.filters_applied["year"]:
            filters.append("EXTRACT(YEAR FROM race_date) = @year")
            params.append(bigquery.ScalarQueryParameter("year", "INT64", int(st.session_state.filters_applied["year"])))

        if filters:
            query += " AND " + " AND ".join(filters)

        query += " ORDER BY race_date DESC"

        job_config = bigquery.QueryJobConfig(query_parameters=params)
        df = bq_client.query(query, job_config=job_config).to_dataframe()
        df["label"] = df["organizer"] + " " + df["cleaned_race_name"] + " " + df["race_gender"] + " (" + df["race_date"].astype(str) + ")"
        st.session_state.races_df = df
    render_login_block(oauth2, redirect_uri)

# ────────────────
# Race Selector
# ────────────────

if st.session_state.races_df is not None and not st.session_state.races_df.empty:
    race_label_to_id = dict(zip(st.session_state.races_df["label"], st.session_state.races_df["unique_race_id"]))
    
    selected_label = st.selectbox("Select a Race", list(race_label_to_id.keys()), key="race_selectbox")

    if st.button("🔍 Load Results"):
        st.session_state.selected_race_id = race_label_to_id.get(selected_label)
        st.session_state.selected_race_label = selected_label
        st.session_state.load_results_clicked = True
else:
    st.info("💡 Use the filters on the side to see a selection of races.")


# ────────────────
# Show Results
# ────────────────
@st.cache_data(ttl=600)
def get_race_results(race_id):
    query = """
    SELECT
        race_category, race_distance, organizer, cleaned_race_name, race_date, race_tier, sof, race_location, athlete_slug, athlete_finishing_place, athlete_name, athlete_country,
        swim_time, t1_time, bike_time, t2_time, run_time, overall_time, overall_seconds
    FROM `trilytx.trilytx_fct.fct_race_results`
    WHERE unique_race_id = @race_id
    ORDER BY COALESCE(athlete_finishing_place, 999)
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("race_id", "STRING", race_id)]
    )
    return bq_client.query(query, job_config=job_config).to_dataframe()

@st.cache_data(ttl=600)
def get_race_segment_positions(race_id):
    query = """
    SELECT
        athlete_slug,
        athlete_name,
        athlete_country,
        rank_after_swim,
        rank_after_bike,
        rank_after_run
    FROM `trilytx.trilytx_fct.fct_race_segment_positions`
    WHERE unique_race_id = @race_id
    ORDER BY COALESCE(rank_after_run, 999)
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("race_id", "STRING", race_id)]
    )
    return bq_client.query(query, job_config=job_config).to_dataframe()

if st.session_state.get("load_results_clicked", False):
    log_race_search(bq_client, st.session_state.selected_race_id, BQ_RACE_SEARCH_LOG)
    st.subheader(f"Results for {st.session_state.get('selected_race_label', 'Selected Race')}")
    results_df = get_race_results(st.session_state.selected_race_id)

    if results_df.empty:
        st.warning("No results found for this race.")
    else:

        race_category = results_df["race_category"].iloc[0]
        organizer = results_df["organizer"].iloc[0]
        race_distance = results_df["race_distance"].iloc[0]
        race_date = results_df["race_date"].iloc[0]
        race_tier = results_df["race_tier"].iloc[0]
        sof = results_df["sof"].iloc[0]
        race_location = results_df["race_location"].iloc[0]




        st.markdown(f"**Distance:** {race_distance}  |  **Location:** {race_location}")
        st.markdown(f"**Tier:** {race_tier}  |  **SOF:** {sof}")
        
        # st.markdown(f"**{len(results_df)} athletes** found.")
        # Define renamed display columns
        # Define the raw columns and matching display column names
        columns_to_check = ["swim_time", "bike_time", "run_time", "overall_time"]
        column_renames = {
            "athlete_finishing_place": "Place",
            "athlete_name": "Athlete",
            "athlete_country": "Country",
            "swim_time": "Swim",
            "t1_time": "T1",
            "bike_time": "Bike",
            "t2_time": "T2",
            "run_time": "Run",
            "overall_time": "Finish Time"
        }

        # Copy for time-safe parsing
        highlight_df = results_df.copy()

        # Convert time columns to timedelta if needed
        for col in columns_to_check:
            if col in highlight_df.columns:
                highlight_df[col] = pd.to_timedelta(highlight_df[col], errors="coerce")

        # Add medal emojis to top 3 before converting anything to string
        for raw_col, medal_col in zip(columns_to_check, ["Swim", "Bike", "Run", "Finish Time"]):
            if raw_col in highlight_df.columns:
                top3_indices = highlight_df[raw_col].nsmallest(3).index
                for i, medal in zip(top3_indices, ["🥇", "🥈", "🥉"]):
                    results_df.at[i, raw_col] = f"{medal} {results_df.at[i, raw_col]}"


        # Drop only 'overall_seconds', keep athlete_slug
        display_df = results_df.drop(columns=["overall_seconds"])

        # Rename display columns
        display_df = display_df.rename(columns=column_renames)

        # Format Place as clean integers
        if "Place" in display_df.columns:
            display_df["Place"] = display_df["Place"].apply(lambda x: str(int(x)) if pd.notna(x) else "")

        # Convert all other columns to safe strings
        for col in display_df.columns:
            if col != "Place":
                display_df[col] = display_df[col].apply(lambda x: "" if pd.isna(x) else str(x))

        # Add hyperlinks (make sure 'athlete_slug' is still present)
        if "athlete_slug" in results_df.columns:
            display_df["athlete_slug"] = results_df["athlete_slug"]
            display_df["Athlete"] = display_df.apply(
                lambda row: make_athlete_link(row["Athlete"], row["athlete_slug"]),
                axis=1
            )
            display_df.drop(columns=["athlete_slug",
                                     "race_category",
                                     "organizer",
                                     "cleaned_race_name",
                                     "race_date",
                                     "race_tier",
                                     "sof",
                                     "race_location",
                                     "race_distance"]
                                     , inplace=True)

        # Add country flags safely
        if "Country" in display_df.columns:
            display_df["Country"] = display_df["Country"].apply(get_flag)

        # Render markdown
        st.markdown(display_df.to_markdown(index=False), unsafe_allow_html=True)



            # Optional segment rank table
    segment_df = get_race_segment_positions(st.session_state.selected_race_id)
    if not segment_df.empty:
        st.markdown("### 🏊🚴🏃 Segment Rankings")
        display_df = segment_df.rename(columns={
            "athlete_name": "Athlete",
            "athlete_country": "Country",
            "rank_after_swim": "Rank After Swim",
            "rank_after_bike": "Rank After Bike",
            "rank_after_run": "Rank After Run"
        })
        # Format Place as clean integers
        numeric_columns = ["Rank After Swim", "Rank After Bike", "Rank After Run"]

        for col in display_df.columns:
            if col in numeric_columns:
                display_df[col] = display_df[col].apply(lambda x: str(int(x)) if pd.notna(x) else "")

        # Convert all other columns to safe strings
        for col in display_df.columns:
            if col not in numeric_columns:
                display_df[col] = display_df[col].apply(lambda x: "" if pd.isna(x) else str(x))

        display_df["Athlete"] = display_df.apply(
            lambda row: make_athlete_link(row["Athlete"], row["athlete_slug"]),
            axis=1
        )
        display_df = display_df.drop(columns=["athlete_slug"])
        display_df["Country"] = display_df["Country"].apply(get_flag)
        st.markdown(display_df.to_markdown(index=False), unsafe_allow_html=True)
    else:
        st.info("No segment ranking data available for this race.")
    st.markdown("### 📋 LLM Generated Race Recap")

    if "user" in st.session_state:
        # Initialize session state for instructions if not present
        if "recap_instructions" not in st.session_state:
            st.session_state["recap_instructions"] = ""

        st.markdown("#### ✍️ Optional Instructions for the Recap")
        st.session_state["recap_instructions"] = st.text_area(
            "Customize how the recap is written (e.g., focus on the bike segment, write it like a pirate):",
            placeholder="Write it in the style of a sports announcer... 🏁",
            key="recap_instructions_input"
        )

        if st.button("🧠 Generate Race Recap"):
            log_race_recap_generate(
                bq_client, 
                st.session_state.selected_race_id, 
                BQ_RACE_RECAP_LOG
            )
            with st.spinner("Generating recap - This might take 10-15 seconds..."):
                instructions = st.session_state["recap_instructions"]
                recap_text = generate_race_recap_for_id(
                    st.session_state.selected_race_id, 
                    instructions
                )
                st.session_state["race_recap_text"] = recap_text

        if st.session_state.get("race_recap_text"):
            st.markdown("#### 📄 Recap Output")
            st.markdown(st.session_state["race_recap_text"])

    else:
        st.warning("🔒 Please log in on the home page to generate the race recaps.")

    st.stop()


