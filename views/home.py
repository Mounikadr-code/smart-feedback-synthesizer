"""Home dashboard."""
import streamlit as st

from modules import charts, trends
from modules import recommendations as rec
from modules import sentiment as sent
from views import ui
from views.upload import sample_buttons


def render(df, df_all):
    ui.header("💬 Smart User Feedback Synthesizer",
              "Collects, cleans and analyses customer feedback, remembers it over time, "
              "and turns repeated problems into product improvements.")
    ui.show_flash()

    if df_all.empty:
        st.info("👋 Welcome! There is no feedback yet. Load the demo data to see every feature, "
                "or go to **Upload Feedback** to add your own CSV / Excel file.")
        st.markdown("**Quick demo:** load Part 1, explore the dashboard, then load Part 2 and watch "
                    "the trends, emerging concerns and recommendations update.")
        sample_buttons("home")
        return
    if df.empty:
        ui.no_data_message()
        return

    pct = sent.sentiment_percentages(df)
    score = sent.satisfaction_score(pct["Positive"], pct["Negative"])
    level = sent.satisfaction_level(pct["Positive"], pct["Negative"])
    counts = df["sentiment"].value_counts()

    cols = st.columns(5)
    with cols[0]:
        ui.kpi("Total feedback", f"{len(df):,}", f"{df['source'].nunique()} sources", "#4f46e5")
    with cols[1]:
        ui.kpi("Positive", f"{counts.get('Positive', 0):,}", f"{pct['Positive']}% of feedback", "#10b981")
    with cols[2]:
        ui.kpi("Neutral", f"{counts.get('Neutral', 0):,}", f"{pct['Neutral']}% of feedback", "#94a3b8")
    with cols[3]:
        ui.kpi("Negative", f"{counts.get('Negative', 0):,}", f"{pct['Negative']}% of feedback", "#ef4444")
    with cols[4]:
        ui.kpi("Satisfaction", f"{score}/100", level, "#f59e0b")

    st.write("")
    st.subheader("Key insights")
    insights = rec.key_insights(df)
    for text in insights or ["Not enough data for insights yet."]:
        ui.insight(text)

    c1, c2 = st.columns([1, 2])
    with c1:
        ui.chart(charts.sentiment_donut(df), "home_donut")
    with c2:
        ui.chart(charts.monthly_volume_sentiment(trends.monthly_trend(df)), "home_monthly")

    c3, c4 = st.columns(2)
    with c3:
        prob = trends.problems(df)
        prob = prob[prob["topic"] != "General"]
        top = prob["topic"].value_counts().head(6)
        if top.empty:
            st.info("No repeated problems detected yet.")
        else:
            ui.chart(charts.hbar(top.index, top.values, "Most common complaints", "#ef4444"), "home_complaints")
    with c4:
        feats = rec.feature_requests(df)
        if feats.empty:
            st.info("No feature requests found yet.")
        else:
            top = feats.head(6)
            ui.chart(charts.hbar(top["feature"], top["requests"], "Frequently requested features", "#4f46e5"),
                     "home_features")

    st.subheader("Top improvement recommendations")
    issues = rec.priority_issues(df)
    if issues.empty:
        st.info("Recommendations appear once problems are detected.")
    else:
        for _, row in issues.head(3).iterrows():
            with st.container(border=True):
                st.markdown(f"**#{row['rank']} {row['topic']}** &nbsp; {ui.pill(row['priority'])}",
                            unsafe_allow_html=True)
                st.write(row["recommendation"])
                st.caption(f"{row['mentions']} reports | owner: {row['owner']}")

    st.subheader("Latest feedback")
    latest = df.sort_values("feedback_date", ascending=False).head(8)[
        ["feedback_date", "source", "feedback_text", "sentiment", "category"]].copy()
    latest["feedback_date"] = latest["feedback_date"].dt.strftime("%d %b %Y")
    latest.columns = ["Date", "Source", "Feedback", "Sentiment", "Category"]
    ui.table(latest)
