"""
AI-Powered Internship Analytics Dashboard
============================================
Home/landing page, plus three dashboard views per the case study's
AI Dashboard requirement:
  - Admin:   overall health, high-risk students, top performers,
             department analytics, batch comparison
  - Mentor:  their weak/strong students, pending reviews, weekly AI
             suggestions, risk alerts, workload
  - Student: their own performance score, weekly improvement plan,
             skill progress, AI learning suggestions, predicted status

NOTE: reads from the `predictions` table (fast, no live model calls
while browsing). Run `python -m app.ml.batch_predict` first to
populate real prediction data for all active interns.

Usage:
    streamlit run app/dashboard_app.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import streamlit as st

from app.database import engine
from app.services.recommendation_engine import generate_recommendations
from app.ml.predict import calculate_mentor_workload
from app.database import SessionLocal

st.set_page_config(page_title="Ezitech | Internship Analytics", layout="wide", page_icon="🎓")

# ---------------------------------------------------------------------------
# Theme tokens
# ---------------------------------------------------------------------------
EZITECH_NAVY = "#0B1B3F"
EZITECH_NAVY_LIGHT = "#16244A"
EZITECH_BLUE = "#2F6FED"
EZITECH_PURPLE = "#7C5CFC"
EZITECH_BG = "#F4F6FC"
EZITECH_GREEN = "#16A34A"
EZITECH_AMBER = "#D97706"
EZITECH_RED = "#DC2626"
EZITECH_INK = "#1D2540"
EZITECH_SUBTLE = "#6B7280"

NAV_ITEMS = [
    ("Home", "🏠"),
    ("Admin", "📊"),
    ("Mentor", "🧑‍🏫"),
    ("Student", "🎓"),
]

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@600;700&family=Inter:wght@400;500;600&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
    }}

    .stApp {{
        background-color: {EZITECH_BG};
    }}

    h1, h2, h3 {{
        font-family: 'Poppins', sans-serif;
        color: {EZITECH_INK};
    }}

    /* ---------- Sidebar ---------- */
    section[data-testid="stSidebar"] {{
        background-color: {EZITECH_NAVY};
    }}
    section[data-testid="stSidebar"] * {{
        color: #FFFFFF !important;
        font-family: 'Inter', sans-serif;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label {{
        background-color: {EZITECH_NAVY_LIGHT};
        border-radius: 8px;
        padding: 10px 12px;
        margin-bottom: 6px;
        border: 1px solid transparent;
        transition: border-color 0.15s ease;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{
        border-color: {EZITECH_BLUE};
    }}

    /* ---------- Hero banner ---------- */
    .ezitech-banner {{
        background: linear-gradient(120deg, {EZITECH_BLUE} 0%, {EZITECH_PURPLE} 100%);
        padding: 28px 32px;
        border-radius: 16px;
        color: white;
        margin-bottom: 26px;
        box-shadow: 0 8px 24px rgba(47, 111, 237, 0.18);
    }}
    .ezitech-banner .eyebrow {{
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 12px;
        font-weight: 600;
        color: #DCE4FF;
        margin: 0 0 6px 0;
    }}
    .ezitech-banner h1 {{
        color: white !important;
        margin: 0;
        font-size: 26px;
    }}
    .ezitech-banner p {{
        color: #E8ECFF;
        margin: 6px 0 0 0;
        font-size: 15px;
    }}

    /* ---------- Metric cards ---------- */
    div[data-testid="stMetric"] {{
        background-color: #FFFFFF;
        border: 1px solid #E5E9F5;
        border-left: 4px solid {EZITECH_BLUE};
        border-radius: 12px;
        padding: 14px 16px;
        box-shadow: 0 1px 3px rgba(11,27,63,0.06);
    }}
    div[data-testid="stMetricLabel"] {{
        color: {EZITECH_SUBTLE} !important;
        font-weight: 500;
    }}

    /* ---------- Section headers ---------- */
    .section-title {{
        display: flex;
        align-items: center;
        gap: 8px;
        font-family: 'Poppins', sans-serif;
        font-weight: 600;
        font-size: 18px;
        color: {EZITECH_INK};
        margin: 6px 0 10px 0;
    }}
    .section-title .dot {{
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: {EZITECH_PURPLE};
        display: inline-block;
    }}

    /* ---------- Badges (pills) ---------- */
    .badge {{
        display: inline-block;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 600;
    }}
    .badge-green {{ background: #DCFCE7; color: {EZITECH_GREEN}; }}
    .badge-amber {{ background: #FEF3C7; color: {EZITECH_AMBER}; }}
    .badge-red   {{ background: #FEE2E2; color: {EZITECH_RED}; }}
    .badge-blue  {{ background: #DBEAFE; color: {EZITECH_BLUE}; }}
    .badge-gray  {{ background: #F1F3F9; color: {EZITECH_SUBTLE}; }}

    /* ---------- Buttons ---------- */
    .stButton > button {{
        background-color: {EZITECH_BLUE};
        color: white;
        border-radius: 8px;
        border: none;
        font-weight: 500;
        padding: 8px 18px;
    }}
    .stButton > button:hover {{
        background-color: {EZITECH_PURPLE};
        color: white;
    }}

    /* ---------- Landing page ---------- */
    .hero-wrap {{
        background: linear-gradient(120deg, {EZITECH_NAVY} 0%, #1B2E63 55%, {EZITECH_PURPLE} 130%);
        border-radius: 20px;
        padding: 56px 48px;
        color: white;
        margin-bottom: 32px;
        box-shadow: 0 12px 32px rgba(11,27,63,0.25);
    }}
    .hero-wrap .eyebrow {{
        text-transform: uppercase;
        letter-spacing: 0.12em;
        font-size: 12px;
        font-weight: 600;
        color: #A9BBFF;
        margin-bottom: 12px;
    }}
    .hero-wrap h1 {{
        color: white !important;
        font-size: 40px;
        line-height: 1.15;
        margin: 0 0 14px 0;
    }}
    .hero-wrap p {{
        color: #DDE3FA;
        font-size: 16px;
        max-width: 620px;
        margin: 0 0 4px 0;
    }}

    .feature-card {{
        background: white;
        border: 1px solid #E5E9F5;
        border-radius: 14px;
        padding: 20px;
        height: 100%;
        box-shadow: 0 1px 3px rgba(11,27,63,0.06);
    }}
    .feature-card .icon {{
        width: 38px;
        height: 38px;
        border-radius: 10px;
        background: #EEF2FF;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        margin-bottom: 12px;
    }}
    .feature-card h4 {{
        font-family: 'Poppins', sans-serif;
        font-size: 15px;
        color: {EZITECH_INK};
        margin: 0 0 6px 0;
    }}
    .feature-card p {{
        color: {EZITECH_SUBTLE};
        font-size: 13.5px;
        margin: 0;
    }}

    .about-card {{
        background: white;
        border: 1px solid #E5E9F5;
        border-radius: 14px;
        padding: 22px 24px;
        height: 100%;
    }}
    .about-card h4 {{
        font-family: 'Poppins', sans-serif;
        font-size: 15px;
        color: {EZITECH_INK};
        margin: 0 0 8px 0;
    }}
    .about-card p {{
        color: {EZITECH_SUBTLE};
        font-size: 13.5px;
        line-height: 1.55;
        margin: 0;
    }}
</style>
""", unsafe_allow_html=True)


def page_header(eyebrow: str, title: str, subtitle: str):
    st.markdown(f"""
    <div class="ezitech-banner">
        <p class="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p>{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


def section_title(icon: str, text: str):
    st.markdown(f"""
    <div class="section-title"><span class="dot"></span>{icon} {text}</div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Presentation-only helpers (formatting for display; never used for the
# underlying filtering/aggregation logic, which is untouched below)
# ---------------------------------------------------------------------------
STATUS_DISPLAY = {"active": "🟢 Active", "completed": "🔵 Completed", "dropped": "🔴 Dropped"}
TREND_DISPLAY = {"improving": "📈 Improving", "stable": "➖ Stable", "declining": "📉 Declining"}


def with_display_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Returns a copy with friendlier text in status/trend columns, purely
    for rendering in st.dataframe. Does not affect any filtering upstream."""
    out = frame.copy()
    if "status" in out.columns:
        out["status"] = out["status"].map(STATUS_DISPLAY).fillna(out["status"])
    if "performance_trend" in out.columns:
        out["performance_trend"] = out["performance_trend"].map(TREND_DISPLAY).fillna(out["performance_trend"])
    return out


def risk_progress_config(label: str = "Dropout Risk"):
    return st.column_config.ProgressColumn(label, format="%.0f%%", min_value=0, max_value=1)


def prob_progress_config(label: str = "Success Probability"):
    return st.column_config.ProgressColumn(label, format="%.0f%%", min_value=0, max_value=1)


# ---------------------------------------------------------------------------
# Data loaders (unchanged — same queries, same columns, same logic)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=60)
def load_interns() -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM interns", engine)


@st.cache_data(ttl=60)
def load_mentors() -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM mentors", engine)


@st.cache_data(ttl=60)
def load_latest_predictions() -> pd.DataFrame:
    # FIX: this project stores the performance-trend class label under
    # the key 'predicted_label' in explanation_json, not 'label'.
    query = """
        SELECT DISTINCT ON (intern_id, prediction_type)
            intern_id, prediction_type, predicted_value,
            explanation_json ->> 'predicted_label' AS label,
            confidence, created_at
        FROM predictions
        ORDER BY intern_id, prediction_type, created_at DESC
    """
    return pd.read_sql(query, engine)


@st.cache_data(ttl=60)
def load_recommendations() -> pd.DataFrame:
    return pd.read_sql(
        "SELECT * FROM recommendations ORDER BY intern_id, created_at DESC", engine
    )


@st.cache_data(ttl=60)
def load_predictions_wide() -> pd.DataFrame:
    """Pivots predictions from long format to wide (one row per intern,
    one column per prediction type)."""
    preds = load_latest_predictions()
    if preds.empty:
        st.warning(
            "No predictions found yet. Run `python -m app.ml.batch_predict` "
            "to generate predictions for all active interns first."
        )
        return load_interns()

    preds["display_value"] = preds.apply(
        lambda r: r["label"] if r["prediction_type"] == "performance_trend" and pd.notna(r["label"])
        else r["predicted_value"],
        axis=1,
    )
    wide = preds.pivot(index="intern_id", columns="prediction_type", values="display_value").reset_index()

    numeric_cols = [
        "dropout_risk", "success_probability", "completion_probability",
        "project_success_probability", "learning_speed", "skill_growth",
    ]
    for col in numeric_cols:
        if col in wide.columns:
            wide[col] = pd.to_numeric(wide[col], errors="coerce")

    interns = load_interns()
    return interns.merge(wide, on="intern_id", how="left")


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------
def render_landing_view():
    st.markdown("""
    <div class="hero-wrap">
        <p class="eyebrow">Ezitech &nbsp;•&nbsp; AI-005 Case Study</p>
        <h1>Internship Performance Prediction<br>&amp; Risk Analytics Platform</h1>
        <p>One place for admins, mentors, and interns to see how every internship is
        really going — attendance, task completion, GitHub activity, and mentor
        feedback distilled into dropout risk, success probability, and personalized
        weekly guidance.</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, _ = st.columns([1, 1, 3])
    with col1:
        if st.button("Get Started →", use_container_width=True):
            st.session_state["view"] = "Admin"
            st.rerun()
    with col2:
        if st.button("View Mentor Panel", use_container_width=True):
            st.session_state["view"] = "Mentor"
            st.rerun()

    st.write("")
    section_title("✨", "What the platform does")
    f1, f2, f3 = st.columns(3)
    with f1:
        st.markdown("""
        <div class="feature-card">
            <div class="icon">📡</div>
            <h4>Real-Time Tracking</h4>
            <p>Attendance, task completion, and GitHub activity rolled up into a
            live view of every intern's progress.</p>
        </div>
        """, unsafe_allow_html=True)
    with f2:
        st.markdown("""
        <div class="feature-card">
            <div class="icon">🧠</div>
            <h4>Smart Analytics</h4>
            <p>ML-driven dropout risk, success probability, and performance trend
            predictions with plain-language explanations.</p>
        </div>
        """, unsafe_allow_html=True)
    with f3:
        st.markdown("""
        <div class="feature-card">
            <div class="icon">🔐</div>
            <h4>Role-Based Dashboards</h4>
            <p>Separate, purpose-built views for Admins, Mentors, and Interns —
            each showing exactly what they need to act on.</p>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    a1, a2 = st.columns(2)
    with a1:
        st.markdown("""
        <div class="about-card">
            <h4>🎯 Our Mission</h4>
            <p>Catch struggling interns early — before a dropout happens — by turning
            raw activity data into timely, explainable signals mentors can act on.</p>
        </div>
        """, unsafe_allow_html=True)
    with a2:
        st.markdown("""
        <div class="about-card">
            <h4>📈 Our Vision</h4>
            <p>Give every intern a personalized weekly plan grounded in their own
            data, and give admins a real-time pulse on cohort health across
            technologies and batches.</p>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    st.caption("Built for Ezitech Case Study AI-005 · Internship Performance Prediction & Risk Analytics Platform")


def render_admin_view():
    page_header("Admin", "Overall Internship Health",
                "Cohort-wide risk, top performers, and batch/technology comparisons.")
    df = load_predictions_wide()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Interns", len(df))
    col2.metric("Active", (df["status"] == "active").sum())
    col3.metric("Completed", (df["status"] == "completed").sum())
    col4.metric("Dropped", (df["status"] == "dropped").sum())

    if "dropout_risk" in df.columns:
        col1, col2 = st.columns(2)
        col1.metric("Avg Dropout Risk", f"{df['dropout_risk'].mean():.1%}" if df['dropout_risk'].notna().any() else "N/A")
        col2.metric("Avg Success Probability", f"{df['success_probability'].mean():.1%}" if df['success_probability'].notna().any() else "N/A")

        st.divider()

        section_title("⚠️", "High-Risk Students (Dropout Risk > 50%)")
        high_risk = df[df["dropout_risk"] > 0.5].sort_values("dropout_risk", ascending=False)
        display_cols = [c for c in ["intern_id", "name", "technology", "batch", "status", "dropout_risk", "performance_trend"] if c in high_risk.columns]
        st.dataframe(
            with_display_columns(high_risk[display_cols]),
            use_container_width=True, hide_index=True,
            column_config={"dropout_risk": risk_progress_config()} if "dropout_risk" in display_cols else None,
        )

        section_title("🏆", "Top Performers (Success Probability > 90%)")
        top_performers = df[df["success_probability"] > 0.9].sort_values("success_probability", ascending=False)
        display_cols = [c for c in ["intern_id", "name", "technology", "batch", "success_probability", "performance_trend"] if c in top_performers.columns]
        st.dataframe(
            with_display_columns(top_performers[display_cols]),
            use_container_width=True, hide_index=True,
            column_config={"success_probability": prob_progress_config()} if "success_probability" in display_cols else None,
        )

        st.divider()

        section_title("🏢", "Department Analytics")
        tech_stats = df.groupby("technology").agg(
            interns=("intern_id", "count"),
            avg_dropout_risk=("dropout_risk", "mean"),
            avg_success_probability=("success_probability", "mean"),
        ).reset_index()
        col1, col2 = st.columns(2)
        col1.dataframe(
            tech_stats, use_container_width=True, hide_index=True,
            column_config={
                "avg_dropout_risk": risk_progress_config("Avg Dropout Risk"),
                "avg_success_probability": prob_progress_config("Avg Success Prob."),
            },
        )
        col2.bar_chart(tech_stats.set_index("technology")["avg_dropout_risk"])

        section_title("📦", "Batch Comparison")
        batch_stats = df.groupby("batch").agg(
            interns=("intern_id", "count"),
            avg_dropout_risk=("dropout_risk", "mean"),
            avg_success_probability=("success_probability", "mean"),
            dropped=("status", lambda s: (s == "dropped").sum()),
        ).reset_index()
        st.dataframe(
            batch_stats, use_container_width=True, hide_index=True,
            column_config={
                "avg_dropout_risk": risk_progress_config("Avg Dropout Risk"),
                "avg_success_probability": prob_progress_config("Avg Success Prob."),
            },
        )


def render_mentor_view():
    page_header("Mentor", "Mentor Dashboard",
                "Your interns, your workload, and this week's AI suggestions.")
    mentors = load_mentors()
    df = load_predictions_wide()

    mentor_name = st.selectbox("Select Mentor", mentors["name"].sort_values())
    mentor_row = mentors[mentors["name"] == mentor_name].iloc[0]
    mentor_id = mentor_row["mentor_id"]

    my_interns = df[df["mentor_id"] == mentor_id]

    db = SessionLocal()
    workload = pd.DataFrame(calculate_mentor_workload(db))
    db.close()
    my_workload = workload[workload["mentor_id"] == mentor_id]
    if not my_workload.empty:
        w = my_workload.iloc[0]
        col1, col2, col3 = st.columns(3)
        col1.metric("Active Interns", int(w["active_interns"]))
        col2.metric("Capacity", int(w["max_capacity"]))
        col3.metric("Utilization", f"{w['utilization']:.0%}", delta="Overloaded" if w["overloaded"] else "OK")

    st.divider()

    if "dropout_risk" in my_interns.columns:
        section_title("😟", "Weak Students (Dropout Risk > 50% or Declining Trend)")
        weak = my_interns[
            (my_interns["dropout_risk"] > 0.5) | (my_interns["performance_trend"] == "declining")
        ].sort_values("dropout_risk", ascending=False)
        display_cols = [c for c in ["intern_id", "name", "technology", "dropout_risk", "performance_trend"] if c in weak.columns]
        st.dataframe(
            with_display_columns(weak[display_cols]),
            use_container_width=True, hide_index=True,
            column_config={"dropout_risk": risk_progress_config()} if "dropout_risk" in display_cols else None,
        )

        section_title("💪", "Strong Students (Success Probability > 85%)")
        strong = my_interns[my_interns["success_probability"] > 0.85].sort_values(
            "success_probability", ascending=False
        )
        display_cols = [c for c in ["intern_id", "name", "technology", "success_probability", "performance_trend"] if c in strong.columns]
        st.dataframe(
            with_display_columns(strong[display_cols]),
            use_container_width=True, hide_index=True,
            column_config={"success_probability": prob_progress_config()} if "success_probability" in display_cols else None,
        )

        st.divider()

        section_title("💡", "Weekly AI Suggestions For Your Interns")
        recs = load_recommendations()
        my_recs = recs[recs["intern_id"].isin(my_interns["intern_id"])]
        my_recs = my_recs.merge(my_interns[["intern_id", "name"]], on="intern_id", how="left")
        if not my_recs.empty:
            st.dataframe(my_recs[["name", "recommendation_type", "message"]], use_container_width=True, hide_index=True)
        else:
            st.info("No recommendations generated yet for your interns.")


def render_student_view():
    page_header("Student", "My Internship Dashboard",
                "Your predicted status, skill progress, and this week's plan.")
    df = load_predictions_wide()

    intern_name = st.selectbox("Select Your Name", df["name"].sort_values())
    intern_row = df[df["name"] == intern_name].iloc[0]
    intern_id = int(intern_row["intern_id"])

    if "dropout_risk" not in df.columns or pd.isna(intern_row.get("dropout_risk")):
        st.warning("No predictions available for this intern yet. Run `python -m app.ml.batch_predict` first.")
        return

    section_title("🔮", "Predicted Internship Status")
    col1, col2, col3 = st.columns(3)
    col1.metric("Dropout Risk", f"{intern_row['dropout_risk']:.1%}")
    col2.metric("Success Probability", f"{intern_row['success_probability']:.1%}")
    col3.metric("Performance Trend", str(intern_row["performance_trend"]).title())

    st.divider()

    performance_score = round(
        (intern_row["success_probability"] * 0.6 + (1 - intern_row["dropout_risk"]) * 0.4) * 100, 1
    )
    st.metric("Overall Performance Score", f"{performance_score}/100")

    section_title("🌱", "Skill Progress")
    col1, col2 = st.columns(2)
    col1.metric("Skill Growth", f"{intern_row['skill_growth']:.3f}",
                delta="Improving" if intern_row["skill_growth"] > 0 else "Needs focus")
    col2.metric("Learning Speed", f"{intern_row['learning_speed']:.3f}")

    st.divider()

    section_title("📝", "Weekly Improvement Plan & AI Suggestions")
    db = SessionLocal()
    recs = generate_recommendations(intern_id=intern_id, db=db)
    db.close()
    for rec in recs:
        st.info(f"**{rec['recommendation_type'].replace('_', ' ').title()}**: {rec['message']}")


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------
st.session_state.setdefault("view", "Home")

st.sidebar.markdown("## 🎓 EZITECH")
st.sidebar.caption("Internship Analytics Platform")
st.sidebar.markdown("---")
view = st.sidebar.radio(
    "Select View",
    [label for label, _icon in NAV_ITEMS],
    format_func=lambda label: f"{dict(NAV_ITEMS)[label]}  {label}",
    key="view",
)

if view == "Home":
    render_landing_view()
elif view == "Admin":
    render_admin_view()
elif view == "Mentor":
    render_mentor_view()
else:
    render_student_view()