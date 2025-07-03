import streamlit as st
from utils.streamlit_utils import render_login_block,get_oauth
oauth2, redirect_uri = get_oauth()



# st.set_page_config(page_title="About the Trilytx Chatbot", layout="wide")
with st.sidebar:
    render_login_block(oauth2, redirect_uri)

st.title("🤖 About the Trilytx Chatbot")

st.markdown("""
The **Trilytx Chatbot** helps you analyze triathlon race data through natural language. It translates your questions into BigQuery SQL, queries a race performance database, and returns structured answers, charts, or summaries.

It’s optimized for triathlon-specific analysis — including PTO scores, athlete rankings, race performance summaries, and segment trends.
""")

with st.expander("✅ What the chatbot can handle"):
    st.markdown("""
- Generate **BigQuery SQL** to explore athlete performance, rankings, and race data  
- Compare athletes across time, gender, or distance  
- Summarize race outcomes (e.g., top finishers, average times)  
- Answer questions like:  
  • “Who had the fastest swim in Kona this year?”  
  • “How has Taylor Knibb’s PTO swim ranking changed over 6 months?”  
  • “List races where Ashleigh Gentle finished top 3.”  
""")

with st.expander("⚠️ What the chatbot cannot handle"):
    st.markdown("""
- Vague or unstructured prompts (e.g., “How’s Taylor doing?”)  
- Questions requiring info **not in the database** (e.g., weather, training plans)  
- Analysis without a clear data reference  
- Overly complex logic without defined structure (e.g., fuzzy joins + time trends)  
""")

with st.expander("💡 Tips for Better Prompts"):
    st.markdown("""
To get the best results:
- Be specific: mention athletes, races, timeframes, and metrics  
- Keep the question focused  
- Use real column names (like `swim_time`, `race_date`, or `overall_pto_score`)  
- Good examples:  
  • “Compare PTO swim rankings for Laura Philipp and Paula Findlay over 6 months”  
  • “List top 5 female finishers in Ironman California 2023”  
  • “Summarize Ashleigh Gentle’s race history in 2024”  
""")

with st.expander("📂 Available Schemas & Data Fields"):
    st.markdown("""
The chatbot uses several structured tables to analyze triathlon performance data. Here’s a breakdown of each core dataset and its key columns:

---

### 🏁 `trilytx_fct.fct_race_results`
Individual race-day performance results, one row per athlete per race.

**Key fields:**
- `athlete`, `athlete_slug`: Athlete name and slug (lowercase-hyphenated)
- `overall_seconds`, `overall_time`: Finish time in seconds (for math) and HH:MM:SS (for display)
- `swim_seconds`, `bike_seconds`, `run_seconds`: Segment times in seconds
- `swim_pto_score`, `bike_pto_score`, `run_pto_score`, `overall_pto_score`: Segment-level PTO scores (higher = better)
- `place`, `gender`, `distance`, `tier`, `organizer`, `location`, `race_date`
- `cleaned_race_name`, `race_name`: Cleaned display name and slug name
- `sof`: Strength of field
- Use this table to analyze real-world race performance and rankings.

---

### 📊 `trilytx_fct.fct_race_results_vs_predict`
Model-predicted race outcomes vs. actual results (one row per athlete per race).

**Key fields:**
- `athlete`, `race_name`, `race_date`, `gender`, `organizer`, `location`
- Predicted ranks: `swim_pto_rank`, `bike_pto_rank`, `run_pto_rank`, `overall_pto_rank`
- Actual ranks: `swim_actual_rank`, `bike_actual_rank`, `run_actual_rank`, `overall_actual_rank`
- Delta columns: `swim_delta`, `bike_delta`, `run_delta`, `overall_delta` (positive = outperformed)
- Use this table to analyze over/under-performance or model prediction accuracy.

---

### 🧠 `trilytx_fct.fct_pto_scores_weekly`
Weekly PTO scores for each athlete and distance group.

**Key fields:**
- `athlete`, `athlete_slug`, `reporting_week`, `distance_group`, `gender`, `country`
- Segment scores: `swim_pto_score`, `bike_pto_score`, `run_pto_score`, `overall_pto_score`
- Transition scores: `t1_pto_score`, `t2_pto_score`
- Relative ranks: `rank_*` columns compare athletes by distance, gender, country, etc.
- Use this table to compare athlete performance over time or generate PTO-based rankings.

**Prompting tip:** Always rank across the full gender and distance group, then filter for the athlete(s) you care about.

---

### 🧭 `trilytx_fct.fct_race_segment_positions`
Tracks athlete progress and rank at each stage of a race.

**Key fields:**
- `athlete`, `race_name`, `gender`, `race_date`, `tier`, `distance`, `location`
- Cumulative time after each segment: `cumulative_seconds_after_swim`, `cumulative_seconds_after_bike`, etc.
- Ranks after each segment: `rank_after_swim`, `rank_after_bike`, etc.
- Position changes: `position_change_in_t1`, `position_change_on_bike`, etc.
- Use this table to analyze pacing, segment position changes, or comeback performance during a race.

---

Use these fields to guide your questions. If you're unsure which table to use, just describe the kind of data you want — the chatbot will figure out the appropriate source.
""")


with st.expander("🔍 How It Works"):
    st.markdown("""
1. You enter a question in natural language.  
2. The chatbot converts it to a **BigQuery SQL query**.  
3. It executes the query and returns either:  
   - A results table  
   - A plain-language summary  
   - Or both  

It's tuned to work best with triathlon performance data and supports comparison logic, ranking, filters, and time-based analysis.
""")
    
with st.expander("⚙️ How to Use the Optional Filters (Sidebar Controls)"):
    st.markdown("""
You can use the **optional filters** in the sidebar or filter panel to refine your query results **without modifying your prompt**.

These filters let you narrow down results interactively before or after asking a question.

#### Available Filter Controls:

- **Athlete Name**  
  Type in all or part of an athlete’s name (e.g., “Laura” or “Taylor Knibb”) to return only matching results.

- **Distance Type**  
  Use this dropdown to focus on specific triathlon race formats:
  - `Half-Iron (70.3 miles)`
  - `Iron (140.6 miles)`
  - `100 km` (T100 format)
  - Other distances (for nonstandard events)

- **Gender**  
  Filter results to show only men’s or women’s races and rankings.

---

#### 💡 How These Filters Work:

- Filters are **optional**: leave any blank to include all options.
- Filters are **applied after** the SQL is generated, so they won’t interfere with how the chatbot interprets your question — they just make the result easier to explore.
- These filters work especially well when exploring tables or charts after asking a general question.

---

For example:
> If you ask: "Compare finish times across all Kona races,"  
> Then set `Gender = women` and `Distance = Iron (140.6 miles)` in the sidebar,  
> You’ll only see results for women competing in full Iron-distance Kona races.
""")

