"""Admin view - overall batch health, risk signals, mentor capacity."""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import streamlit as st
from api_client import get_interns_df, call_api
from style import inject_page_css, banner, kpi_row, badge_block, risk_badge_text, NAVY, INDIGO, SUCCESS, DANGER
from charts import status_pie, horizontal_bar

st.set_page_config(page_title="Admin | Ezitech Analytics", page_icon="◆", layout="wide")
inject_page_css()

banner("Admin Dashboard", "Batch health, risk signals, and mentor capacity - Ezitech AI-005")

interns = get_interns_df()

kpi_row([
    ("Total Interns", str(len(interns)), INDIGO),
    ("Active", str((interns["status"] == "active").sum()), INDIGO),
    ("Completed", str((interns["status"] == "completed").sum()), SUCCESS),
    ("Dropped", str((interns["status"] == "dropped").sum()), DANGER),
])

st.write("")
col_left, col_right = st.columns(2)

with col_left:
    with st.container(border=True):
        st.markdown("##### Status Breakdown")
        status_counts = interns["status"].value_counts().reset_index()
        status_counts.columns = ["status", "count"]
        st.plotly_chart(status_pie(status_counts), use_container_width=True)

with col_right:
    with st.container(border=True):
        st.markdown("##### Interns by Technology")
        tech_counts = interns["technology"].value_counts().reset_index()
        tech_counts.columns = ["technology", "count"]
        st.plotly_chart(horizontal_bar(tech_counts, "count", "technology"), use_container_width=True)

with st.container(border=True):
    st.markdown("##### Mentor Workload")
    workload_data, error = call_api("/predict/mentor-workload", method="GET")
    if error:
        st.error(f"Could not load mentor workload: {error}")
    else:
        workload_df = pd.DataFrame(workload_data)
        overloaded = workload_df[workload_df["overloaded"] == True]
        if len(overloaded) > 0:
            badge_block(f"{len(overloaded)} MENTOR(S) OVERLOADED", "high")
            st.dataframe(overloaded, use_container_width=True, hide_index=True)
        else:
            badge_block("ALL MENTORS WITHIN CAPACITY", "low")
        with st.expander("View all mentors"):
            st.dataframe(workload_df, use_container_width=True, hide_index=True)

with st.container(border=True):
    st.markdown("##### Check Any Intern's Dropout Risk")
    active_interns = interns[interns["status"] == "active"]
    if len(active_interns) > 0:
        selected_id = st.selectbox(
            "Select an active intern:",
            active_interns["intern_id"].tolist(),
            format_func=lambda x: f"#{x} - {active_interns[active_interns['intern_id']==x]['name'].values[0]}"
        )
        if st.button("Run Prediction"):
            with st.spinner("Running model..."):
                result, error = call_api("/predict/dropout-risk", intern_id=selected_id)
            if error:
                st.error(error)
            else:
                text_, kind = risk_badge_text(result["predicted_value"])
                badge_block(text_, kind)
                with st.expander("Why this score?"):
                    st.json(result["explanation"])
    else:
        st.info("No active interns to display.")
