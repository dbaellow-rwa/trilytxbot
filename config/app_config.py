# config/app_config.py

# ──────────────────────────────────────────────────────────────────────────────
# Application Settings
# ──────────────────────────────────────────────────────────────────────────────
USE_LOCAL = 0 # Set to 0 for pushing to production, 1 for local development

# ──────────────────────────────────────────────────────────────────────────────
# BigQuery Logging Table Paths
# ──────────────────────────────────────────────────────────────────────────────
# These are the fully qualified table paths (project.dataset.table)
# Ensure these tables exist in your BigQuery project.
BQ_CHATBOT_ERROR_LOG = "trilytx.trilytx.chatbot_error_log"
BQ_CHATBOT_ZERO_RESULT_LOG = "trilytx.trilytx.chatbot_zero_result_log"
BQ_CHATBOT_QUESTION_LOG = "trilytx.trilytx.chatbot_question_log"
BQ_CHATBOT_VOTE_FEEDBACK = "trilytx.trilytx.chatbot_vote_feedback"
BQ_RACE_SEARCH_LOG = "trilytx.trilytx.race_search_log"
BQ_RACE_RECAP_LOG = "trilytx.trilytx.race_recap_generate_log"