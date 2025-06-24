# 🏊‍♂️🚴‍♂️🏃‍♂️ Trilytx — Natural Language Access to Triathlon Performance Data

**Trilytx** is a domain-specific, LLM-driven data exploration tool that enables natural language querying of triathlon performance data. Built with **Streamlit**, integrated with **BigQuery**, and powered by **OpenAI GPT models**, Trilytx bridges the gap between raw race results and high-level analytical insights — no SQL required.

---

## 🧠 Executive Summary

Designed for athletes, coaches, analysts, and fans, Trilytx enables intuitive Q&A over structured triathlon datasets. By transforming natural language into optimized SQL queries and returning human-readable summaries, it offers a user-friendly interface over a high-volume analytical backend.

Example queries:

- _“Who won Kona in 2023?”_  
- _“Show me Gustav Iden’s average run time in 70.3 races this season”_  
- _“Which athletes improved their bike segment time across consecutive races?”_

---

## 🚀 Key Features

- **Natural Language to SQL Translation**  
  Uses GPT-4 to convert user queries into BigQuery-compatible SQL, with modular prompt engineering.

- **BigQuery Analytics Engine**  
  Triathlon performance data lives in a scalable cloud warehouse, enabling subsecond query response on millions of rows.

- **Conversational State Management**  
  Tracks prior queries and answers for accurate follow-up handling and conversational context building.

- **Streamlit App Interface**  
  Interactive, multipage frontend with support for sidebars, filters, and charts.

- **Telemetry & Logging**  
  All interactions are logged for debugging, retraining, and insight generation.

- **Deployed on Heroku**  
  Auto-scaled deployment with CI/CD integration and API key security.

---

## 📊 Data Science & NLP Stack

| Component         | Tool/Service               |
|------------------|----------------------------|
| LLM Backend       | OpenAI GPT-4 via API       |
| Vector Prompting  | Modular SQL prompt templates |
| SQL Execution     | Google BigQuery            |
| Frontend UI       | Streamlit (multipage)      |
| Hosting           | Heroku (containerized)     |
| Logging & QA      | BigQuery (event logging)   |

---

## 🧪 Planned Enhancements

- **RAG (Retrieval-Augmented Generation)**  
  Enhance prompt grounding with metadata lookup and semantic vector search.

- **Athlete Embedding Memory**  
  Vectorized tracking of athlete performance trends across time and distance groups.

- **Enterprise-Grade Features**  
  - OAuth or SSO login  
  - Role-based access control  
  - BI export (Looker/Tableau-compatible output)

---

## 📂 Project Structure

```text
trilytx/
├── app.py                  # Main Streamlit app entrypoint
├── pages/                  # Multi-page views (charts, filters, etc.)
├── prompts/                # Modular GPT prompt templates
├── utils/                  # Query builders, summarizers, helpers
├── requirements.txt        # Python dependencies
├── setup.sh                # Heroku deployment script
└── README.md               # This file