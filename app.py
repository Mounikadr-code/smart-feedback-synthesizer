"""Smart User Feedback Synthesizer - main entry point.

Run with:   streamlit run app.py
"""
import pandas as pd
import streamlit as st

from modules import database
from views import (analysis, cleaning_view, hindsight_view, home, recommendations_view,
                   sentiment_view, trends_view, ui, upload)

st.set_page_config(page_title="Smart Feedback Synthesizer", page_icon="💬", layout="wide")
ui.inject_css()

PAGES = {
    "🏠  Home": home,
    "📤  Upload Feedback": upload,
    "🧹  Data Cleaning": cleaning_view,
    "🔍  Feedback Analysis": analysis,
    "😊  Sentiment Analysis": sentiment_view,
    "🧠  Hindsight Memory": hindsight_view,
    "📈  Trend Analysis": trends_view,
    "💡  Recommendations": recommendations_view,
}


def apply_filters(df_all):
    """Sidebar filters (source + date range). Returns the filtered DataFrame."""
    st.sidebar.markdown("---")
    st.sidebar.subheader("Filters")
    sources = sorted(df_all["source"].unique())
    chosen = st.sidebar.multiselect("Source", sources, default=sources)

    dmin, dmax = df_all["feedback_date"].min().date(), df_all["feedback_date"].max().date()
    picked = st.sidebar.date_input("Date range", value=(dmin, dmax), min_value=dmin, max_value=dmax)
    if isinstance(picked, (list, tuple)):
        start = picked[0] if len(picked) > 0 else dmin
        end = picked[1] if len(picked) > 1 else start
    else:
        start = end = picked

    mask = (df_all["source"].isin(chosen)
            & (df_all["feedback_date"] >= pd.Timestamp(start))
            & (df_all["feedback_date"] <= pd.Timestamp(end)))
    return df_all[mask]


def main():
    st.sidebar.markdown("## 💬 Feedback Synthesizer")
    st.sidebar.caption("Turn customer feedback into product decisions")
    choice = st.sidebar.radio("Navigate", list(PAGES), label_visibility="collapsed")

    try:
        df_all = database.load_feedback()
    except Exception as exc:
        st.error(f"Could not open the feedback database: {exc}")
        st.stop()

    filtered = df_all
    if not df_all.empty:
        if choice != "📤  Upload Feedback":
            filtered = apply_filters(df_all)
        st.sidebar.markdown("---")
        st.sidebar.markdown(
            f"🗄️ **Memory:** {len(df_all):,} feedback stored  \n"
            f"📅 {df_all['feedback_date'].min():%d %b %Y} → {df_all['feedback_date'].max():%d %b %Y}"
        )
    else:
        st.sidebar.markdown("---")
        st.sidebar.markdown("🗄️ **Memory:** empty - upload feedback to begin")

    PAGES[choice].render(filtered, df_all)


main()
