import streamlit as st
st.set_page_config(page_title="About Trilytx", layout="wide")
st.title("📘 About Trilytx")

from utils.streamlit_utils import render_login_block,get_oauth
oauth2, redirect_uri = get_oauth()


from utils.whitepaper import render_whitepaper
from utils.executive_summary import render_summary_triathlon_community

with st.sidebar:
    render_login_block(oauth2, redirect_uri)


tab1, tab2 = st.tabs(["📌 Executive Summary", "📄 Whitepaper"])

with tab1:
    render_summary_triathlon_community()

with tab2:
    render_whitepaper()
