"""Sentiment Analysis page."""
import streamlit as st

from modules import charts
from modules import sentiment as sent
from views import ui


def render(df, df_all):
    ui.header("😊 Sentiment Analysis", "How do customers feel? Each feedback is scored from -1 (very negative) to +1 (very positive).")
    ui.show_flash()
    if df_all.empty:
        st.info("Upload some feedback first.")
        return
    if df.empty:
        ui.no_data_message()
        return

    pct = sent.sentiment_percentages(df)
    counts = df["sentiment"].value_counts()
    score = sent.satisfaction_score(pct["Positive"], pct["Negative"])
    level = sent.satisfaction_level(pct["Positive"], pct["Negative"])

    cols = st.columns(3)
    for col, label, color in zip(cols, ("Positive", "Neutral", "Negative"), ("#10b981", "#94a3b8", "#ef4444")):
        with col:
            ui.kpi(label, f"{pct[label]}%", f"{counts.get(label, 0):,} feedback", color)
    st.write("")

    c1, c2 = st.columns(2)
    with c1:
        ui.chart(charts.sentiment_donut(df), "sa_donut")
    with c2:
        ui.chart(charts.satisfaction_gauge(score, level), "sa_gauge")
        st.caption("Score = (positive% - negative% + 100) / 2. Above 55 is satisfied, below 45 is dissatisfied.")

    c3, c4 = st.columns(2)
    with c3:
        ui.chart(charts.sentiment_by_source(df), "sa_source")
    with c4:
        ui.chart(charts.sentiment_by_category(df), "sa_category")

    ui.chart(charts.polarity_histogram(df), "sa_hist")

    c5, c6 = st.columns(2)
    with c5:
        st.markdown("**Most positive feedback**")
        for _, r in df.sort_values("polarity", ascending=False).drop_duplicates("feedback_text").head(5).iterrows():
            st.success(f"{r['feedback_text']}  ({r['polarity']:+.2f})")
    with c6:
        st.markdown("**Most negative feedback**")
        for _, r in df.sort_values("polarity").drop_duplicates("feedback_text").head(5).iterrows():
            st.error(f"{r['feedback_text']}  ({r['polarity']:+.2f})")
