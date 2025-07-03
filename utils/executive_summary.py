import streamlit as st
# def render_executive_summary():
#     audience = st.radio(
#         "Choose summary view:",
#         ["Triathlon Community", "Data Scientists", "Sponsors & Media"],
#         horizontal=True
#     )

#     if audience == "Triathlon Community":
#         render_summary_triathlon_community()
#     elif audience == "Data Scientists":
#         render_summary_data_scientists()
#     else:
#         render_summary_sponsors()
def render_summary_triathlon_community():
    st.markdown("""
<div style="max-width: 900px; margin: 0 auto; text-align: left;">

<h3>🏁 Executive Summary – Triathlon Community</h3>

<p><strong>Trilytx</strong> is your personal triathlon data assistant. Ask natural questions, get clear answers, and explore athlete and race insights without needing spreadsheets or coding.</p>

<p>Now, you can even create <strong>full race recaps</strong> and <strong>athlete summaries</strong> — written by AI, using real data — in your voice and style.</p>

<hr/>

<h3>🚀 What You Can Do</h3>

<ul>
  <li><strong>Ask questions like:</strong><br>
      • “How did Chelsea Sodaro perform in 2023?”<br>
      • “What were the fastest bike splits at 70.3 Oceanside?”</li>
</ul>

<ul>
  <li><strong>Create Race Recaps (NEW):</strong><br>
      • 🏅 Podium highlights<br>
      • 📈 Standout performances<br>
      • 📉 Tough days<br>
      • 📊 Segment breakdowns<br>
      • 🗣️ Analyst-style commentary</li>
</ul>

<ul>
  <li><strong>Athlete Summaries (NEW):</strong><br>
      • Segment strengths<br>
      • Trends over time<br>
      • Recent performances</li>
</ul>

<p>🎨 Add your spin with prompts like:<br>
“Make it sound dramatic” or “Focus on swim performance”</p>

<hr/>

<h3>🔧 Under the Hood (if you're curious)</h3>

<ul>
  <li>Powered by OpenAI GPT + BigQuery</li>
  <li>Built in Streamlit, hosted on Heroku</li>
  <li>Learns from your votes to improve</li>
  <li>Updated weekly with new features</li>
</ul>

<hr/>

<h3>🔮 What’s Coming</h3>

<ul>
  <li>Smarter answers with athlete/race context</li>
  <li>Deeper recaps + long-term memory</li>
  <li>Shareable recap cards + media tools</li>
</ul>

<p>Thanks for being part of the beta! 💪</p>

</div>
""", unsafe_allow_html=True)


def render_summary_data_scientists():
    st.markdown("""
<div style="max-width: 900px; margin: 0 auto; text-align: left;">
### 🧠 Executive Summary – Data Scientists  

**Trilytx** is a domain-specific LLM assistant for triathlon analytics. Built on Streamlit and powered by OpenAI, it translates natural language into BigQuery SQL, retrieves structured results, and summarizes insights for fans, coaches, and analysts.

Now enhanced with **LLM-generated race recaps** and **athlete performance narratives**, it demonstrates how foundation models can drive storytelling over sports telemetry data.

---

### 🔍 Core Capabilities  

**Natural Language → SQL → Insights**  
Examples:  
• “Show all 70.3 podium finishes by American women in 2023”  
• “Compare Sam Long’s bike split trends over time”  

**Race Recap Generator (NEW):**  
Uses modular LLM prompting to generate:  
• Podium summaries  
• Performance deltas  
• Segment trends  
• Analyst commentary  

**Athlete Summary Generator (NEW):**  
Auto-generates personalized breakdowns based on:  
• Segment strengths  
• Momentum across seasons  
• Recent improvements  

**BigQuery Integration:**  
Handles multi-join queries on normalized athlete/race tables.

**Prompt Engineering:**  
Uses dynamic prompt templates and fallback logic to reduce hallucinations.

**Deployed on Heroku:**  
Multi-page Streamlit app with CI/CD and usage logging.

---

### 📈 Data Stack Enhancements Coming  

• RAG-based metadata grounding  
• Embedding memory for athlete-specific context  
• RLHF from recap and summary corrections  
• Role-based access + export tools  
</div>
""", unsafe_allow_html=True)
def render_summary_sponsors():
    st.markdown("""
<div style="max-width: 900px; margin: 0 auto; text-align: left;">
### 📣 Executive Summary – Sponsors & Media  

**Trilytx** is a smart assistant for triathlon storytelling. It takes raw performance data and turns it into compelling summaries, race recaps, and athlete narratives — ideal for newsletters, broadcast prep, or brand performance tracking.

Built with OpenAI GPT + BigQuery, it’s your shortcut to insights, fast.

---

### ✨ What You Can Do

**🗣️ Ask questions like:**  
• “Who had the best run split in the men’s field at Kona?”  
• “How’s Taylor Knibb trending on the bike?”  

**📝 Get Media-Ready Recaps (NEW):**  
• Podium + highlight summaries  
• Segment breakdowns  
• Performance surprises  
• Custom tones — dramatic, technical, playful  

**👤 Track Sponsored Athletes**  
See trends, strengths, and how they performed by segment.

**📦 Perfect for:**  
• Newsletter and blog content  
• Live event prep  
• Partner reports  
• Podcast scripts  

---

### 🛠️ Under the Hood

• Built with GPT + BigQuery  
• Streamlit frontend on Heroku  
• Query + summary logging for model improvement  

---

### 📈 What’s Coming

• Automated content packs by sponsor/region  
• Branded race summaries and athlete cards  
• Share/export tools for media use  

Join the beta — and help us shape the next generation of triathlon coverage.
</div>
""", unsafe_allow_html=True)
