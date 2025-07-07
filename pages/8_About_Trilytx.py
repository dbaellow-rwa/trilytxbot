import streamlit as st
st.set_page_config(page_title="About Trilytx",
    page_icon="https://github.com/dbaellow-rwa/trilytxbot/blob/fe681401e506fd4deccca9fa7c0c751c2cbbf070/assets/logo.png?raw=true",
    initial_sidebar_state="expanded",
    layout="wide")
st.title("📘 About Trilytx")
# Cookie management for user authentication
from streamlit_cookies_manager import EncryptedCookieManager
import os
cookies = EncryptedCookieManager(prefix="trilytx_", password=os.environ["COOKIE_SECRET_TRILYTXBOT"])
if not cookies.ready():
    st.stop()
from utils.streamlit_utils import get_oauth
oauth2, redirect_uri = get_oauth()


from utils.whitepaper import render_whitepaper
from utils.executive_summary import render_summary_triathlon_community


tab1, tab2 = st.tabs(["📌 Executive Summary", "📄 Whitepaper"])

with tab1:
    render_summary_triathlon_community()

with tab2:
    render_whitepaper()
