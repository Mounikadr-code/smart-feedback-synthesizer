"""Data Cleaning page: shows what the cleaner did and the cleaned data."""
import streamlit as st

from views import ui


def render(df, df_all):
    ui.header("🧹 Data Cleaning", "Duplicates removed, missing values handled, spaces and special characters cleaned.")
    ui.show_flash()

    last = st.session_state.get("last_cleaning")
    st.subheader("Last upload")
    if not last:
        st.info("Upload a file (or load the sample data) in this session to see a before/after comparison here.")
    else:
        r = last["report"]
        st.caption(f"File: {last['file']}")
        cols = st.columns(6)
        cols[0].metric("Rows received", r["rows_received"])
        cols[1].metric("Empty rows removed", r["missing_text_removed"])
        cols[2].metric("Duplicates removed", r["duplicates_removed"])
        cols[3].metric("Dates filled", r["dates_filled"])
        cols[4].metric("Sources filled", r["sources_filled"])
        cols[5].metric("Clean rows", r["rows_final"])
        b, a = st.columns(2)
        with b:
            st.markdown("**Before (raw file, first rows)**")
            st.dataframe(r["raw_preview"])
        with a:
            st.markdown("**After (cleaned)**")
            clean = r["clean_preview"].copy()
            clean["feedback_date"] = clean["feedback_date"].dt.strftime("%Y-%m-%d")
            st.dataframe(clean)

    st.subheader("All cleaned data in the database")
    if df_all.empty:
        st.info("The database is empty.")
        return
    st.caption(f"{len(df_all):,} cleaned feedback rows are stored. Cleaning rules: trim extra spaces, remove URLs, "
               "HTML, emojis and special characters, fill missing source/date, drop empty text and duplicates "
               "(same text + source + date).")
    view = df_all[["feedback_date", "source", "feedback_text"]].copy()
    view["feedback_date"] = view["feedback_date"].dt.strftime("%Y-%m-%d")
    view.columns = ["Date", "Source", "Cleaned feedback"]
    ui.table(view)
    st.download_button("⬇️ Download cleaned data (CSV)", view.to_csv(index=False).encode("utf-8"),
                       "cleaned_feedback.csv", "text/csv")
