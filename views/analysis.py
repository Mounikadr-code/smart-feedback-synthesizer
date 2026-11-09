"""Feedback Analysis page: categories, topics and a searchable table of all feedback."""
import streamlit as st

from modules import charts
from modules.categorizer import CATEGORIES
from views import ui


def render(df, df_all):
    ui.header("🔍 Feedback Analysis", "Every piece of feedback, automatically categorised and tagged by topic.")
    ui.show_flash()
    if df_all.empty:
        st.info("Upload some feedback first.")
        return
    if df.empty:
        ui.no_data_message()
        return

    c1, c2 = st.columns(2)
    with c1:
        ui.chart(charts.category_bar(df), "an_cat")
    with c2:
        topics = df[df["topic"] != "General"]["topic"].value_counts().head(8)
        ui.chart(charts.hbar(topics.index, topics.values, "Most discussed topics"), "an_topics")

    summary = df["category"].value_counts().reindex(CATEGORIES).dropna().astype(int).reset_index()
    summary.columns = ["Category", "Count"]
    summary["Share"] = (100 * summary["Count"] / len(df)).round(1).astype(str) + "%"
    ui.table(summary)

    st.subheader("All collected feedback")
    f1, f2, f3 = st.columns(3)
    cats = f1.multiselect("Category", sorted(df["category"].unique()))
    sents = f2.multiselect("Sentiment", ["Positive", "Neutral", "Negative"])
    topic_sel = f3.multiselect("Topic", sorted(df["topic"].unique()))
    query = st.text_input("Search the feedback text", placeholder="e.g. payment")

    view = df
    if cats:
        view = view[view["category"].isin(cats)]
    if sents:
        view = view[view["sentiment"].isin(sents)]
    if topic_sel:
        view = view[view["topic"].isin(topic_sel)]
    if query.strip():
        view = view[view["feedback_text"].str.contains(query.strip(), case=False, regex=False)]

    st.caption(f"Showing {len(view):,} of {len(df):,} feedback")
    table = view.sort_values("feedback_date", ascending=False)[
        ["feedback_date", "source", "feedback_text", "sentiment", "polarity", "category", "topic"]].copy()
    table["feedback_date"] = table["feedback_date"].dt.strftime("%Y-%m-%d")
    table.columns = ["Date", "Source", "Feedback", "Sentiment", "Score", "Category", "Topic"]
    ui.table(table)
    st.download_button("⬇️ Download as CSV", table.to_csv(index=False).encode("utf-8"),
                       "feedback_analysis.csv", "text/csv")
