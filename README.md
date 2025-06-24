# 🏊‍♂️🚴‍♂️🏃‍♂️ Trilytx — A Triathlon SQL Chatbot

Trilytx is a domain-specific chatbot designed to make triathlon performance data accessible and insightful using natural language. Built with **Streamlit** and powered by **OpenAI GPT models**, Trilytx converts user questions into **BigQuery SQL**, executes them, and delivers easy-to-understand summaries.

---

## 📌 Executive Summary

Trilytx bridges the gap between raw triathlon data and user-friendly insights. Whether you're a data-savvy coach or a curious fan, Trilytx helps you answer questions like:

- _"Who won Kona in 2023?"_  
- _"How did Lionel Sanders rank in bike segments this year?"_

All without needing to write a single line of SQL.

---

## 🚀 Key Features

- **Natural Language Interface**  
  Ask plain-English questions and get analytical answers instantly.

- **BigQuery Backend**  
  Scalable, real-time analytics over athlete-level triathlon race data.

- **GPT-Powered Querying**  
  Modular prompt templates and context-aware generation for accurate SQL.

- **Heroku Deployment**  
  Hosted as a multi-page Streamlit app with auto-scaling and CI/CD.

- **Robust UX**  
  - Follow-up question handling  
  - Sidebar filters  
  - Structured conversation memory  

- **Feedback & Logging**  
  All interactions logged in BigQuery for debugging, analysis, and iteration.

---

## 🧪 Future Enhancements

- **Retrieval-Augmented Generation (RAG)**  
  Grounding responses with metadata and semantic search for higher reliability.

- **Embedding Memory**  
  Track athlete performance trends and conversation flow.

- **Enterprise UX Features**  
  - Authentication and role-based access  
  - Export to business intelligence (BI) tools  

---

## 📂 Project Structure

```text
trilytx/
├── app.py                  # Main Streamlit app
├── pages/                  # Additional Streamlit pages
├── prompts/                # Prompt templates for GPT
├── utils/                  # Helper functions and wrappers
├── requirements.txt        # Python dependencies
├── setup.sh                # Heroku deployment script
└── README.md               # You're here!
```
🤝 Contributing
Contributions are welcome! Feel free to open issues, submit pull requests, or suggest features via Discussions.