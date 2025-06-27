# cd "C:\Users\dusti\OneDrive\Documents\GitHub\trilytxbot"
# streamlit run Home.py
import streamlit as st
import json
import requests as pyrequests  # rename to avoid conflict with google.auth.transport.requests
from streamlit_oauth import OAuth2Component

# ───────────────────────────────
# Shared Beta Overview Block
# ───────────────────────────────
def show_beta_overview():
    st.title("🏁 Welcome to the Trilytx Beta!")
    st.markdown("""
    ### 🎯 Our Mission

    Trilytx is your AI-powered assistant for triathlon race analytics — designed to answer detailed questions about race results, athlete stats, matchups, and trends.

    We're in **Beta** right now, and you're invited to help us shape the future.

    ---
                
    
    ### 🤝 Why We're Doing This

    We're building a **custom LLM** fine-tuned on triathlon data — but to make it truly world-class, we need **your real questions** and **your feedback**.

    By participating, you're helping us:

    - 🧠 Train a smarter, faster, more accurate triathlon-specific model  
    - ⚡ Reduce answer latency by refining SQL and RAG patterns  
    - 📊 Expand domain knowledge through your natural questions

    ---
    ### 🔍 Trilytx: Current Beta vs Future Vision

    | 🟡 **Current Beta (Today)** | 🟢 **Future Trilytx (Post-Fine-Tuning)** |
    |----------------------------|------------------------------------------|
    | Relies on OpenAI’s general-purpose model | Uses a fine-tuned, triathlon-specific model |
    | Requires complex prompt engineering to guide SQL generation | Understands triathlon data patterns natively |
    | **Question → table guess → large prompt → SQL → data → answer** | **Question → SQL → data → answer** |
    | Slower response time due to longer prompts and multiple LLM steps | Faster, more efficient responses with compact prompts |
    | Prone to errors if athlete or race context is unclear | Learns from real questions + validated feedback to improve precision |
    | Answers are occasionally vague or redundant | Answers are targeted, accurate, and often deeper in insight |
    | Limited to simpler queries to avoid SQL errors | Capable of handling complex, multi-faceted questions |
    | Basic error handling and retries | Robust error recovery and adaptive learning |

    ---
                
    ### 🚀 How You Can Help

    1. **Ask real questions** about races, athletes, and results  
    2. **Vote 👍 or 👎** on answers  
    3. Come back often — the more data we gather, the smarter the system becomes

    Upvoted answers will help train a fine-tuned model — so your input has real impact.

    ---

    ### 🎁 Beta Tester Perks

    - 🧪 Early access to upcoming features  
    - 🏆 Recognition as a Founding Beta User  
    - 🎉 Surprise rewards for top contributors

    ---
                
    ### 📝 Join the Trilytx Beta
    - Want to join the leaderboard and shape the future of triathlon AI?
    - [Click here to sign up for the beta](https://docs.google.com/forms/d/e/1FAIpQLScAA8LmWCd0WUupNBp9QstbAtqkJNXwqkokTlJMb731xovzRA/viewform?usp=dialog)

    We're excited to have you on this journey with us. Together, we can revolutionize triathlon analytics!
                
    --- 
    """)

# ───────────────────────────────
# Load Google OAuth Credentials
# ───────────────────────────────
with open("google_credentials.json") as f:
    creds = json.load(f)["web"]

oauth2 = OAuth2Component(
    client_id=creds["client_id"],
    client_secret=creds["client_secret"],
    authorize_endpoint=creds["auth_uri"],
    token_endpoint=creds["token_uri"]
)

redirect_uri = creds["redirect_uris"][1]
scope = "openid email profile"

# ───────────────────────────────
# Render Page
# ───────────────────────────────

with st.sidebar:
    st.header("🔐 Log In")

    if "user" in st.session_state:
        user_info = st.session_state["user"]
        st.success(f"Welcome, {user_info.get('name', 'triathlete')} 👋")
        st.image(user_info.get("picture", ""), width=80)
        st.markdown(f"**Email:** {user_info.get('email')}")

        if st.button("Logout"):
            del st.session_state["user"]
            st.rerun()

    else:
        token = oauth2.authorize_button(
            name="Login with Google",
            redirect_uri=redirect_uri,
            scope=scope
        )

        if token:
            raw_token = token.get("token")
            if raw_token and "access_token" in raw_token:
                response = pyrequests.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {raw_token['access_token']}"}
                )
                if response.status_code == 200:
                    user_info = response.json()
                    st.session_state["user"] = user_info
                    st.rerun()
                else:
                    st.error("❌ Failed to fetch user info from Google.")
            else:
                st.error("❌ OAuth token missing access_token.")
        else:
            st.warning("👆 Please log in with Google to access full features.")

if "user" in st.session_state:
    user_info = st.session_state["user"]
    st.success(f"Welcome back, {user_info.get('name', 'triathlete')} 👋")
    st.image(user_info.get("picture", ""), width=60)
    st.markdown(f"**Email:** {user_info.get('email')}")

    st.markdown("""
    ---
    ### 📚 Where to Go Next

    - 🧠 **Chatbot** — Ask questions about race results, athlete stats, and predictions  
    - ℹ️ **About Trilytx** — Learn what powers this project

    ---
    """)

    if st.button("🔓 Logout"):
        del st.session_state["user"]
        st.rerun()


show_beta_overview()