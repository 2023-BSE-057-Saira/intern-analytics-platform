"""
Chart builders - kept separate from page logic so styling stays
consistent everywhere a chart appears.
"""
import plotly.express as px
import plotly.graph_objects as go

NAVY = "#14213D"
INDIGO = "#4361EE"
SUCCESS = "#10B981"
WARNING = "#F59E0B"
DANGER = "#EF4444"


def gauge_ring(value_pct: float, title: str, color: str = INDIGO):
    """Circular progress ring, similar to a completion/score indicator."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value_pct,
        number={"suffix": "%", "font": {"size": 28, "family": "JetBrains Mono", "color": NAVY}},
        title={"text": title, "font": {"size": 13, "family": "Inter", "color": "#6B7280"}},
        gauge={
            "axis": {"range": [0, 100], "visible": False},
            "bar": {"color": color, "thickness": 0.28},
            "bgcolor": "#EEF1F5",
            "borderwidth": 0,
        },
    ))
    fig.update_layout(height=180, margin=dict(t=40, b=10, l=20, r=20), paper_bgcolor="rgba(0,0,0,0)")
    return fig


def status_pie(status_counts_df):
    color_map = {"active": INDIGO, "completed": SUCCESS, "dropped": DANGER}
    fig = px.pie(status_counts_df, names="status", values="count", hole=0.55,
                 color="status", color_discrete_map=color_map)
    fig.update_layout(showlegend=True, height=300, margin=dict(t=10, b=10, l=10, r=10), font_family="Inter")
    fig.update_traces(textfont_size=13)
    return fig


def horizontal_bar(df, x_col, y_col, color=INDIGO):
    fig = px.bar(df, x=x_col, y=y_col, orientation="h", color_discrete_sequence=[color])
    fig.update_layout(height=300, margin=dict(t=10, b=10, l=10, r=10), font_family="Inter",
                       xaxis_title="", yaxis_title="")
    return fig


def trend_line(x_values, y_values, title: str, color: str = INDIGO):
    fig = go.Figure(go.Scatter(x=x_values, y=y_values, mode="lines+markers",
                                line=dict(color=color, width=3), marker=dict(size=6)))
    fig.update_layout(
        title={"text": title, "font": {"size": 14, "family": "Inter", "color": NAVY}},
        height=260, margin=dict(t=40, b=20, l=30, r=20),
        font_family="Inter", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#EEF1F5"),
    )
    return fig
