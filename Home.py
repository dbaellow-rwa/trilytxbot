# cd "C:\Users\dusti\OneDrive\Documents\GitHub\trilytxbot"
# streamlit run Home.py
import streamlit as st
import json
import requests as pyrequests  # rename to avoid conflict with google.auth.transport.requests
from streamlit_oauth import OAuth2Component
from config.app_config import USE_LOCAL
from utils.streamlit_utils import render_login_block,get_oauth
oauth2, redirect_uri = get_oauth()

import warnings
if not USE_LOCAL:
    warnings.filterwarnings("ignore", category=DeprecationWarning)

# ───────────────────────────────
# Shared Beta Overview Block
# ───────────────────────────────
def show_beta_overview():
    st.markdown("""
<div style="max-width: 900px; margin: 0 auto; text-align: left;">

<h1 style="text-align: center;">🏁 Welcome to the Trilytx Beta</h1>

<h3>🎯 Our Mission</h3>
<p><strong>Trilytx</strong> is your AI-powered assistant for triathlon data — built to answer natural language questions, generate full-length race recaps, and spotlight performance trends across athletes, events, and seasons.</p>
<p>You’re part of our <strong>Beta</strong> program, helping shape the future of triathlon analytics.</p>

<hr/>

<h3>🤝 Why This Matters</h3>
<p>We’re training a <strong>custom large language model (LLM)</strong> specifically for triathlon — but it needs real usage to learn:</p>
<ul>
  <li>🧠 Smarter, faster answers tuned to the sport</li>
  <li>⚙️ More accurate SQL generation + fewer hallucinations</li>
  <li>📚 Deeper understanding of athlete, segment, and trend context</li>
</ul>
<p>Your questions and feedback are critical to building a world-class triathlon assistant.</p>

<hr/>

<h3>🆕 What’s New: Athlete Profiles + LLM Recaps</h3>
<p>We now support two powerful features:</p>
<ul>
  <li><strong>Athlete Profiles</strong>: Race history, segment splits, PTO score trends, and rankings — all in one place</li>
  <li><strong>LLM-Powered Recaps</strong>: Full-text summaries using structured race data + customizable instructions</li>
</ul>
<p>Whether you’re a fan, coach, or broadcaster — Trilytx makes tri data actionable, fast, and fun.</p>

<hr/>

<h3>🔍 Trilytx: Beta Today vs the Future</h3>

<table style="width:100%; border-collapse: collapse;">
  <thead>
    <tr>
    <th style="text-align:left; background-color:#fff8dc; padding: 8px; color: black;">🟡 <strong>Current Beta</strong></th>
    <th style="text-align:left; background-color:#e6ffe6; padding: 8px; color: black;">🟢 <strong>Post-Fine-Tuning</strong></th>
    </tr>
  </thead>
  <tbody>
    <tr><td style="padding: 8px;">Uses general-purpose OpenAI model</td><td style="padding: 8px;">Trained on triathlon-specific data + questions</td></tr>
    <tr><td style="padding: 8px;">Manual prompt structuring needed for good SQL</td><td style="padding: 8px;">Understands schema + sport-specific logic natively</td></tr>
    <tr><td style="padding: 8px;">Long prompts with table guessing + retries</td><td style="padding: 8px;">Direct Q → SQL → Answer in fewer steps</td></tr>
    <tr><td style="padding: 8px;">Occasional vagueness or misunderstanding</td><td style="padding: 8px;">Tighter, more targeted, confident responses</td></tr>
    <tr><td style="padding: 8px;">Limited ability to answer complex, layered queries</td><td style="padding: 8px;">Handles multi-part, comparative, and historical questions</td></tr>
    <tr><td style="padding: 8px;">Race recaps are powered by GPT-4 and user prompts</td><td style="padding: 8px;">Recaps will be fine-tuned for segment logic + race context</td></tr>
    <tr><td style="padding: 8px;">Basic feedback loop (votes only)</td><td style="padding: 8px;">Adaptive learning from high-quality answers + corrections</td></tr>
  </tbody>
</table>

<hr/>

<h3>🚀 How You Can Help</h3>
<ol>
  <li><strong>Ask real questions</strong> — about athletes, events, matchups, rankings</li>
  <li><strong>Use the recap tool</strong> with creative instructions (“focus on swim”, “make it dramatic”)</li>
  <li><strong>Vote</strong> 👍 or 👎 on results — this feedback trains the future model</li>
  <li><strong>Return regularly</strong> — each use sharpens Trilytx’s accuracy and insight</li>
</ol>

<hr/>

<h3>🎁 Beta Tester Perks</h3>
<ul>
  <li>🚀 Early access to new tools and dashboards</li>
  <li>🏅 Recognition as a Founding Beta User</li>
  <li>🎉 Surprise rewards for top contributors</li>
</ul>

<hr/>

<h3>📝 Join the Trilytx Beta</h3>
<p>Want to be part of the leaderboard and shape triathlon’s future with AI?</p>
<p><a href="https://docs.google.com/forms/d/e/1FAIpQLScAA8LmWCd0WUupNBp9QstbAtqkJNXwqkokTlJMb731xovzRA/viewform?usp=dialog" target="_blank"><strong>Click here to sign up</strong></a></p>

<p>Thanks for riding with us. 🏊‍♂️🚴‍♀️🏃‍♂️ Let’s make triathlon data intelligent, together.</p>

<hr/>

</div>
""", unsafe_allow_html=True)





# ───────────────────────────────
# Render Page
# ───────────────────────────────

with st.sidebar:
    render_login_block(oauth2, redirect_uri)

show_beta_overview()