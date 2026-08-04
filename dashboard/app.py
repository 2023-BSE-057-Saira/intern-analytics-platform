"""
Entry point / landing page.
Streamlit automatically builds sidebar navigation from every file in
dashboard/pages/ (Admin, Mentor, Student) - this file is just the
welcome screen shown before picking a role.
"""
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from api_client import get_interns_df
from style import inject_page_css, banner, kpi_row, INDIGO, SUCCESS

st.set_page_config(page_title="Ezitech Intern Analytics", page_icon="◆", layout="wide")
inject_page_css()

banner(
    "Ezitech Intern Analytics",
    "AI-Powered Internship Performance Prediction & Risk Analytics Platform",
    tag="AI-005"
)

st.write("")
interns = get_interns_df()

kpi_row([
    ("Total Interns", str(len(interns)), INDIGO),
    ("Active Now", str((interns["status"] == "active").sum()), SUCCESS),
    ("Prediction Models Live", "4", INDIGO),
    ("Required Predictions Covered", "8 / 8", SUCCESS),
])

st.write("")
st.markdown("### Choose a view")
st.caption("Select a role from the sidebar to explore the platform.")

col1, col2, col3 = st.columns(3)
with col1:
    with st.container(border=True):
        st.markdown("#### Admin")
        st.write("Batch-wide health, risk signals, and mentor capacity monitoring.")
with col2:
    with st.container(border=True):
        st.markdown("#### Mentor")
        st.write("Track your assigned interns' risk, trend, and get AI recommendations.")
with col3:
    with st.container(border=True):
        st.markdown("#### Student")
        st.write("See your own success probability, trend, and personalized guidance.")
