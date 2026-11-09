"""All Plotly charts in one place, so the dashboard code stays short."""
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

COLORS = {"Positive": "#10b981", "Neutral": "#94a3b8", "Negative": "#ef4444"}
STATUS_COLORS = {"New concern": "#ef4444", "Rising": "#f97316", "Stable": "#94a3b8", "Improving": "#10b981"}
PRIMARY = "#4f46e5"
SOFT = "#c7d2fe"
ORDER = ["Positive", "Neutral", "Negative"]


def _style(fig, title=None, height=340, legend=True):
    fig.update_layout(
        title=dict(text=title, font=dict(size=16)) if title else None,
        height=height, margin=dict(l=10, r=10, t=55 if title else 15, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Segoe UI, Inter, sans-serif", size=13, color="#0f172a"),
        showlegend=legend, legend=dict(orientation="h", y=-0.18, x=0),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#e2e8f0")
    return fig


def sentiment_donut(df):
    counts = df["sentiment"].value_counts().reindex(ORDER).fillna(0)
    fig = go.Figure(go.Pie(labels=counts.index, values=counts.values, hole=0.58, sort=False,
                           marker=dict(colors=[COLORS[k] for k in counts.index]),
                           textinfo="percent+label"))
    fig.add_annotation(text=f"<b>{len(df)}</b><br>feedback", showarrow=False, font=dict(size=16))
    return _style(fig, "Sentiment distribution", legend=False)


def sentiment_by_source(df):
    table = df.groupby(["source", "sentiment"]).size().reset_index(name="count")
    fig = px.bar(table, x="source", y="count", color="sentiment", color_discrete_map=COLORS,
                 category_orders={"sentiment": ORDER}, barmode="stack")
    fig.update_xaxes(title=None)
    return _style(fig, "Sentiment by source")


def sentiment_by_category(df):
    table = df.groupby(["category", "sentiment"]).size().reset_index(name="count")
    fig = px.bar(table, y="category", x="count", color="sentiment", color_discrete_map=COLORS,
                 category_orders={"sentiment": ORDER}, orientation="h", barmode="stack")
    fig.update_yaxes(title=None, categoryorder="total ascending")
    return _style(fig, "Sentiment by feedback category")


def polarity_histogram(df):
    fig = px.histogram(df, x="polarity", nbins=24, color_discrete_sequence=[PRIMARY])
    fig.update_xaxes(title="Sentiment score (-1 = very negative, +1 = very positive)", range=[-1, 1])
    fig.update_yaxes(title="Number of feedback")
    return _style(fig, "How strong are the opinions?", legend=False)


def satisfaction_gauge(score, level):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=score, number={"suffix": " / 100"},
        title={"text": f"<b>{level}</b>", "font": {"size": 18}},
        gauge={"axis": {"range": [0, 100]}, "bar": {"color": PRIMARY},
               "steps": [{"range": [0, 30], "color": "#fecaca"}, {"range": [30, 45], "color": "#fed7aa"},
                         {"range": [45, 55], "color": "#e2e8f0"}, {"range": [55, 70], "color": "#bbf7d0"},
                         {"range": [70, 100], "color": "#86efac"}]}))
    return _style(fig, "Customer satisfaction score", height=300, legend=False)


def category_bar(df):
    counts = df["category"].value_counts()
    return hbar(counts.index, counts.values, "Feedback by category", PRIMARY)


def hbar(labels, values, title, color=PRIMARY, height=340):
    """Horizontal bar chart; first label is drawn at the top."""
    fig = go.Figure(go.Bar(x=list(values), y=list(labels), orientation="h", marker_color=color,
                           text=list(values), textposition="outside", cliponaxis=False))
    fig.update_yaxes(autorange="reversed", title=None)
    fig.update_xaxes(visible=False)
    return _style(fig, title, height=height, legend=False)


def monthly_volume_sentiment(trend):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=trend["month"], y=trend["total"], name="Feedback volume",
                         marker_color=SOFT), secondary_y=False)
    fig.add_trace(go.Scatter(x=trend["month"], y=trend["avg_polarity"], name="Average sentiment",
                             mode="lines+markers", line=dict(color=PRIMARY, width=3)), secondary_y=True)
    fig.update_yaxes(title_text="Feedback count", secondary_y=False)
    fig.update_yaxes(title_text="Avg sentiment (-1 to +1)", range=[-1, 1], showgrid=False, secondary_y=True)
    fig.update_xaxes(tickformat="%b %Y", dtick="M1")
    return _style(fig, "Monthly feedback volume and sentiment")


def monthly_sentiment_stack(trend):
    fig = go.Figure()
    for label, col in (("Positive", "positive_pct"), ("Neutral", "neutral_pct"), ("Negative", "negative_pct")):
        fig.add_trace(go.Bar(x=trend["month"], y=trend[col], name=label, marker_color=COLORS[label]))
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title="% of feedback", range=[0, 100])
    fig.update_xaxes(tickformat="%b %Y", dtick="M1")
    return _style(fig, "Sentiment mix per month (%)")


def topic_heatmap(matrix):
    fig = px.imshow(matrix, text_auto=True, aspect="auto", color_continuous_scale="Reds")
    fig.update_coloraxes(showscale=False)
    fig.update_xaxes(title=None)
    fig.update_yaxes(title=None)
    return _style(fig, "Problem reports per topic and month", height=380, legend=False)


def emerging_bar(table):
    fig = px.bar(table, x="change", y="topic", color="status", color_discrete_map=STATUS_COLORS,
                 orientation="h")
    fig.update_yaxes(title=None, categoryorder="total ascending")
    fig.update_xaxes(title="Change in problem reports vs previous period")
    return _style(fig, "Which concerns are growing?")
