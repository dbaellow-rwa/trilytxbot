import streamlit as st
from utils.streamlit_utils import get_oauth
oauth2, redirect_uri = get_oauth()


st.title("Trilytx Executive Summary")
st.markdown("""
### 📌 Executive Summary  
**Trilytx** is a domain-specific AI assistant that makes triathlon performance data accessible through natural language. Built with Streamlit and powered by OpenAI’s GPT models, it translates user questions into BigQuery SQL, retrieves structured results, and delivers readable, insightful summaries.

Now, Trilytx also generates full **LLM-powered race recaps** and **athlete summaries**, transforming raw race data into compelling narratives and personalized performance reviews — tailored to the user’s tone, focus, or audience.

---

### 🚀 Key Features  

**Natural Language Interface**  
Ask questions like:  
• “Who won Kona in 2023?”  
• “How did Lionel Sanders perform in bike segments this year?”

**Race Recap Generator (NEW)**  
Generate AI-written recaps for any race, with sections like:  
• 🏅 Podium Highlights  
• 📈 Overperformers  
• 📉 Underperformers  
• 📊 Segment Trends  
• 🏁 Analyst Commentary  
Supports custom instructions (e.g., “Focus on the swim” or “Write it like a pirate”).

**Athlete Summary Generator (NEW)**  
Get personalized summaries for any athlete:  
• Trends in race performance over time  
• Segment strengths and weaknesses  
• Notable finishes and recent momentum  
Customize with prompts like “Focus on 70.3 events” or “Compare swim vs run performance.”

**BigQuery Backend**  
Fast, scalable querying over detailed athlete- and race-level data.

**GPT-Powered SQL Generation**  
Modular prompt templates drive accurate, domain-aware SQL generation.

**Streamlit App on Heroku**  
Deployed as a responsive multi-page app with CI/CD and auto-scaling.

**Thoughtful UX Design**  
Includes sidebar filters, follow-up question support, chat memory, and recap customization.

**Feedback & Logging**  
All queries, summaries, and recaps are logged to BigQuery for ongoing model training and quality improvement.

---

### 🧪 Roadmap / Future Enhancements  

**RAG (Retrieval-Augmented Generation)**  
Ground answers in metadata and context through embedding search.

**Long-Term Embedding Memory**  
Track athlete trends and enable more coherent multi-turn chats.

**Enterprise Features**  
Add authentication, role-based permissions, and export tools for BI teams.
""")

