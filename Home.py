# cd "C:\Users\dusti\OneDrive\Documents\GitHub\trilytxbot"
# streamlit run Home.py
import streamlit as st
import json
import requests as pyrequests  # rename to avoid conflict with google.auth.transport.requests
from streamlit_oauth import OAuth2Component
from config.app_config import USE_LOCAL
from utils.streamlit_utils import render_login_block,get_oauth
oauth2, redirect_uri = get_oauth()

# ───────────────────────────────
# Shared Beta Overview Block
# ───────────────────────────────
def show_beta_overview():
    st.markdown("""
<div style="max-width: 900px; margin: 0 auto; text-align: left;">

<h1 style="text-align: center;">🏁 Welcome to the Trilytx Beta!</h1>

<h3>🎯 Our Mission</h3>
<p>Trilytx is your AI-powered assistant for triathlon race analytics — designed to answer detailed questions about race results, athlete stats, matchups, and trends.</p>
<p>We're in <strong>Beta</strong> right now, and you're invited to help us shape the future.</p>

<hr/>

<h3>🤝 Why We're Doing This</h3>
<p>We're building a <strong>custom LLM</strong> fine-tuned on triathlon data — but to make it truly world-class, we need <strong>your real questions</strong> and <strong>your feedback</strong>.</p>
<p>By participating, you're helping us:</p>
<ul>
  <li>🧠 Train a smarter, faster, more accurate triathlon-specific model</li>
  <li>⚡ Reduce answer latency by refining SQL and RAG patterns</li>
  <li>📊 Expand domain knowledge through your natural questions</li>
</ul>

<hr/>

<h3>🔍 Trilytx: Current Beta vs Future Vision</h3>

<table style="width:100%; border-collapse: collapse;">
  <thead>
    <tr>
    <th style="text-align:left; background-color:#fff8dc; padding: 8px; color: black;">🟡 <strong>Current Beta (Today)</strong></th>
    <th style="text-align:left; background-color:#e6ffe6; padding: 8px; color: black;">🟢 <strong>Future Trilytx (Post-Fine-Tuning)</strong></th>
    </tr>
  </thead>
  <tbody>
    <tr><td style="padding: 8px;">Relies on OpenAI’s general-purpose model</td><td style="padding: 8px;">Uses a fine-tuned, triathlon-specific model</td></tr>
    <tr><td style="padding: 8px;">Requires complex prompt engineering to guide SQL generation</td><td style="padding: 8px;">Understands triathlon data patterns natively</td></tr>
    <tr><td style="padding: 8px;"><strong>Question → table guess → large prompt → SQL → data → answer</strong></td><td style="padding: 8px;"><strong>Question → SQL → data → answer</strong></td></tr>
    <tr><td style="padding: 8px;">Slower response time due to longer prompts and multiple LLM steps</td><td style="padding: 8px;">Faster, more efficient responses with compact prompts</td></tr>
    <tr><td style="padding: 8px;">Prone to errors if athlete or race context is unclear</td><td style="padding: 8px;">Learns from real questions + validated feedback to improve precision</td></tr>
    <tr><td style="padding: 8px;">Answers are occasionally vague or redundant</td><td style="padding: 8px;">Answers are targeted, accurate, and often deeper in insight</td></tr>
    <tr><td style="padding: 8px;">Limited to simpler queries to avoid SQL errors</td><td style="padding: 8px;">Capable of handling complex, multi-faceted questions</td></tr>
    <tr><td style="padding: 8px;">Basic error handling and retries</td><td style="padding: 8px;">Robust error recovery and adaptive learning</td></tr>
  </tbody>
</table>

<hr/>

<h3>🚀 How You Can Help</h3>
<ol>
  <li><strong>Ask real questions</strong> about races, athletes, and results</li>
  <li><strong>Vote 👍 or 👎</strong> on answers</li>
  <li>Come back often — the more data we gather, the smarter the system becomes</li>
</ol>
<p>Upvoted answers will help train a fine-tuned model — so your input has real impact.</p>

<hr/>

<h3>🎁 Beta Tester Perks</h3>
<ul>
  <li>🧪 Early access to upcoming features</li>
  <li>🏆 Recognition as a Founding Beta User</li>
  <li>🎉 Surprise rewards for top contributors</li>
</ul>

<hr/>

<h3>📝 Join the Trilytx Beta</h3>
<p>Want to join the leaderboard and shape the future of triathlon AI?</p>
<p><a href="https://docs.google.com/forms/d/e/1FAIpQLScAA8LmWCd0WUupNBp9QstbAtqkJNXwqkokTlJMb731xovzRA/viewform?usp=dialog" target="_blank"><strong>Click here to sign up for the beta</strong></a></p>
                
<p>We're excited to have you on this journey with us. Together, we can revolutionize triathlon analytics!</p>

<hr/>

</div>
""", unsafe_allow_html=True)



# ───────────────────────────────
# Render Page
# ───────────────────────────────

with st.sidebar:
    render_login_block(oauth2, redirect_uri)

if "user" in st.session_state:
    user_info = st.session_state["user"]
    st.success(f"Welcome back, {user_info.get('name', 'triathlete')} 👋")

    st.markdown("""
    ---
    ### 📚 Where to Go Next

    - 🧠 **Chatbot** — Ask questions about race results, athlete stats, and predictions  
    - 📌 **Trilytx Executive Summary** — Overview of features, roadmap, and vision
    - 📘 **Trilytx Whitepaper** - Accelerating Triathlon Intelligence Through Human-AI Collaboration
    - ℹ️ **About The Chatbot** — Learn what powers this project

    ---
    """)



show_beta_overview()