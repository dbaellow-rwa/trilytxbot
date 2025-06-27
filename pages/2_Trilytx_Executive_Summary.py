import streamlit as st
from utils.streamlit_utils import render_login_block,get_oauth
oauth2, redirect_uri = get_oauth()

with st.sidebar:
    render_login_block(oauth2, redirect_uri)

st.title("Trilytx Executive Summary")
st.markdown("""
### 📌 Executive Summary  
**Trilytx** is a domain-specific AI assistant that makes triathlon performance data accessible through natural language. Built with Streamlit and powered by OpenAI’s GPT models, it translates user questions into BigQuery SQL, retrieves structured results, and delivers readable, insightful summaries.

---

### 🚀 Key Features  

**Natural Language Interface**  
Ask questions like:  
• “Who won Kona in 2023?”  
• “How did Lionel Sanders perform in bike segments this year?”

**BigQuery Backend**  
Fast, scalable querying over detailed athlete- and race-level data.

**GPT-Powered SQL Generation**  
Modular prompt templates drive accurate, domain-aware SQL generation.

**Streamlit App on Heroku**  
Deployed as a responsive multi-page app with CI/CD and auto-scaling.

**Thoughtful UX Design**  
Includes sidebar filters, follow-up question support, and chat memory.

**Feedback & Logging**  
All interactions are logged to BigQuery for quality review and iteration.

---

### 🧪 Roadmap / Future Enhancements  

**RAG (Retrieval-Augmented Generation)**  
Ground answers in metadata and context through embedding search.

**Long-Term Embedding Memory**  
Track athlete trends and enable more coherent multi-turn chats.

**Enterprise Features**  
Add authentication, role-based permissions, and export tools for BI teams.
""")

