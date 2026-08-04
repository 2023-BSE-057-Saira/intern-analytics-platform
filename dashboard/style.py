"""
Design system + reusable UI components for the dashboard.

IMPORTANT FIX: the previous version injected custom HTML via
st.markdown(..., unsafe_allow_html=True) for banners/cards. On some
Streamlit versions/configurations that renders unreliably - raw HTML
tags can show up as literal text instead of being rendered. Every
custom-styled component below now uses st.components.v1.html instead,
which renders inside a real isolated HTML document (an iframe) - this
guarantees the HTML/CSS actually renders as intended, with zero risk
of showing raw markup as text.
"""
import streamlit.components.v1 as components
import streamlit as st

NAVY = "#14213D"
NAVY_LIGHT = "#1E3A6E"
INDIGO = "#4361EE"
INDIGO_LIGHT = "#EEF1FF"
SUCCESS = "#10B981"
WARNING = "#F59E0B"
DANGER = "#EF4444"
BG = "#F5F7FA"
CARD = "#FFFFFF"
TEXT = "#1F2937"
MUTED = "#6B7280"

FONT_IMPORT = (
    "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700"
    "&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap"
)

BASE_STYLE = f"""
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Inter', sans-serif; color: {TEXT}; background: transparent; }}
  .display {{ font-family: 'Space Grotesk', sans-serif; }}
  .mono {{ font-family: 'JetBrains Mono', monospace; }}
</style>
"""


def inject_page_css():
    """Applies fonts + background color to the actual Streamlit page shell."""
    st.markdown(f"""
    <link href="{FONT_IMPORT}" rel="stylesheet">
    <style>
        html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
        .stApp {{ background-color: {BG}; }}
        h1, h2, h3, h4, h5 {{ font-family: 'Space Grotesk', sans-serif !important; color: {NAVY} !important; }}
        [data-testid="stSidebar"] {{ background-color: {NAVY}; }}
        [data-testid="stSidebar"] * {{ color: #E8ECF7 !important; }}
        .stButton button {{
            background-color: {INDIGO}; color: white; border-radius: 8px;
            border: none; font-weight: 600; padding: 8px 18px;
        }}
        .stButton button:hover {{ background-color: #3651D4; color: white; }}
        div[data-testid="stExpander"] {{ background: {CARD}; border-radius: 10px; border: 1px solid #E9ECF2; }}
    </style>
    """, unsafe_allow_html=True)


def banner(title: str, subtitle: str, tag: str = "AI-005 - LIVE MODEL", height: int = 120):
    html = f"""
    {BASE_STYLE}
    <div style="background: linear-gradient(135deg, {NAVY} 0%, {NAVY_LIGHT} 100%);
                padding: 28px 36px; border-radius: 14px; display: flex;
                align-items: center; justify-content: space-between; height: {height-20}px;">
        <div>
            <div class="display" style="font-size: 26px; font-weight: 700; color: white;">{title}</div>
            <div style="font-size: 13px; color: #AFC0E8; margin-top: 6px;">{subtitle}</div>
        </div>
        <div class="mono" style="background: rgba(255,255,255,0.14); color: white;
                    padding: 7px 16px; border-radius: 20px; font-size: 11px; letter-spacing: 0.5px;">
            {tag}
        </div>
    </div>
    """
    components.html(html, height=height)


def kpi_row(items, height: int = 110):
    """items = list of (label, value, accent_color) tuples"""
    cards = ""
    for label, value, color in items:
        cards += f"""
        <div style="flex: 1; background: {CARD}; border-radius: 12px; padding: 18px 20px;
                    box-shadow: 0 1px 3px rgba(20,33,61,0.08); border: 1px solid #E9ECF2;
                    border-top: 3px solid {color};">
            <div style="font-size: 11px; color: {MUTED}; text-transform: uppercase;
                        letter-spacing: 0.6px; font-weight: 600;">{label}</div>
            <div class="mono" style="font-size: 26px; font-weight: 700; color: {NAVY}; margin-top: 6px;">{value}</div>
        </div>
        """
    html = f"""
    {BASE_STYLE}
    <div style="display: flex; gap: 16px;">{cards}</div>
    """
    components.html(html, height=height)


def badge(text: str, kind: str = "neutral") -> str:
    colors = {
        "low": ("#DCFCE7", "#15803D"),
        "moderate": ("#FEF3C7", "#B45309"),
        "high": ("#FEE2E2", "#B91C1C"),
        "neutral": (INDIGO_LIGHT, INDIGO),
    }
    bg, fg = colors.get(kind, colors["neutral"])
    return f'<span style="background:{bg}; color:{fg}; padding:4px 12px; border-radius:20px; font-size:12px; font-weight:600; font-family:Inter,sans-serif;">{text}</span>'


def badge_block(text: str, kind: str = "neutral", height: int = 36):
    html = f"{BASE_STYLE}<div>{badge(text, kind)}</div>"
    components.html(html, height=height)


def risk_badge_text(risk: float, threshold: float = 0.45):
    if risk >= threshold:
        return f"HIGH RISK - {risk:.0%}", "high"
    elif risk >= threshold * 0.6:
        return f"MODERATE - {risk:.0%}", "moderate"
    return f"LOW RISK - {risk:.0%}", "low"


def trend_badge_text(label: str):
    mapping = {
        "declining": ("DECLINING", "high"),
        "stable": ("STABLE", "neutral"),
        "improving": ("IMPROVING", "low"),
    }
    return mapping.get(label, (label.upper(), "neutral"))


def welcome_card(name: str, subtitle: str, progress_pct: float, status: str, height: int = 200):
    status_color = SUCCESS if status.lower() == "active" else (DANGER if status.lower() == "dropped" else MUTED)
    initials = "".join([p[0] for p in name.split()[:2]]).upper()
    html = f"""
    {BASE_STYLE}
    <div style="background: {CARD}; border-radius: 14px; padding: 26px 30px;
                border: 1px solid #E9ECF2; box-shadow: 0 1px 3px rgba(20,33,61,0.06);">
        <div style="display: flex; align-items: center; gap: 16px;">
            <div class="display" style="width: 52px; height: 52px; border-radius: 50%;
                        background: {INDIGO}; color: white; display: flex; align-items: center;
                        justify-content: center; font-size: 20px; font-weight: 700;">{initials}</div>
            <div>
                <div class="display" style="font-size: 20px; font-weight: 700; color: {NAVY};">Welcome back, {name}</div>
                <div style="font-size: 13px; color: {MUTED}; margin-top: 2px;">{subtitle}</div>
            </div>
            <div style="margin-left: auto;">
                <span style="background:{status_color}22; color:{status_color}; padding:5px 14px;
                            border-radius:20px; font-size:12px; font-weight:700;">&#9679; {status.title()}</span>
            </div>
        </div>
        <div style="margin-top: 22px;">
            <div style="display:flex; justify-content:space-between; font-size:12px; color:{MUTED}; margin-bottom:6px;">
                <span>Internship Progress</span><span class="mono">{progress_pct:.0f}%</span>
            </div>
            <div style="background:#EEF1F5; border-radius: 8px; height: 10px; overflow:hidden;">
                <div style="background: linear-gradient(90deg, {INDIGO}, #6C8CFF); width:{progress_pct}%; height:100%;"></div>
            </div>
        </div>
    </div>
    """
    components.html(html, height=height)
