"""Upload Feedback page: CSV/Excel upload, manual entry, history and data tools."""
from datetime import date
from pathlib import Path

import streamlit as st

from modules import database, pipeline
from modules.cleaning import load_file
from views import ui

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SOURCES = ["Google Reviews", "Twitter", "Email", "Feedback Form", "Support Chat", "Other"]
SAMPLE_FILES = {0: "sample_feedback.csv", 1: "sample_feedback_part1.csv", 2: "sample_feedback_part2.csv"}


def describe(name, r):
    """One-line summary of an ingestion report."""
    return (f"**{name}**: {r['added']} new feedback saved to memory "
            f"({r['already_stored']} were already stored). Cleaning removed {r['duplicates_removed']} duplicates "
            f"and {r['missing_text_removed']} empty rows; filled {r['dates_filled']} missing dates "
            f"and {r['sources_filled']} missing sources.")


def remember_cleaning(name, report):
    """Keep the last cleaning report so the Data Cleaning page can show before/after."""
    st.session_state["last_cleaning"] = {"file": name, "report": report}


def load_sample_part(part):
    """Load one of the bundled demo files. Shows a message and refreshes the app."""
    path = DATA_DIR / SAMPLE_FILES[part]
    if not path.exists():
        st.error("Sample file not found. Run `python generate_sample_data.py` first.")
        return
    try:
        report = pipeline.ingest_file(str(path), filename=path.name, default_source="Sample")
        remember_cleaning(path.name, report)
        ui.set_flash("success", describe(path.name, report))
        st.rerun()
    except ValueError as exc:
        st.error(str(exc))


def sample_buttons(prefix):
    c0, c1, c2 = st.columns(3)
    if c0.button("📦 Quick sample (40 rows)", key=f"{prefix}_s0"):
        load_sample_part(0)
    if c1.button("📦 Sample Part 1 (Jun-Aug)", key=f"{prefix}_s1"):
        load_sample_part(1)
    if c2.button("📦 Sample Part 2 (Sep-Nov)", key=f"{prefix}_s2"):
        load_sample_part(2)


def tab_upload():
    st.write("Upload one or more **CSV / Excel** files. Needed column: `feedback` (or `review` / `comment`). "
             "Optional columns: `date`, `source`.")
    files = st.file_uploader("Choose files", type=["csv", "xlsx", "xls"], accept_multiple_files=True)
    default_source = st.text_input("Default source (used when the file has no source column)", "Feedback Form")
    if not files:
        st.caption("No file yet? Use the sample data buttons in the **Data tools** tab.")
        return

    for f in files:
        with st.expander(f"Preview: {f.name}"):
            try:
                st.dataframe(load_file(f, f.name).head(8))
            except ValueError as exc:
                st.error(str(exc))
            finally:
                f.seek(0)

    if st.button("🚀 Clean, analyse & save", type="primary"):
        for f in files:
            try:
                report = pipeline.ingest_file(f, filename=f.name, default_source=default_source)
                remember_cleaning(f.name, report)
                ui.set_flash("success", describe(f.name, report))
            except ValueError as exc:
                ui.set_flash("error", f"{f.name}: {exc}")
            except Exception as exc:  # never crash the demo
                ui.set_flash("error", f"{f.name}: unexpected problem - {exc}")
        st.rerun()


def tab_manual(df_all):
    with st.form("manual_entry", clear_on_submit=True):
        text = st.text_area("Customer feedback", placeholder="e.g. The app keeps crashing when I pay by UPI")
        c1, c2, c3 = st.columns(3)
        source = c1.selectbox("Source", SOURCES)
        custom = c2.text_input("Custom source (optional)")
        when = c3.date_input("Date", value=date.today(), max_value=date.today())
        submitted = st.form_submit_button("➕ Add feedback", type="primary")
    if submitted:
        if not text.strip():
            st.warning("Please type some feedback first.")
            return
        try:
            final_source = custom.strip() or source
            memory = ui.get_memory()                       # recall BEFORE saving, so it cannot find itself
            recalled = memory.recall_similar(text, local_df=df_all, k=3)
            report = pipeline.ingest_manual(text, final_source, when)
            if report["added"]:
                ui.set_flash("success", "Feedback saved and analysed.")
                if recalled["items"]:
                    lines = "\n".join(f"- {i['text']}  \n  _{i['detail']}_" for i in recalled["items"])
                    ui.set_flash("info", f"**Similar earlier feedback recalled [{recalled['mode']}]**\n\n{lines}")
                elif recalled["error"]:
                    ui.set_flash("warning", f"Hindsight recall failed: {recalled['error']}")
            else:
                ui.set_flash("warning", "This exact feedback (same text, source and date) is already stored.")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))


def tab_history():
    log = database.get_upload_log()
    if log.empty:
        st.info("No uploads yet.")
    else:
        ui.table(log)


def tab_tools(df_all):
    st.markdown("**Demo data** - load Part 1 first, explore the dashboard, then load Part 2 "
                "to watch the trends and recommendations update.")
    sample_buttons("tools")
    st.markdown("---")
    if st.button("🔄 Re-run analysis on all stored feedback"):
        n = pipeline.reanalyze_all()
        ui.set_flash("success", f"Re-analysed {n} feedback rows.")
        st.rerun()
    st.markdown("---")
    st.markdown("**Danger zone**")
    sure = st.checkbox("I understand this permanently deletes all stored feedback")
    if st.button("🗑️ Clear all stored feedback", disabled=not sure):
        database.clear_database()
        ui.set_flash("success", "All stored feedback was deleted.")
        st.rerun()


def render(df, df_all):
    ui.header("📤 Upload Feedback", "Every upload is cleaned, analysed and saved to the database (memory).")
    ui.show_flash()
    t1, t2, t3, t4 = st.tabs(["📁 Upload file", "✍️ Enter manually", "🕘 Upload history", "⚙️ Data tools"])
    with t1:
        tab_upload()
    with t2:
        tab_manual(df_all)
    with t3:
        tab_history()
    with t4:
        tab_tools(df_all)
