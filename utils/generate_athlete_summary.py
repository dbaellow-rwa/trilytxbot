#!/usr/bin/env python3
# file: build_new_athlete_pages.py

import os
import sys
import json
import pandas as pd
from google.cloud import bigquery
from openai import OpenAI 
from datetime import datetime

from utils.bq_utils import load_credentials
from config.app_config import USE_LOCAL


# ──────────────────────────────────────────────────────────────────────────────
# 1) Credentials & BigQuery Client
# ──────────────────────────────────────────────────────────────────────────────

def get_bq_client(credentials, project_id):
    """
    Returns a bigquery.Client authenticated with trilytx_credentials.
    """
    return bigquery.Client(
        credentials=credentials,
        project=project_id
    )


# ──────────────────────────────────────────────────────────────────────────────
# 2) Data Pull & Aggregation
# ──────────────────────────────────────────────────────────────────────────────
def load_race_predict_v_results_data(bq_client):
    query = """
        SELECT * FROM trilytx.trilytx_aggregate.agg_race_predict_vs_results
    """
    return bq_client.query(query).to_dataframe()

def load_race_segment_positions_data(bq_client):
    query = """
        SELECT * FROM trilytx.trilytx_aggregate.agg_race_segment_positions
    """
    return bq_client.query(query).to_dataframe()

def load_weekly_pto_scores_data(bq_client):
    query = """
        WITH
scores as (
  SELECT * FROM `trilytx.trilytx_fct.fct_pto_scores_weekly`
),

 weeks AS (
  SELECT DISTINCT DATE(reporting_week) AS reporting_week
  FROM scores
),
reference_weeks AS (
  SELECT 
    MAX(reporting_week) AS most_recent_week
  FROM weeks
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
  SELECT 
    MAX(reporting_week) AS reporting_week,
    '6 Months Ago' as week_type
  FROM weeks, target_weeks
  WHERE reporting_week <= week_6mo_ago
  UNION ALL
  SELECT 
    MAX(reporting_week),
    '12 Months Ago' as week_type
  FROM weeks, target_weeks
  WHERE reporting_week <= week_12mo_ago
  UNION ALL
  SELECT 
    MAX(reporting_week),
    '24 Months Ago' as week_type
  FROM weeks, target_weeks
  WHERE reporting_week <= week_24mo_ago
  UNION ALL
  SELECT most_recent_week,
    'Current' as week_type
  FROM target_weeks
), 

filtered as (

SELECT t.*, f.week_type
FROM scores t
JOIN filtered_targets f
  ON DATE(t.reporting_week) = f.reporting_week

)
select * from filtered
-- where distance_group = 'Overall'

    """
    return bq_client.query(query).to_dataframe()



def generate_race_results_detail(df: pd.DataFrame, specific_athlete: str) -> str:
    athlete_df = df[df["athlete_name"].str.lower()== specific_athlete.lower()].copy()
    athlete_df = athlete_df.sort_values("race_date", ascending=False).head(10)
    if athlete_df.empty:
        return f"No data found for race: {specific_athlete}"

    selected_cols = [
        "athlete_name","overall_pto_rank", "overall_actual_rank", "overall_delta",
        "swim_delta", "swim_actual_rank", "bike_delta", "bike_actual_rank", "run_delta", "run_actual_rank", "swim_time", "bike_time", "run_time", "overall_time",
        "sof","race_distance","race_gender","race_name", "race_location", "race_date",
        "race_overall_delta_rank_desc", "race_overall_delta_rank_asc" ,
        "race_swim_delta_rank_desc", "race_swim_delta_rank_asc" ,
        "race_bike_delta_rank_desc", "race_bike_delta_rank_asc" ,
        "race_run_delta_rank_desc", "race_run_delta_rank_asc" 
    ]
    
    df["race_date"] = pd.to_datetime(df["race_date"]).dt.strftime("%b %d, %Y")
    athlete_df = athlete_df[selected_cols].sort_values("overall_actual_rank")

    return athlete_df.to_markdown(index=False)

def generate_race_position_detail(df: pd.DataFrame, specific_athlete: str) -> str:
    athlete_df = df[df["athlete_name"].str.lower()== specific_athlete.lower()].copy()
    athlete_df = athlete_df.sort_values("race_date", ascending=False).head(10)
    if athlete_df.empty:
        return f"No data found for race: {specific_athlete}"

    selected_cols = [
        "athlete_name",  "cumulative_seconds_after_swim", "cumulative_seconds_after_t1", "cumulative_seconds_after_bike",
        "cumulative_seconds_after_t2", "cumulative_seconds_after_run", "rank_after_swim", "rank_after_t1", "rank_after_bike",
        "rank_after_t2", "rank_after_run", "position_change_in_t1", "position_change_on_bike", "position_change_in_t2", "position_change_on_run",
        "race_position_change_bike_rank_desc", "race_position_change_run_rank_desc","race_position_change_bike_rank_asc", "race_position_change_run_rank_asc"
    ]
    


    athlete_df = athlete_df[selected_cols]
    return athlete_df.to_markdown(index=False)


def generate_weekly_pto_scores_detail(df: pd.DataFrame, specific_athlete: str) -> str:
    athlete_df = df[df["athlete_name"].str.lower()== specific_athlete.lower()].copy()
    athlete_df = athlete_df.sort_values("reporting_week", ascending=False).head(10)
    if athlete_df.empty:
        return f"No data found for athlete: {specific_athlete}"

    selected_cols = [
        "athlete_id",
        "athlete_name",
        "athlete_slug",
        "athlete_gender",
        "athlete_country",
        "athlete_weight",
        "athlete_height",
        "athlete_year_of_birth",
        "reporting_week",
        "distance_group",
        "swim_pto_score",
        "t1_pto_score",
        "bike_pto_score",
        "t2_pto_score",
        "run_pto_score",
        "overall_pto_score",
        "rank_swim_pto_score_by_distance_group_athlete_gender_reporting_week_desc",
        "rank_swim_pto_score_by_distance_group_athlete_gender_athlete_country_reporting_week_desc",
        "rank_bike_pto_score_by_distance_group_athlete_gender_reporting_week_desc",
        "rank_bike_pto_score_by_distance_group_athlete_gender_athlete_country_reporting_week_desc",
        "rank_run_pto_score_by_distance_group_athlete_gender_reporting_week_desc",
        "rank_run_pto_score_by_distance_group_athlete_gender_athlete_country_reporting_week_desc",
        "rank_overall_pto_score_by_distance_group_athlete_gender_reporting_week_desc",
        "rank_overall_pto_score_by_distance_group_athlete_gender_athlete_country_reporting_week_desc",
    ]


    athlete_df = athlete_df[selected_cols]

    rename_for_llm = {
        "rank_swim_pto_score_by_distance_group_athlete_gender_reporting_week_desc": 
            "swim_rank_among_same_gender_same_distance_group",
        
        "rank_swim_pto_score_by_distance_group_athlete_gender_athlete_country_reporting_week_desc": 
            "swim_rank_among_same_gender_same_country_same_distance_group",

        "rank_bike_pto_score_by_distance_group_athlete_gender_reporting_week_desc": 
            "bike_rank_among_same_gender_same_distance_group",
        
        "rank_bike_pto_score_by_distance_group_athlete_gender_athlete_country_reporting_week_desc": 
            "bike_rank_among_same_gender_same_country_same_distance_group",

        "rank_run_pto_score_by_distance_group_athlete_gender_reporting_week_desc": 
            "run_rank_among_same_gender_same_distance_group",
        
        "rank_run_pto_score_by_distance_group_athlete_gender_athlete_country_reporting_week_desc": 
            "run_rank_among_same_gender_same_country_same_distance_group",

        "rank_overall_pto_score_by_distance_group_athlete_gender_reporting_week_desc": 
            "overall_rank_among_same_gender_same_distance_group",
        
        "rank_overall_pto_score_by_distance_group_athlete_gender_athlete_country_reporting_week_desc": 
            "overall_rank_among_same_gender_same_country_same_distance_group"
    }
    athlete_df = athlete_df.rename(columns=rename_for_llm)

    return athlete_df.to_markdown(index=False)

# ──────────────────────────────────────────────────────────────────────────────
# 3) LLM Prompt Construction
# ──────────────────────────────────────────────────────────────────────────────


# ---
def construct_athlete_profile_prompt(athlete_results_table: str, athlete_segment_table: str, specific_weekly_pto_scores_text: str, specific_athlete: str, instructions: str = "") -> str:
    return f"""
You are a professional triathlon analyst. Below are two tables showing recent race performances for an athlete named **{specific_athlete.title()}**.

Your task is to write a clear, flowing **athlete profile summary**, focusing on their **recent trends**, **segment strengths**, and **overall performance patterns**.

---

### 🧠 Instructions:

- Write a **single narrative paragraph** that summarizes how this athlete has performed lately.
- Highlight:
  - Their most recent podiums or standout races
  - Notable trends (e.g., consistently strong on the bike, improving run times, struggling in transitions)
  - Key performance metrics from recent races (e.g., finish time, rank, delta, segment gains/losses)
  - Any improvement or decline across recent races
- If available, mention past race names and dates to add context.
- Use a natural, analytical tone — imagine you’re writing a 1-paragraph blurb for a race broadcast or triathlon magazine.
- Refer to the athlete as **{specific_athlete.title()}** in the third person, and always use Proper Case names for other competitors or races.
- You may include light commentary like “What stands out…” or “Interestingly…”

### 📝 Example structure (not literal template):

“{specific_athlete} has been building momentum over the past few races. After a strong showing at Ironman Oceanside in April, where they gained five places on the run, they continued their upward trajectory with a podium at Challenge Roth. Their bike splits have consistently ranked among the top five, though transitions remain an area of opportunity. Overall, {specific_athlete.title()} is trending upward and may be poised for a breakthrough performance in upcoming events.”

---

### Additional Instructions from the User:
{instructions if instructions else "None"}

---

### 📋 Race Results Table

{athlete_results_table}

---

### 📋 Segment Details & Position Changes

{athlete_segment_table}

---

### 📋 Selected Athlete Scores and Rankings

{specific_weekly_pto_scores_text}
"""




def call_openai(prompt: str, openai_key: str) -> str:
    api_client = OpenAI(api_key=openai_key)
    try:
        response = api_client.chat.completions.create(
            model="gpt-4o",  # Replace with your appropriate model name if needed
            # model="gpt-4-turbo",

            messages=[{"role": "user", "content": prompt}],
            temperature=0.85,
            max_completion_tokens=5000,
            top_p=1,
            frequency_penalty=0.2,
            presence_penalty=0.4
        )
        intro_text = response.choices[0].message.content.strip()
        return intro_text
    except Exception as e:
        print(f"Error generating intro email: {e}")
        return "Error generating AI content - please see the data below for detailed information."
    

def generate_athlete_summary_for_athlete(specific_athlete: str, instructions: str = ""):
    credentials, project_id, openai_key = load_credentials(USE_LOCAL)
    bq_client = get_bq_client(credentials, project_id)

    race_predict_v_results_df = load_race_predict_v_results_data(bq_client)
    race_segment_position_df = load_race_segment_positions_data(bq_client)
    weekly_pto_scores_df = load_weekly_pto_scores_data(bq_client)

    specific_race_results_text = generate_race_results_detail(race_predict_v_results_df, specific_athlete)
    specific_race_positions_text = generate_race_position_detail(race_segment_position_df, specific_athlete)
    specific_weekly_pto_scores_text = generate_weekly_pto_scores_detail(weekly_pto_scores_df, specific_athlete)

    athlete_profile_prompt = construct_athlete_profile_prompt(
        specific_race_results_text, 
        specific_race_positions_text,
        specific_weekly_pto_scores_text,
        specific_athlete,
        instructions)

    recap_response = call_openai(athlete_profile_prompt, openai_key)
    return recap_response
            


# ──────────────────────────────────────────────────────────────────────────────
# Run the script
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    arg_athlete_name = sys.argv[1] if len(sys.argv) > 1 else None
    arg_instructions = sys.argv[2] if len(sys.argv) > 2 else ""

    generate_athlete_summary_for_athlete(specific_athlete=arg_athlete_name, instructions=arg_instructions)

