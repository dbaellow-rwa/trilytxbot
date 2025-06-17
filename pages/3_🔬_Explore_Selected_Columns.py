import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Explore Selected Columns", layout="wide")
st.title("🔬 Explore Selected Columns")

if "selected_df" not in st.session_state:
    st.warning("No data to explore. Go back to the Chatbot and run a query.")
    st.stop()

df = st.session_state.selected_df

# ─────────────────────────────────────────────────────────────────────────────
# Column Selector
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("### 📌 Step 1: Select Columns")
cols = st.multiselect("Choose columns to display", df.columns.tolist(), default=df.columns.tolist())
df_selected = df[cols]
st.dataframe(df_selected)

# ─────────────────────────────────────────────────────────────────────────────
# Search Filter
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("### 🔍 Step 2: Filter Rows (Optional)")
search_term = st.text_input("Enter a keyword to search across all visible columns:")

if search_term:
    df_filtered = df_selected[df_selected.apply(
        lambda row: row.astype(str).str.contains(search_term, case=False, na=False).any(), axis=1
    )]
    st.dataframe(df_filtered)
else:
    df_filtered = df_selected

# ─────────────────────────────────────────────────────────────────────────────
# Summary Stats
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("### 📊 Step 3: Summary Statistics")
if not df_filtered.empty:
    st.write(df_filtered.describe(include='all').transpose())
else:
    st.info("No rows match your search.")

# ─────────────────────────────────────────────────────────────────────────────
# Chart Builder
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("### 📈 Step 4: Simple Chart Builder")

# Include "Count of Records" as a Y-axis option
chart_y_options = ["Count of Records"] + df_filtered.select_dtypes(include="number").columns.tolist()

if len(df_filtered.columns) >= 1: # We need at least one column for the X-axis
    x_axis = st.selectbox("X-axis", options=df_filtered.columns.tolist())
    y_axis = st.selectbox("Y-axis", options=chart_y_options)

    if x_axis: # Ensure X-axis is selected
        # Initialize x_axis_type here to ensure it's always defined
        # This allows Altair to infer the type if not explicitly set later for "Count of Records"
        x_axis_type = None  # or omit it entirely and let Altair infer the type
# <--- Ensure this line is present and executed

        if y_axis == "Count of Records":
            # For "Count of Records", the y-axis encoding is 'count():Q'
            x_axis_type = "nominal" # Treat X as categorical for counts when counting
            chart = alt.Chart(df_filtered).mark_bar().encode(
                x=alt.X(x_axis, type=x_axis_type, sort="-y"),
                y=alt.Y('count():Q', title='Count of Records'), # Use count() aggregation
                tooltip=[x_axis, alt.Tooltip('count():Q', title='Count')]
            ).properties(height=400)
        else:
            # For actual numeric columns, use the selected column name
            # x_axis_type remains alt.Undefined (or whatever Altair infers)
            chart = alt.Chart(df_filtered).mark_bar().encode(
                x=alt.X(x_axis, type=x_axis_type, sort="-y"), # Using x_axis_type which is now always defined
                y=alt.Y(y_axis, title=y_axis), # Use the selected numeric column
                tooltip=[x_axis, y_axis]
            ).properties(height=400)

        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Please select an X-axis column to build a chart.")
else:
    st.info("Not enough data or columns to build a chart.")


if st.button("⬅️ Back"):
    st.switch_page("2_Chatbot.py")  # Put correct file path if needed
