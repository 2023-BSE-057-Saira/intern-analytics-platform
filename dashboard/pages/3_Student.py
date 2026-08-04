"""Student view - personal performance overview."""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from api_client import get_interns_df, get_weekly_performance, call_api
from style import inject_page_css, banner, welcome_card, trend_badge_text, badge_block, INDIGO
from charts import gauge_ring, trend_line

st.set_page_config(page_title="My Progress | Ezitech", page_icon="◆", layout="wide")
inject_page_css()

banner("My Progress", "Your personal performance overview", tag="STUDENT VIEW")

interns = get_interns_df()

intern_id = st.sidebar.selectbox(
    "Select profile (demo)",
    interns["intern_id"].tolist(),
    format_func=lambda x: f"#{x} - {interns[interns['intern_id']==x]['name'].values[0]}"
)
intern_row = interns[interns["intern_id"] == intern_id].iloc[0]

weekly = get_weekly_performance(int(intern_id))
progress_pct = min(100, (len(weekly) / 13) * 100) if len(weekly) > 0 else 0  # ~13 weeks = 90 days

welcome_card(
    name=intern_row["name"],
    subtitle=f"{intern_row['technology']} - Batch {intern_row['batch']}",
    progress_pct=progress_pct,
    status=intern_row["status"],
)

st.write("")

if st.button("Load My Insights"):
    with st.spinner("Loading your performance insights..."):
        success_result, err1 = call_api("/predict/success-probability", intern_id=int(intern_id))
        trend_result, err2 = call_api("/predict/performance-trend", intern_id=int(intern_id))
        growth_result, err3 = call_api("/predict/learning-growth", intern_id=int(intern_id))

    if err1 or err2 or err3:
        st.error(err1 or err2 or err3)
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.plotly_chart(gauge_ring(success_result["predicted_value"] * 100, "Success Probability"),
                             use_container_width=True)
        with col2:
            trend_label = trend_result["explanation"]["predicted_label"]
            trend_confidence = trend_result.get("confidence", 0) or 0
            st.plotly_chart(gauge_ring(trend_confidence * 100, f"Trend: {trend_label.title()}"),
                             use_container_width=True)
        with col3:
            learning_speed = growth_result["explanation"]["learning_speed"]
            # Normalize roughly to a 0-100 display scale for the gauge
            display_val = max(0, min(100, 50 + learning_speed * 100))
            st.plotly_chart(gauge_ring(display_val, "Learning Speed Index"), use_container_width=True)

        if len(weekly) > 0:
            st.write("")
            with st.container(border=True):
                st.markdown("##### Task Completion Over Time")
                st.plotly_chart(
                    trend_line(
                        weekly["week_number"].tolist(),
                        (weekly["task_completion_rate"].fillna(0) * 100).tolist(),
                        "Weekly Task Completion Rate (%)"
                    ),
                    use_container_width=True
                )

        st.write("")
        with st.container(border=True):
            st.markdown("##### Recommended for You")
            recs, err = call_api(f"/recommendations/{intern_id}/generate", method="POST")
            if err:
                st.error(err)
            else:
                for rec in recs:
                    st.success(rec["message"])
