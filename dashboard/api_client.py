"""
Shared data layer for the dashboard.
Every page imports from here instead of duplicating DB/API logic.
"""
import os
import requests
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://intern_admin:intern_pass123@localhost:5432/intern_analytics"
)

engine = create_engine(DATABASE_URL)


@st.cache_data(ttl=30)
def get_interns_df() -> pd.DataFrame:
    return pd.read_sql(text("SELECT * FROM interns ORDER BY intern_id"), engine)


@st.cache_data(ttl=30)
def get_mentors_df() -> pd.DataFrame:
    return pd.read_sql(text("SELECT * FROM mentors ORDER BY mentor_id"), engine)


@st.cache_data(ttl=30)
def get_weekly_performance(intern_id: int) -> pd.DataFrame:
    return pd.read_sql(
        text("SELECT * FROM weekly_performance WHERE intern_id = :iid ORDER BY week_number"),
        engine, params={"iid": intern_id}
    )


def call_api(endpoint: str, intern_id: int = None, method: str = "POST"):
    """Calls the live FastAPI backend. Returns (data, error_message)."""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        if method == "GET":
            resp = requests.get(url, timeout=15)
        else:
            resp = requests.post(url, json={"intern_id": intern_id}, timeout=15)
        resp.raise_for_status()
        return resp.json(), None
    except Exception as e:
        return None, str(e)
