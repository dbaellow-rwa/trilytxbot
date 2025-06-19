import json
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
import os
import streamlit as st # Only needed for st.error if you want to display errors at this low level, otherwise remove.

# Assuming sources_of_truth is a package and accessible.
# If not, you might need a sys.path.append in your main entry point (e.g., Home.py)
# or configure your project's PYTHONPATH.
try:
    from sources_of_truth.secret_manager_utils import get_secret
except ImportError:
    # This block is for robustness in case running directly or testing.
    # In a structured Streamlit app, the main file's sys.path manipulation should handle it.
    def get_secret(secret_id: str, project_id: str):
        # Placeholder for local testing if secret_manager_utils isn't set up
        # In a real scenario, this would fetch from a secure source.
        # For local testing, you might read from a local .env or dummy file.
        if secret_id == "service-account-trilytxbot-key":
            # This is a dummy example. Replace with your actual local key path/content if needed.
            # It's better to manage this via environment variables or a secure local setup.
            try:
                with open("path/to/your/local_service_account_key.json", "r") as f:
                    return f.read()
            except FileNotFoundError:
                st.error("Local service account key file not found. Ensure 'path/to/your/local_service_account_key.json' is correct or use environment variables.")
                return None
        elif secret_id == "openai_rwa_1":
            return os.environ.get("OPENAI_API_KEY_LOCAL_DEV") # Or another local env var name
        return None

def load_credentials(use_local: int):
    """
    Loads Google Cloud and OpenAI credentials based on the USE_LOCAL flag.

    Args:
        use_local (int): 1 for local development (using Secret Manager),
                         0 for production (using environment variables).

    Returns:
        tuple: (credentials, project_id, openai_key)
    """
    credentials = None
    project_id = None
    openai_key = None

    if use_local:
        json_key_str = get_secret(secret_id="service-account-trilytxbot-key", project_id="trilytx")
        if not json_key_str:
            raise ValueError("Service account key not found via secret manager.")
        json_key = json.loads(json_key_str)
        credentials = service_account.Credentials.from_service_account_info(json_key)
        project_id = json_key["project_id"]
        openai_key = get_secret("openai_rwa_1", project_id="906828770740")
        if not openai_key:
            raise ValueError("OpenAI API key not found via secret manager.")
    else:
        json_key_str = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_TRILYTXBOT")
        if not json_key_str:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS_TRILYTXBOT environment variable not set for production.")
        json_key = json.loads(json_key_str)
        credentials = service_account.Credentials.from_service_account_info(json_key)
        project_id = json_key["project_id"]
        openai_key = os.environ.get("OPENAI_API_KEY")
        if not openai_key:
            raise ValueError("OPENAI_API_KEY environment variable not set for production.")

    return credentials, project_id, openai_key

def extract_table_schema(client: bigquery.Client, dataset_id: str, table_id: str) -> dict:
    """
    Extracts the schema (description and field details) for a given BigQuery table.

    Args:
        client (bigquery.Client): An initialized BigQuery client.
        dataset_id (str): The ID of the BigQuery dataset.
        table_id (str): The ID of the BigQuery table.

    Returns:
        dict: A dictionary containing the table's description and a dictionary of
              field names to their descriptions/types.
    """
    try:
        table = client.get_table(f"{dataset_id}.{table_id}")
        return {
            "description": table.description or "",
            "fields": {field.name: field.description or str(field.field_type) for field in table.schema}
        }
    except Exception as e:
        st.error(f"Error extracting schema for {dataset_id}.{table_id}: {e}")
        return {"description": "", "fields": {}} # Return empty structure on error

def run_bigquery(query: str, client: bigquery.Client) -> pd.DataFrame:
    """
    Executes a BigQuery SQL query and returns the results as a Pandas DataFrame.

    Args:
        query (str): The SQL query string to execute.
        client (bigquery.Client): An initialized BigQuery client.

    Returns:
        pd.DataFrame: A DataFrame containing the query results.
    """
    try:
        return client.query(query).to_dataframe()
    except Exception as e:
        # In a production app, you might re-raise after logging or
        # handle more gracefully, but for now, Streamlit's error logging
        # will catch it higher up.
        raise e # Re-raise the exception to be caught in Home.py's try-except block