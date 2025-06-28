#!/usr/bin/env python3
# file: build_new_athlete_pages.py

import os
import sys
import json
import pandas as pd
from google.cloud import bigquery, secretmanager, storage
from google.oauth2 import service_account
from openai import OpenAI 
from datetime import datetime
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.mime.base import MIMEBase
from email import encoders
import smtplib

# ──────────────────────────────────────────────────────────────────────────────
# Set up sys.path for local imports
# ──────────────────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from sources_of_truth.secret_manager_utils import get_secret


# ──────────────────────────────────────────────────────────────────────────────
# 1) Credentials & BigQuery Client
# ──────────────────────────────────────────────────────────────────────────────
def load_credentials():
    if "GOOGLE_APPLICATION_CREDENTIALS_TRILYTX" not in os.environ:
        print("INFO: No GOOGLE_APPLICATION_CREDENTIALS_TRILYTX found, using ADC locally.")
    json_key_str = get_secret(secret_id="service-account-trilytx-key", project_id="trilytx")
    json_key = json.loads(json_key_str)
    return json_key, service_account.Credentials.from_service_account_info(json_key)

def get_bq_client(credentials, project_id):
    """
    Returns a bigquery.Client authenticated with trilytx_credentials.
    """
    return bigquery.Client(
        credentials=credentials,
        project=project_id
    )

def get_recent_races(bq_client) :
    """

    """

    query = f"""

    WITH
    recent_races AS (
    SELECT
        DISTINCT unique_race_id
    FROM
        `trilytx_core.core_race_info`
    WHERE
        race_date BETWEEN CURRENT_DATE() - 1
        AND CURRENT_DATE()
        AND organizer IS NOT NULL ),
    race_reports_generated AS (
    SELECT
        DISTINCT unique_race_id
    FROM
        `trilytx.race_reports_generated` )
    SELECT
    r.unique_race_id
    FROM
    recent_races r
    LEFT JOIN
    race_reports_generated g
    ON
    r.unique_race_id = g.unique_race_id
    WHERE
    1=1
    and g.unique_race_id IS NULL
    -- AND r.unique_race_id in (
    -- 'san-francisco-t100-2025-women'
    -- 'san-francisco-t100-2025-women'
    -- 'im-703-eagleman-2025-men', 'im-703-eagleman-2025-women'
    -- 'san-francisco-t100-2025-men', 'san-francisco-t100-2025-women'
    --)
    """
    df = bq_client.query(query).to_dataframe()
    return set(df["unique_race_id"].astype(str).tolist())

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



def generate_race_results_detail(df: pd.DataFrame, race_id: str) -> str:
    race_df = df[df["unique_race_id"] == race_id].copy()
    if race_df.empty:
        return f"No data found for race: {race_id}"

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
    race_df = race_df[selected_cols].sort_values("overall_actual_rank")

    return race_df.to_markdown(index=False)

def generate_race_position_detail(df: pd.DataFrame, race_id: str) -> str:
    race_df = df[df["unique_race_id"] == race_id].copy()
    if race_df.empty:
        return f"No data found for race: {race_id}"

    selected_cols = [
        "athlete_name",  "cumulative_seconds_after_swim", "t1_cumulative_seconds_after_t1", "bike_cumulative_seconds_after_bike",
        "t2_cumulative_seconds_after_t2", "run_cumulative_seconds_after_run", "rank_after_swim", "rank_after_t1", "rank_after_bike",
        "rank_after_t2", "rank_after_run", "position_change_in_t1", "position_change_on_bike", "position_change_in_t2", "position_change_on_run",
        "race_position_change_bike_rank_desc", "race_position_change_run_rank_desc","race_position_change_bike_rank_asc", "race_position_change_run_rank_asc"
    ]
    


    race_df = race_df[selected_cols]
    return race_df.to_markdown(index=False)



def format_historical_race_rows(df: pd.DataFrame) -> str:
    if df.empty:
        return "No historical races found."

    # Only keep fields relevant for storytelling
    selected_cols = [
               "athlete_name", "athlete_gender", "overall_pto_rank", "overall_actual_rank", "overall_delta",
        "swim_delta", "swim_actual_rank", "bike_delta", "bike_actual_rank", "run_delta", "run_actual_rank", "swim_time", "bike_time", "run_time", "overall_time",
        "sof","race_distance","race_gender","race_name", "race_location", "race_date"
    ]
    df = df[selected_cols].copy()
    df["race_date"] = pd.to_datetime(df["race_date"]).dt.strftime("%b %d, %Y")

    # Sort by athlete and recency
    df.sort_values(by=["athlete_name", "race_date"], ascending=[True, False], inplace=True)

    return df.to_markdown(index=False)
# ──────────────────────────────────────────────────────────────────────────────
# 3) LLM Prompt Construction
# ──────────────────────────────────────────────────────────────────────────────


# ---
def construct_race_report_prompt(specific_race_text, specific_race_positions_text):
    return f"""
You are a professional sports performance analyst. Below are two tables from a triathlon that took place this weekend.

Using the athlete data and historical performance trends, generate a clear, structured race recap that includes the following sections:

---

### 🔹 Race Introduction
- Include the **race name**, **date**, **location**, **distance**, and **Strength of Field (SOF)**.
note: a higher strength of field is better - ~100 is about the max it can be
---

### 🏅 Podium Summary
For the top 3 finishers:
- Write a short (2-3 sentance) summary of each athlete’s performance.
- Include:
    - **Finish time** (overall_time)
    - **Overall rank** (overall_actual_rank)
    - **Overall predicted performance delta** (overall_delta)
- Highlight key segments (swim, bike, run) with:
  - **segment time(s)**(swim_time and/or bike_time and/or run_time)
  - **segment actual rank** how they performed in the segment (swim_actual_rank and/or bike_actual_rank and/or run_actual_rank)
  - **segment predicted performance delta** positive number means they overperformed their predicted performance (swim_delta and/or bike_delta and/or run_delta)
  - **segment positions gained** positive number means they made up ground in the race during the segment (position_change_on_bike and/or position_change_on_run)

---

### 📈 Overperformers
- Identify athletes with a **positive overall predicted performance delta**.
- For each:
  - Write a 2-3 sentance summary of their race, focusing on where they gained positions.
  - Include:
    - **Finish time** (overall_time)
    - **Overall rank** (overall_actual_rank)
    - **Overall predicted performance delta** (overall_delta)
    - **Top segment with the most position change** athlete's highest value in the position_change_on_bike or position_change_on_run columns (must be positive to include)
    - Notable segments with `time`, `actual rank`, `predicted performance delta`, 
    - typically one of the athletes with the lowest values in race_overall_delta_rank_desc should be included

---

### 📉 Underperformers
- Identify athletes with a **negative overall predicted performance delta**.
- For each:
  - Write a 2-3 sentance summary describing where they lost ground.
  - Include:
    - **Finish time** (overall_time)
    - **Overall rank** (overall_actual_rank)
    - **Overall predicted performance delta** (overall_delta)
    - **Worst segment with the most position change** athlete's lowest value in the position_change_on_bike or position_change_on_run columns (must be negative to include)
    - Struggling segments with `time`, `actual rank`, and `predicted performance delta`
    - typically one of the athletes with the lowest values in race_overall_delta_rank_asc should be included

---

### 📊 Segment Trends
- Describe any patterns across **swim**, **bike**, and **run** segments.
- Highlight top and bottom performers based on their `position_change_on_bike` and `position_change_on_run`.

---

### 🏁 Conclusion:
- Wrap up the recap with 2 sentences that reflect on the overall competitiveness of the race.
- You may highlight key takeaways, surprising outcomes, or implications for future races.
- Mention any standout storylines (e.g., unexpected podium, breakthrough performance, rough day for a favorite).
- Use a professional yet conversational tone to leave the reader with a sense of closure.


---

### ❗Instructions:
- Use a **natural, conversational tone** — your writing should feel like a race analyst talking to an engaged triathlon audience.
- Start each section or athlete summary with a **short narrative paragraph** that gives context before listing the numbers.
- Use **more full sentences and flowing paragraphs** instead of relying only on bullet points.
- Use **phrases like “What stood out…”**, “Interestingly…”, or “Despite expectations…” to add analytical voice and personality.
- Still include the key metrics (`time`, `actual rank`, `delta`, and `position change`) for each athlete and segment.
- Always refer to each athlete by their real name, in Proper Case.
- Avoid placeholders like ATHLETE A or [Athlete Name].
- You may still use bullet points, but aim for a balance between narrative and structure.
- Always consider the historical context when summarizing athlete performances.
  - If an athlete recently won a major race, mention it.
  - If they have multiple podiums or a big improvement over past results, point it out.
  - Use specific past race names and dates to make the analysis feel grounded.

### Points you have halucinated in the past:
- overall_pto_rank refers to the athlete's incoming overall rank **relative to the other participants in the field**
---

### 📋 Race Table: Predicted vs Actual Rankings

{specific_race_text}

---

### 📋 Race Table: Segment Times & Position Changes

{specific_race_positions_text}

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
    

def generate_race_recap_for_id(specific_race_id=None):
    current_date_est = datetime.now()
    print("🔁 Loading credentials and clients...")
    json_key, credentials = load_credentials()
    bq_client = get_bq_client(credentials, json_key["project_id"])
    openai_key = get_secret(secret_id="openai_rwa_1", project_id="trilytx")

    print("📥 Pulling and summarizing race data...")
    race_predict_v_results_df = load_race_predict_v_results_data(bq_client)
    race_segment_position_df = load_race_segment_positions_data(bq_client)
    specific_race_results_text = generate_race_results_detail(race_predict_v_results_df, specific_race_id)
    specific_race_positions_text = generate_race_position_detail(race_segment_position_df, specific_race_id)


    race_report_prompt = construct_race_report_prompt(
        specific_race_results_text, 
        specific_race_positions_text)

    recap_response = call_openai(race_report_prompt, openai_key)
    return recap_response
            


# ──────────────────────────────────────────────────────────────────────────────
# Run the script
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    arg_race_id = sys.argv[1] if len(sys.argv) > 1 else None
    generate_race_recap_for_id(specific_race_id=arg_race_id)

