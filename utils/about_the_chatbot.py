import streamlit as st

def render_about():
    with st.expander("📖 About the Trilytx Chatbot"):
        st.markdown("""
The **Trilytx Chatbot** helps you analyze triathlon race data through natural language. It translates your questions into BigQuery SQL, queries a race performance database, and returns structured answers, charts, or summaries.

It’s optimized for triathlon-specific analysis — including PTO scores, athlete rankings, race performance summaries, and segment trends.
""")

        st.markdown("### ✅ What the chatbot can handle")
        st.markdown("""
- Generate **BigQuery SQL** to explore athlete performance, rankings, and race data  
- Compare athletes across time, gender, or distance  
- Summarize race outcomes (e.g., top finishers, average times)  
- Answer questions like:  
  • “Who had the fastest swim in Kona this year?”  
  • “How has Taylor Knibb’s PTO swim ranking changed over 6 months?”  
  • “List races where Ashleigh Gentle finished top 3.”
""")

        st.markdown("### ⚠️ What the chatbot cannot handle")
        st.markdown("""
- Vague or unstructured prompts (e.g., “How’s Taylor doing?”)  
- Questions requiring info **not in the database** (e.g., weather, training plans)  
- Analysis without a clear data reference  
- Overly complex logic without defined structure (e.g., fuzzy joins + time trends)
""")

        st.markdown("### 💡 Tips for Better Prompts")
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

        st.markdown("### 📂 Available Schemas & Data Fields")
        st.markdown("""
**🏁 `trilytx_fct.fct_race_results`**  
Individual race-day performance results.

Key fields:
- `athlete`, `athlete_slug`, `overall_seconds`, `swim_seconds`, `bike_seconds`, `run_seconds`
- PTO scores: `swim_pto_score`, `bike_pto_score`, `run_pto_score`, `overall_pto_score`
- `place`, `gender`, `distance`, `organizer`, `location`, `race_date`, `sof`

---

**📊 `trilytx_fct.fct_race_results_vs_predict`**  
Model-predicted outcomes vs. actual results.

Key fields:
- Predicted vs actual PTO ranks and deltas per segment
- Use to evaluate over/under-performance

---

**🧠 `trilytx_fct.fct_pto_scores_weekly`**  
Weekly PTO scores and relative rankings.

Key fields:
- `athlete`, `reporting_week`, `distance_group`, segment scores, rank fields
- Use for trends and comparisons over time

---

**🧭 `trilytx_fct.fct_race_segment_positions`**  
Tracks rank and time after each segment.

Key fields:
- `cumulative_seconds_after_*`, `rank_after_*`, `position_change_*`
- Use to understand pacing and segment dynamics
""")

        st.markdown("### 🔍 How It Works")
        st.markdown("""
1. You enter a question in natural language.  
2. The chatbot converts it to a **BigQuery SQL query**.  
3. It runs the query and returns:
   - A results table  
   - A summary  
   - Or both  
""")

        st.markdown("### ⚙️ How to Use the Optional Filters")
        st.markdown("""
Filters let you narrow down results **without rewriting your question**.

**Filter Options:**
- **Athlete Name**: match all or part of an athlete’s name  
- **Distance Type**: e.g., 70.3, Ironman, 100km  
- **Gender**: men or women  
- **Organizer**: Ironman, PTO, T100, etc.

💡 Filters apply after the SQL is generated — they just refine what you see.
""")
