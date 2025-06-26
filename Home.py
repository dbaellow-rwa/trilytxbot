# cd "C:\Users\dusti\OneDrive\Documents\GitHub\trilytxbot"
# streamlit run Home.py
import streamlit as st
import json
import requests as pyrequests  # rename to avoid conflict with google.auth.transport.requests
from streamlit_oauth import OAuth2Component

import streamlit as st
import json
import requests as pyrequests
from streamlit_oauth import OAuth2Component

# ───── Load Credentials ─────
with open("google_credentials.json") as f:
    creds = json.load(f)["web"]

# ───── Init OAuth2 ─────
oauth2 = OAuth2Component(
    client_id=creds["client_id"],
    client_secret=creds["client_secret"],
    authorize_endpoint=creds["auth_uri"],
    token_endpoint=creds["token_uri"]
)

redirect_uri = creds["redirect_uris"][1]
scope = "openid email profile"

# ───── Login Flow ─────
# If already logged in, skip login button
if "user" in st.session_state:
    user_info = st.session_state["user"]
    st.success(f"Welcome back, {user_info.get('name', 'triathlete')} 👋")
    st.image(user_info.get("picture", ""), width=60)
    st.markdown(f"**Email:** {user_info.get('email')}")
    
    st.title("🏁 Welcome to Trilytx")
    st.markdown("""
    Welcome to **Trilytx**, where triathlon meets data.

    Explore:
    - 🧠 **Chatbot** — Ask questions about race results, athlete stats, and predictions.
    - ℹ️ **About Trilytx** — Learn what powers this project and how it works.
    """)
    
    if st.button("🔓 Logout"):
        del st.session_state["user"]
        st.rerun()

else:
    token = oauth2.authorize_button(
        name="🔐 Login with Google",
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
                st.error("Failed to fetch user info from Google.")
        else:
            st.error("OAuth token missing access_token.")
    else:
        st.warning("Please log in with Google to access Trilytx.")

