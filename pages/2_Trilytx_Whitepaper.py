import streamlit as st
from utils.streamlit_utils import render_login_block,get_oauth
oauth2, redirect_uri = get_oauth()

with st.sidebar:
    render_login_block(oauth2, redirect_uri)

st.title("📘 Trilytx Whitepaper")
st.markdown("""
# Trilytx Whitepaper: Accelerating Triathlon Intelligence Through Human-AI Collaboration

## Overview
**Trilytx** is building the world’s first AI-powered triathlon data assistant — capable of answering natural language questions, generating full-length race recaps, and surfacing athlete insights from structured performance data. By combining athlete stats with large language models (LLMs) and human feedback, Trilytx delivers fast, contextual, and evolving insights for fans, coaches, and media pros.

## Problem Statement
Triathlon data is abundant — but insight is buried:

- Fans can’t easily ask things like “How has Lucy Charles performed in swims over the last 2 years?”
- Coaches struggle to track segment trends and position changes across races  
- Broadcasters spend hours pulling stat packs from scattered sources  

Existing tools are either too rigid (charts, filters) or too generic (AI with no sport context).

## Our Approach
Trilytx combines three core layers:

1. **Structured Data (BigQuery)**  
   - Central warehouse with results, splits, rankings, athlete bios, and projections  
   - Weekly PTO scores and trend metrics down to the segment level

2. **Retrieval-Augmented Generation (RAG)**  
   - Embedding-based search over athlete bios, race history, and user feedback  
   - Context-rich prompt assembly feeds LLMs for more accurate outputs

3. **Human-in-the-Loop Feedback**  
   - Every query, answer, and vote is logged  
   - High-confidence outputs are used to fine-tune our domain models  
   - Performance improves with every real-world triathlon question

## Current Architecture
- **Input**: Natural language query or recap request  
- **LLM 1**: SQL generation via OpenAI (GPT-4) with structured schema context  
- **Execution**: Query runs on BigQuery's triathlon warehouse  
- **LLM 2**: Generates recap or summary in plain English  
- **Logging**: Results, feedback, and metadata stored for fine-tuning + RAG

## 🔥 New Capability: Athlete Profiles with Trend Tracking
Users can now view rich, interactive athlete dashboards:

- Full race history including splits, finish times, and strength of field  
- Rankings and PTO segment scores across the past 2 years  
- Breakdown by swim, bike, run, and overall performance  
- Automatically detects rank shifts (e.g., national rank, gender-specific rank)  
- Built-in LLM summaries for recap generation or newsletter copy

## LLM-Powered Recaps
Generate custom long-form recaps for any athlete or race:

- Highlights podiums, segment performance, and surprises  
- Supports natural language prompts like “Focus on the bike” or “Make it poetic”  
- Useful for post-race reports, media previews, and broadcast prep  

## Beta Participation
Trilytx is in **Beta**, and we’re inviting testers to:

- Ask questions about athletes, races, or segment trends  
- Build custom recaps using natural instructions  
- Vote on summary quality to train our models  
- Earn early access, swag, and leaderboard recognition

## Fine-Tuning Strategy
We log and use the following for each interaction:

- Original user query  
- Generated SQL  
- Result summary or recap  
- Upvote/downvote feedback

These are used to train two custom models:

- **SQL generation (function-first)**  
- **Answer generation (chat-style)**  

Fine-tuning benefits:

- 2× faster query handling  
- 40–70% fewer hallucinations  
- Stronger sport-specific reasoning

## Future Vision
Once fine-tuned and deployed, Trilytx will support:

- **Fans**: Historical stats, trivia, and interactive previews  
- **Coaches**: Segment deltas, taper optimization, and progression tracking  
- **Broadcasters**: Stat summaries and real-time athlete comps  
- **Brands & Organizers**: Automated race recaps and insights

## Join the Trilytx Beta
Want to shape the future of triathlon analytics?

👉 [Join the Beta](https://docs.google.com/forms/d/e/1FAIpQLScAA8LmWCd0WUupNBp9QstbAtqkJNXwqkokTlJMb731xovzRA/viewform?usp=dialog)

We're building this **with** the triathlon community — not just for it.  
Thanks for being part of the journey. 🏊‍♂️🚴‍♀️🏃‍♂️
""")
