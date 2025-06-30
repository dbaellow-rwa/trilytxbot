from typing import Dict

# ──────────────────────────────────────────────────────────────────────────────
# BigQuery Table Summaries (for initial table selection by LLM)
# ──────────────────────────────────────────────────────────────────────────────
TABLE_SUMMARIES = {
    "fct_race_results": "Race-day performance results for athletes (one row per race entry). Use for finishing times, athlete info, podiums.",
    "fct_race_results_vs_predict": "Comparison between predicted and actual results. Use for performance deltas and prediction accuracy.",
    "fct_pto_scores_weekly": "Weekly PTO scores by athlete. Use for tracking rank changes or discipline scores over time. Use this table to compare athletes to each other today, over time, or to compare athletes to themselves over time.",
    "fct_race_segment_positions": "Rank and time progression through swim, bike, run segments. Use for mid-race dynamics and position shifts (such as who moved up or down in rankings during specific legs or transitions.)"
}

# ──────────────────────────────────────────────────────────────────────────────
# Prompt Functions for Specific Tables (detailed schema and examples)
# ──────────────────────────────────────────────────────────────────────────────
def FCT_RACE_RESULTS_PROMPT() -> str:
    return """Prompt for fct_race_results:
`trilytx_fct.fct_race_results`
Contains race-day performance results for individual athletes. One row per athlete per race.

Important columns:
- athlete_id: Unique identifier for the athlete
- athlete_name: Athlete’s full name (e.g., “LIONEL SANDERS”)
- athlete_slug: Lowercase, hyphenated version of the athlete's name (e.g., “lionel-sanders”)
- athlete_gender:  Gender of the athlete (e.g., "men", "women")
- athlete_country: Country the athlete represents (e.g., "Canada")
- athlete_weight: Weight as string (e.g., "73kg")
- athlete_height: Height in meters (e.g., 1.77)
- athlete_age: Age at time of race
- athlete_year_of_birth: Athlete’s birth year (e.g., 1990)
- reporting_week: The reporting week this data corresponds to (e.g., 2024-04-14)
- distance_group: Race type (e.g., "Half-Iron (70.3 miles)", "Iron (140.6 miles)", "100 km", etc.)
- swim_pto_score, bike_pto_score, run_pto_score, t1_pto_score, t2_pto_score, overall_pto_score: PTO segment scores calculated based on strength of field and reslts. Higher is better.
  Result columns:
  - athlete_finishing_place: The actual finishing position
  - swim_time/t1_time/bike_time/t2_time/run_time/overall_time: The athlete's actual finish time in HH:MM:SS format
  - swim_seconds/bike_seconds/run_seconds/t1_seconds/t2_seconds/overall_seconds: The actual finish time in seconds

- race_distance: Full race distance label (e.g., "Half-Iron (70.3 miles)", "Iron (140.6 miles)", "Short course", "Other middle distances", "Other long distances", "100 km")
- race_category: race category
- race_country: Country the race was held in (e.g., "Canada")
- race_year: Year of the race
- race_name: Lowercase-hyphenated race name (e.g., "san-francisco-t100-2025-women")
- cleaned_race_name: Cleaned version of the race name (e.g., "San Francisco T100 2025 Women").
- race_date: Race date
- tier: Tier classification (e.g., “Gold Tier”)
- sof: Strength of Field (numeric)
- organizer: Race organizer
- race_location: city/country (e.g. Miami, FL, United States, Buenos Aires, Argentina )

general guidelines:
- When the user is asking for specific times in a segment or segments, use the _segment columns
Head-to-Head Race Comparisons
- Use the following as the starting point for head-to-head comparisons. Replace `athlete_a_slug` and `athlete_b_slug` with actual athlete slugs.
```sql
WITH athlete_meetings AS (
  SELECT
    a.unique_race_id,
    a.race_date,
    a.cleaned_race_name,
    a.race_location,
    a.athlete_name AS athlete_a,
    a.athlete_finishing_place AS athlete_a_place,
    b.athlete_name AS athlete_b,
    b.athlete_finishing_place AS athlete_b_place,
    CASE
      WHEN a.athlete_finishing_place < b.athlete_finishing_place THEN a.athlete_name
      ELSE b.athlete_name
    END AS better_athlete
  FROM
    trilytx_fct.fct_race_results a
  JOIN
    trilytx_fct.fct_race_results b
  ON
    a.unique_race_id = b.unique_race_id
    AND a.athlete_slug = 'athlete-a-slug-here' -- REPLACE THIS
    AND b.athlete_slug = 'athlete-b-slug-here' -- REPLACE THIS
  WHERE
    a.overall_seconds IS NOT NULL
    AND b.overall_seconds IS NOT NULL
)
SELECT * FROM athlete_meetings
```
-- recent race podiums ("show me the most recent mens and womens podium for the t100 event")

Use the following as the starting point:
```sql
WITH recent_t100_races AS (
  SELECT
    unique_race_id,
    race_date,
    race_name,
    race_location,
    athlete_gender,
    ROW_NUMBER() OVER (PARTITION BY athlete_gender ORDER BY race_date DESC) AS rn
  FROM
    trilytx_fct.fct_race_results
  WHERE
    overall_seconds IS NOT NULL
),
podium_athletes AS (
  SELECT
    r.unique_race_id,
    r.race_date,
    r.race_name,
    r.race_location,
    r.athlete_gender,
    f.athlete_name,
    f.athlete_finishing_place,
    f.overall_time
  FROM
    recent_t100_races r
  JOIN
    trilytx_fct.fct_race_results f
  ON
    r.unique_race_id = f.unique_race_id
  WHERE
    r.rn = 1
    AND f.athlete_finishing_place <= 3
)
SELECT
  race_name,
  race_date,
  race_location,
  athlete_gender,
  STRING_AGG(CONCAT(athlete_name, ': ', CAST(athlete_finishing_place AS STRING), ' (', overall_time, ')'), ', ') AS podium
FROM
  podium_athletes
GROUP BY
  race_name, race_date, race_location, athlete_gender
ORDER BY
  race_date DESC, athlete_gender
 ``` 
"""

def FCT_RACE_RESULTS_VS_PREDICT_PROMPT() -> str:
    return """Prompt for fct_race_results_vs_predict:
    `trilytx_fct.fct_race_results_vs_predict`
Contains model-predicted triathlon race outcomes compared to actual race-day results, one row per athlete per race.

Important columns:
- unique_race_id: Unique identifier for the race
- race_name: Lowercase-hyphenated race name (e.g., "san-francisco-t100-2025-women")
- cleaned_race_name: Cleaned version of the race name (e.g., "San Francisco T100 2025 Women").
- athlete_name: Athlete’s full name, uppercased (e.g., "ASHLEIGH GENTLE")
- athlete_slug: Lowercase, hyphenated version of the athlete's name (e.g., "ashleigh-gentle")
- athlete_gender: Athlete gender (e.g., "women", "men')
- organizer: Race organizer (e.g., "t100", "ironman")
- race_distance: Race distance (e.g., "100 km", "Half-Iron (70.3 miles)", "Iron (140.6 miles)")
- race_location: City and country (e.g., "San Francisco, CA, United States")
- race_date: Race date

Prediction columns:
- swim_pto_rank/bike_pto_rank/run_pto_rank/overall_pto_rank: The athlete's predicted finishing position in the disciplines relative to the rest of the field
- swim_actual_rank/bike_actual_rank/run_actual_rank/overall_actual_rank: The athlete's actual finishing position in the disciplines relative to the rest of the field
- swim_delta/bike_delta/run_delta/overall_delta: Difference between predicted and actual rank (positive means better than predicted i.e. they overperformed, negative means worse than predicted i.e. they underperformed)

Result columns:
- athlete_finishing_place: The actual finishing position
- swim_time/bike_time/run_time/overall_time: The athlete's actual time in HH:MM:SS format
- swim_seconds/bike_seconds/run_seconds/overall_seconds: The actual time in seconds

This table is used to compare how closely the athletes's race predictions matched the actual outcomes. You can calculate accuracy, identify over- or under-performing athletes, or summarize over/under performance by race, gender, or athlete.
"""

def FCT_PTO_SCORES_WEEKLY_PROMPT() -> str:
    return """Prompt for fct_pto_scores_weekly:

    `trilytx_fct.fct_pto_scores_weekly`
Contains weekly PTO segment scores for each athlete by distance group and overall. The higher the score, the better the athlete.
    Important columns:
- athlete_id: Unique identifier for the athlete
- athlete_name: Athlete’s full name (e.g., “LIONEL SANDERS”)
- athlete_slug: Lowercase, hyphenated version of the athlete's name (e.g., "lionel-sanders")
- athlete_gender: Athlete gender (e.g., "men" and "women")
- athlete_country: Country the athlete represents (e.g., "Canada")
- athlete_weight: Athlete weight (e.g., "73kg")
- athlete_height: Athlete height in meters (e.g., "1.77")
- athlete_year_of_birth: Athlete birth year
- reporting_week: Date of the week this score is reporting on (e.g., "2023-09-10") - Assume the user is asking for an up-to-date week if they do not specify. up-to-date means reporting_week = DATE_TRUNC(CURRENT_DATE(), WEEK). If the user asks for a specific date, use DATE_TRUNC(specific_date, WEEK) to find the reporting week.
- distance_group: Race category (e.g., "Iron (140.6 miles)", "Half-Iron (70.3 miles)", "100 km", "Overall"). If the user does not define a distance, default to distance_group = 'Overall'
- swim_pto_score, bike_pto_score, run_pto_score, overall_pto_score: PTO segment scores. Higher is better.
- t1_pto_score, t2_pto_score: Transition segment scores
- rank_*: Ranking columns that compare this athlete’s score across different groupings (e.g., by distance, gender, country, birth year). These are useful for relative performance analysis.


- When comparing athlete rankings over time:
    • start with these CTEs (replace `requested_discipline_score` with actual column, `timeframe_where_clause` with date filter, and `'athlete_1', 'athlete_2'` with actual names):
```sql
    WITH ranked_discipline_scores AS (
    SELECT
        athlete_name,
        athlete_gender,
        distance_group,
        reporting_week,
        overall_pto_score AS requested_discipline_score, -- Example: using overall_pto_score
        RANK() OVER (PARTITION BY athlete_gender, distance_group, reporting_week ORDER BY overall_pto_score DESC) AS requested_discipline_rank
    FROM
        trilytx_fct.fct_pto_scores_weekly
    WHERE
        reporting_week >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 WEEK) -- Example: last 12 weeks
        AND distance_group = 'Overall'
        -- do not filter athletes HERE!!
    ),

    selected_athletes as (
    select * from ranked_discipline_scores
    where athlete_name in ('LIONEL SANDERS', 'SAM LAIDLOW' -- Example athletes
    )

    SELECT
        reporting_week,
        STRING_AGG(CONCAT(athlete_name, ': ', CAST(requested_discipline_rank AS STRING)), ', ') AS athlete_discipline_ranks
    FROM
        selected_athletes
    GROUP BY
        reporting_week
    ORDER BY
        reporting_week DESC
```        
timeframe_where_clause: Use this to filter the reporting_week to a specific range. For example, to get the last 12 weeks, use reporting_week >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 WEEK). If the user does not specify a timeframe, default to the last 12 weeks.
"""        
def FCT_RACE_SEGMENT_POSITIONS_PROMPT() -> str:
    return """Prompt for fct_race_segment_positions:
  `trilytx_fct.fct_race_segment_positions`
  Contains athlete-level rank and cumulative time tracking throughout each segment of a race. Use this table to analyze mid-race dynamics, such as who moved up or down in rankings during specific legs or transitions.

  Important columns:
  - race_results_id: Unique identifier for each athlete's race result record.
  - unique_race_id: Unique identifier for the race event.
  - athlete_name: Athlete’s full name UPPERCASE (e.g., “LIONEL SANDERS”).
  - athlete_slug: Lowercase, hyphenated version of the athlete's name (e.g., “lionel-sanders”).
  - athlete_gender: Athlete gender (e.g., “men” or “women”).
  - race_name: Lowercase-hyphenated race name (e.g., "san-francisco-t100-2025-women").
  - cleaned_race_name: Cleaned version of the race name (e.g., "San Francisco T100 2025 Women").
  - race_year: Year the race occurred.
  - race_date: Date of the race (e.g., “2025-06-01”).
  - race_tier: Tier classification of the race (e.g., “Gold Tier”).
  - race_country: Country the athlete represents (e.g., “Canada”).
  - race_distance: Race distance category (e.g., "Iron (140.6 miles)", "Half-Iron (70.3 miles)", "100 km", "Overall").
  - race_location: City and country of the race (e.g., "San Francisco, CA, United States").

  Cumulative time tracking (in seconds):
  - cumulative_seconds_after_swim: Time after swim segment.
  - cumulative_seconds_after_t1: Time after T1 transition.
  - cumulative_seconds_after_bike: Time after bike segment.
  - cumulative_seconds_after_t2: Time after T2 transition.
  - cumulative_seconds_after_run: Final time after the run.

  Rank tracking:
  - rank_after_swim: Athlete’s rank immediately after swim.
  - rank_after_t1: Rank after T1.
  - rank_after_bike: Rank after bike.
  - rank_after_t2: Rank after T2.
  - rank_after_run: Final rank after run.

  Position change metrics (relative movement):
  - position_change_in_t1: Rank change during T1 transition.
  - position_change_on_bike: Rank change during the bike leg.
  - position_change_in_t2: Rank change during T2 transition.
  - position_change_on_run: Rank change during the run leg.

 - swim_seconds/bike_seconds/run_seconds/overall_seconds: The actual time in seconds

  """


#──────────────────────────────────────────────────────────────────────────────
#General SQL Guidelines (applied across all query generations)
#──────────────────────────────────────────────────────────────────────────────
def GENERAL_SQL_GUIDELINES() -> str:
    return """

        If you must join table together, You may use `athlete_slug` and 'unique_race_id'. For time-based analysis, use `reporting_week` (weekly scores) or `race_date` (race day).If joining reporting_week to race_date, ensure to use DATE_TRUNC(race_date, week) to align them to the same week.
Do not join on cleaned_race_name as it is not unique across race years or race genders. 
        
        Keyword Mapping for Filters

        - "Half" or "70.3" → race_distance = 'Half-Iron (70.3 miles)' -- ❌ DO NOT DO THIS: -- WHERE race_name LIKE '%70.3%' -- ✅ DO THIS INSTEAD: -- WHERE race_distance = 'Half-Iron (70.3 miles)'
        - "Full" or "140.6" → race_distance = 'Iron (140.6 miles)' (do not search for this in race_name)
        - "Female" → athlete_gender = 'women', "Male" → athlete_gender = 'men' (do not search for this in race_name) -- ❌ DO NOT DO THIS: -- WHERE race_name LIKE '%women%' -- ✅ DO THIS INSTEAD: -- WHERE athlete_gender = 'women'
        - "T100" → organizer = 't100' or unique_race_id like '%t100%' (do not search for race_name LIKE '%t100%')
        - "DNF" or "Did Not Finish" → overall_seconds IS NULL
        
        Helpful SQL Tips for Query Generation

        General Structure

        Use CTEs (WITH clauses) to modularize and simplify logic.
        Always alias base tables and CTEs (e.g., trilytx_fct.fct_race_results_vs_predict AS p)
        Use those aliases in the SELECT, WHERE, JOIN, and QUALIFY clauses
        Avoid using unqualified column names when multiple tables or CTEs are involved
        Filter for relevant data early in the CTE chain to improve performance.
        In the final SELECT, only return the columns needed to answer the question.
        If possible, return a single row summarizing the results.
        If the result involves listing multiple values (e.g., names, races, locations), use STRING_AGG to combine them into a single comma-separated string per group.
        Ignore null values unless specifically asked for.
        Use ORDER BY and LIMIT to control result size when appropriate.

        Data Recency
        - Use: WHERE date = (SELECT MAX(date) FROM ...) or QUALIFY ROW_NUMBER() OVER (...) = 1
        - Use QUALIFY only with window functions (RANK(), ROW_NUMBER()).
        
        Filtering Rules
        -Exclude non-finishers with: overall_seconds IS NOT NULL
        -For Olympic races: unique_race_id LIKE '%olympic-games%'
        -Assume “latest” = most recent race_date or reporting_week if unspecified.
        
        Fuzzy Matching
        - Race name: LOWER(cleaned_race_name) LIKE '%eagleman%'
        - Location: race_location LIKE '%Oceanside%' or race_name LIKE '%Oceanside%'
        
        Include the Following When Relevant
        - Race Summaries: race name, athlete_gender, race_location, race_date, race_distance, organizer, overall_time, athlete_finishing_place
        - Athlete Info: athlete_name, athlete_year_of_birth, athlete_country, athlete_gender
        - provide 1 row of context when able:
        -- question: When was the last time athlete x was on the podium?
        -- answer: include race_name, race_date, race_location, race_distance, athlete_finishing_place, overall_time 
        """
def get_table_prompts() -> Dict[str, str]:
    """
    Returns a dictionary mapping table names to their detailed prompt strings.
    """
    return {
        "fct_race_results": FCT_RACE_RESULTS_PROMPT(),
        "fct_race_results_vs_predict": FCT_RACE_RESULTS_VS_PREDICT_PROMPT(),
        "fct_pto_scores_weekly": FCT_PTO_SCORES_WEEKLY_PROMPT(),
        "fct_race_segment_positions": FCT_RACE_SEGMENT_POSITIONS_PROMPT()
    }