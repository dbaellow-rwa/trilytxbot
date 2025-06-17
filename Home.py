# cd "C:\Users\dusti\OneDrive\Documents\GitHub\trilytxbot"
# streamlit run app.py

import streamlit as st

st.set_page_config(page_title="Welcome to Trilytx", layout="centered")

st.title("🏁 Welcome to Trilytx")
st.markdown("""
Welcome to **Trilytx**, where triathlon meets data.

Explore:
- 🧠 **[Chatbot](./Chatbot)** — Ask questions about race results, athlete stats, and predictions.
- ℹ️ **[About Trilytx](./About_Trilytx)** — Learn what powers this project and how it works.

Use the sidebar to navigate between pages, or click a link above to get started!
""")
