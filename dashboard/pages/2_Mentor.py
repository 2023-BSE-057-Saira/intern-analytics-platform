"""Mentor view - a mentor's own interns, risk/trend, recommendations."""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from api_client import get_interns_df, get_mentors_df, call_api
from style import inject_page_css, banner, kpi_row, badge_block, risk_badge_text, trend_badge_text, INDIGO

st.set_page_config(page_title="Mentor | Ezitech Analytics", page_icon="◆", layout="wide")
inject_page_css()

banner("Mentor Dashboard", "Your interns, at a glance")

mentors = get_mentors_df()
interns = get_interns_df()

mentor_id = st.sidebar.selectbox(
    "Select mentor",
    mentors["mentor_id"].tolist(),
    format_func=lambda x: mentors[mentors["mentor_id"] == x]["name"].values[0]
)
mentor_row = mentors[mentors["mentor_id"] == mentor_id].iloc[0]

my_interns = interns[interns["mentor_id"] == mentor_id]
active_my_interns = my_interns[my_interns["status"] == "active"]

over_capacity = len(active_my_interns) > mentor_row["max_capacity"]
capacity_color = "#EF4444" if over_capacity else INDIGO

kpi_row([
    ("Mentor", mentor_row["name"], INDIGO),
    ("Active Interns", str(len(active_my_interns)), INDIGO),
    ("Capacity", str(mentor_row["max_capacity"]), capacity_color),
])

if over_capacity:
    st.write("")
    badge_block("OVER CAPACITY", "high")

st.write("")
st.markdown("##### Your Interns")

if len(active_my_interns) == 0:
    st.info("No active interns currently assigned.")
else:
    for _, intern in active_my_interns.iterrows():
        with st.expander(f"#{intern['intern_id']} - {intern['name']} - {intern['technology']}"):
            col1, col2 = st.columns(2)

            with col1:
                if st.button("Check Risk & Trend", key=f"check_{intern['intern_id']}"):
                    with st.spinner("Running predictions..."):
                        risk_result, err1 = call_api("/predict/dropout-risk", intern_id=int(intern["intern_id"]))
                        trend_result, err2 = call_api("/predict/performance-trend", intern_id=int(intern["intern_id"]))
                    if err1 or err2:
                        st.error(err1 or err2)
                    else:
                        risk = risk_result["predicted_value"]
                        trend_label = trend_result["explanation"].get("predicted_label", "unknown")
                        risk_text, risk_kind = risk_badge_text(risk)
                        trend_text, trend_kind = trend_badge_text(trend_label)
                        badge_block(risk_text, risk_kind, height=32)
                        badge_block(trend_text, trend_kind, height=32)

            with col2:
                if st.button("Get Recommendations", key=f"rec_{intern['intern_id']}"):
                    with st.spinner("Generating recommendations..."):
                        recs, err = call_api(f"/recommendations/{int(intern['intern_id'])}/generate", method="POST")
                    if err:
                        st.error(err)
                    else:
                        for rec in recs:
                            st.info(f"**{rec['recommendation_type'].replace('_', ' ').title()}** - {rec['message']}")
