from openai import OpenAI
import pandas as pd
import re
from typing import List, Dict

# Import prompts and table summaries from your data_prompts module
from utils.data_prompts import TABLE_SUMMARIES, get_table_prompts, GENERAL_SQL_GUIDELINES

def extract_table_names(text: str) -> List[str]:
    """
    Extracts potential BigQuery table names (e.g., 'fct_...') from a given text,
    and filters them against a predefined list of valid table summaries.

    Args:
        text (str): The text from which to extract table names.

    Returns:
        List[str]: A list of valid, extracted table names.
    """
    # Extract comma-separated table names (basic cleanup)
    candidates = re.findall(r"fct_[a-z_]+", text)
    return list(set(candidates) & set(TABLE_SUMMARIES.keys()))

def generate_sql_from_question_modular(question: str, openai_key: str) -> str:
    """
    Generates a BigQuery SQL query based on a natural language question
    using the OpenAI GPT model in a two-step process:
    1. Selects the most relevant table(s).
    2. Generates the SQL query using detailed table schema and guidelines.

    Args:
        question (str): The natural language question from the user.
        openai_key (str): Your OpenAI API key.

    Returns:
        str: The generated BigQuery SQL query.
    """
    client = OpenAI(api_key=openai_key)

    # Step 1: Ask GPT to choose relevant tables
    table_selection_prompt = f"""
    The user asked: "{question}"

    Below are summaries of available BigQuery tables:
    {chr(10).join([f"- {tbl}: {desc}" for tbl, desc in TABLE_SUMMARIES.items()])}

    Which table is most relevant to answer the question? Respond with 1 (ideally) or 2 (if required) table names (e.g., fct_race_results, fct_pto_scores_weekly).
    guidelines:
    - Only select tables that are directly relevant to the question.
    - If multiple tables are needed, separate them with a comma.
    - If the user is asking for specific times in a segment or segments or races, use fct_rae_results
    """

    selection_response = client.chat.completions.create(
        model="gpt-4", # Or "gpt-3.5-turbo" if you prefer
        messages=[{"role": "user", "content": table_selection_prompt}],
        temperature=0.0 # Keep temperature low for deterministic table selection
    )
    selected_raw = selection_response.choices[0].message.content
    selected_tables = extract_table_names(selected_raw)

    # If no valid tables are selected, provide a generic prompt or raise an error
    if not selected_tables:
        # This can happen if GPT doesn't identify a known table
        # For robustness, you might want a default table or a more specific error/retry.
        # For now, we'll try to proceed with a general context if no specific table is chosen.
        # Alternatively, you could raise an error: raise ValueError("No relevant tables could be identified.")
        selected_tables = list(TABLE_SUMMARIES.keys()) # Fallback to all tables if none are identified specifically
        # Or, just use a generic prompt without specific table context if selection fails.
        # The prompt below heavily relies on table_context, so a fallback to all tables
        # is safer than no context at all for the LLM to generate.

    # Step 2: Load full prompts for selected tables
    table_prompts = get_table_prompts()
    # Filter to ensure only prompts for truly selected tables are included
    selected_prompts = [table_prompts[t] for t in selected_tables if t in table_prompts]
    table_context = "\n\n".join(selected_prompts)

    # Step 3: Final prompt to generate SQL
    final_prompt = f"""
You are a SQL assistant for triathlon race data in BigQuery. Use standard SQL syntax compatible with Google BigQuery. Always use fully qualified table names (`project.dataset.table`) if not specified, and prefer `SAFE_CAST`, `DATE_DIFF`, `DATE_TRUNC`, and `QUALIFY` where appropriate.
{GENERAL_SQL_GUIDELINES()}
{table_context}

User question: {question}

Your Task:
Based on the user question below, generate only a valid BigQuery SQL query using the columns stated above.
Do not include explanations, comments, or markdown. Return SQL only.
    """

    sql_response = client.chat.completions.create(
        model="gpt-4", # Or "gpt-4o" for better performance and cost in some cases
        messages=[{"role": "user", "content": final_prompt}],
        temperature=0.0 # Keep temperature low for reliable SQL generation
    )

    sql = sql_response.choices[0].message.content.strip()

    # Clean up common LLM formatting (e.g., markdown code blocks)
    if "```sql" in sql:
        sql = sql.split("```sql")[-1].split("```")[0].strip()
    return sql

def row_to_sentence(row: pd.Series) -> str:
    """
    Converts a Pandas Series (representing a DataFrame row) into a natural language sentence.

    Args:
        row (pd.Series): A single row from a DataFrame.

    Returns:
        str: A sentence summarizing the row's content.
    """
    return ". ".join([f"{col}: {row[col]}" for col in row.index]) + "."

def summarize_results(df: pd.DataFrame, openai_key: str, question: str,
                      conversational_history: list = None, generated_sql: str = "") -> str:

    """
    Summarizes the given DataFrame results in a plain analytical tone using the OpenAI GPT model.
    Bolds specific keywords like athlete names, finish times, countries, and finishing places.

    Args:
        df (pd.DataFrame): The DataFrame containing the query results.
        openai_key (str): Your OpenAI API key.
        question (str): The original natural language question from the user.

    Returns:
        str: A 1-3 sentence summary of the results.
    """
    client = OpenAI(api_key=openai_key)

    rows_as_sentences = "\n".join(row_to_sentence(row) for _, row in df.iterrows())
    history_context = ""
    if conversational_history:
        for q_prev, a_prev, df_result, sql_prev in conversational_history:
            history_context += f"Previous user query: '{q_prev}'\n"
            history_context += f"Previous assistant answer: '{a_prev}'\n"
            history_context += "---\n"

    prompt = f"""
    You are an AI assistant specializing in triathlon race summaries.

{history_context if history_context else ""}
Current user question: "{question}"
Here is the SQL query that was used to retrieve the data:
```sql
{generated_sql}
```
Here are the results:
{rows_as_sentences}

🧠 IMPORTANT: Context-Aware Answering

If the prior conversation included filters (e.g., specific athlete names, race years, gender categories, distances, or organizers), you must respect those filters when answering this follow-up question — even if the user doesn’t repeat them.

For example:

If the user previously asked about results from "last year", assume the same time frame unless they ask about a different one.

If the prior answer referred to MARTEN VAN RIEL, assume "he" refers to that athlete.

Do not invent filters. Only carry them forward if they were clearly used in previous questions or answers.

The goal is to maintain contextual consistency across turns without adding or changing the user's intent.

📝 Please return your response using this format:

**ANSWER:** Write a 1–3 sentence summary in a plain analytical tone. If the answer is 1 word or a number, 1 sentence is fine.

**LOGIC USED:** Explain how the SQL answered the question using 1-2 sentences like:  
"In order to answer this question, I first did X, Y, and Z..." — describing what filters, joins, or columns were used. If specific dates are used, include the specifics. 

**Bold** the following when they appear:
- Athlete names  
- Finish times (e.g., '1:25:30' or similar)  
- Country names  
- Finishing places (e.g., athlete_finishing_place = 1st, 2nd, 3rd)  
Use Markdown formatting (e.g., `**name**`) in your summary.

"""
    response = client.chat.completions.create(
        model="gpt-4o", # Using gpt-4o for potentially better summarization
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2, # A bit of creativity for summarization
    )
    return response.choices[0].message.content.strip()