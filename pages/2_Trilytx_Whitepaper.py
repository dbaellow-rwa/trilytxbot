import streamlit as st
from utils.streamlit_utils import render_login_block,get_oauth
oauth2, redirect_uri = get_oauth()

with st.sidebar:
    render_login_block(oauth2, redirect_uri)

st.title("📘 Trilytx Whitepaper")
st.markdown("""
# Trilytx Whitepaper: Accelerating Triathlon Intelligence Through Human-AI Collaboration

## Overview
Trilytx is building the world's first AI-powered triathlon data assistant designed to answer natural language questions about races, athletes, matchups, and trends. By blending structured data with generative AI and user feedback, Trilytx delivers accurate, fast, and context-aware answers that evolve with the sport.

## Problem Statement
Despite the explosion of triathlon data across results databases, leaderboards, and athlete histories, it remains difficult for fans, coaches, and athletes to:

- Answer comparative or contextual queries (e.g., "Has Sam Long ever beaten Lionel Sanders in a 70.3?")
- Explore trends in performance, training load, or seasonal patterns
- Generate quick insights without manual filtering and analysis

Existing tools are either too rigid (filters, charts) or too opaque (news articles, subjective commentary).

## Our Approach
Trilytx is a hybrid system built on three pillars:

1. **Structured Data (BigQuery)**  
   - Centralized athlete, race, and result tables  
   - Weekly PTO scoring and historical matchup data

2. **Retrieval-Augmented Generation (RAG)**  
   - Embedding search across athlete bios, race recaps, and results context  
   - Generated context becomes input to LLM prompting

3. **User-Validated Fine-Tuning Loop**  
   - All user questions, answers, and feedback (👍/👎) are logged  
   - High-confidence responses become training examples for a fine-tuned OpenAI model  
   - The system improves over time, becoming more accurate, domain-specific, and efficient

## Current Architecture
- **Input**: Natural language question from user  
- **LLM 1**: SQL generation (OpenAI GPT-4, prompted with schema/table context)  
- **Data**: Query runs against BigQuery triathlon warehouse  
- **LLM 2**: Answer generation (summarizes results into plain English)  
- **Feedback**: Users vote on response quality (stored for supervised training)

## Beta Participation
To improve accuracy, we launched a **Beta Program** that invites triathlon fans to:

- Ask real questions about races, athletes, and events  
- Vote on the quality of answers (👍/👎)  
- Earn rewards and leaderboard status based on participation

## Fine-Tuning Strategy
We collect the following for each user interaction:

- Question (user text)  
- Generated SQL  
- Final answer  
- Upvote/downvote  

Fine-tuned models will be trained on two formats:

- **Chat-style (Q+A)**: For answer generation  
- **Function-style (Q+SQL)**: For SQL generation  

By reducing reliance on large prompts and few-shot templates, we expect:

- 2× faster response time  
- 40–70% fewer hallucinations  
- More interpretable and accurate SQL for complex triathlon queries

## Future Vision
Once fine-tuned, Trilytx will serve:

- Fans looking for race previews, trivia, and matchup data  
- Coaches needing performance comparisons and taper modeling  
- Broadcasters/creators wanting instant stat lookups during race weekends

## Join the Trilytx Beta
- Want to join the leaderboard and shape the future of triathlon AI?
- [Click here to sign up for the beta](https://docs.google.com/forms/d/e/1FAIpQLScAA8LmWCd0WUupNBp9QstbAtqkJNXwqkokTlJMb731xovzRA/viewform?usp=dialog)

We're excited to have you on this journey with us. Together, we can revolutionize triathlon analytics!
""")

