import streamlit as st
st.set_page_config(page_title="Connect With Us",
    page_icon="https://github.com/dbaellow-rwa/trilytxbot/blob/fe681401e506fd4deccca9fa7c0c751c2cbbf070/assets/logo.png?raw=true",
    initial_sidebar_state="expanded",
    layout="wide")
st.title("🤝 Connect With Us")
# Cookie management for user authentication
from streamlit_cookies_manager import EncryptedCookieManager
import os
cookies = EncryptedCookieManager(prefix="trilytx_", password=os.environ["COOKIE_SECRET_TRILYTXBOT"])
if not cookies.ready():
    st.stop()
from utils.streamlit_utils import render_login_block,get_oauth
oauth2, redirect_uri = get_oauth()

with st.sidebar:
    render_login_block(oauth2, redirect_uri, cookies)


st.markdown("""
We’re building Trilytx in public — and we’d love for you to be part of it.

Whether you’re a triathlete, data nerd, coach, or curious fan, your questions, feedback, and ideas help shape this project.

---
            
### 📝 Join the Trilytx Beta
Want to join the leaderboard and shape the future of triathlon AI?
[Click here to sign up for the beta](https://docs.google.com/forms/d/e/1FAIpQLScAA8LmWCd0WUupNBp9QstbAtqkJNXwqkokTlJMb731xovzRA/viewform?usp=dialog)
             
--- 
### 💬 Join the Conversation

- 🗨️ [Join our Discord community](https://discord.gg/sUGvgYR8)
  Get early access updates, share insights, report bugs, and meet other triathlon data fans.

- 🐙 [View the Trilytxbot GitHub repo](https://github.com/dbaellow-rwa/trilytxbot)  
  Explore the code, contribute, or file an issue.

- 📸 [Follow us on Instagram @trilytx](https://instagram.com/trilytx)  
  For visual race insights, feature announcements, and leaderboard fun.

---

### 📬 Contact Us

Have a private question or want to collaborate?

- 📧 Email: [dustin@trilytx.com](mailto:dustin@trilytx.com)

---

Thanks for being part of our beta — together, we're building the smartest triathlon brain on the planet. 🧠

""")

