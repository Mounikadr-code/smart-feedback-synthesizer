"""Glue code: clean -> analyse -> save."""
import pandas as pd

from modules import database
from modules.categorizer import assign_topic, categorize
from modules.cleaning import clean_dataframe, load_file
from modules.sentiment import analyze_sentiment


def analyze_dataframe(df, text_col="feedback_text"):
    """Add sentiment, polarity, topic and category columns to a DataFrame."""
    out = df.copy()
    results = out[text_col].map(analyze_sentiment)
    out["sentiment"] = [r[0] for r in results]
    out["polarity"] = [r[1] for r in results]
    out["topic"] = out[text_col].map(assign_topic)
    out["category"] = [categorize(t, s, tp) for t, s, tp in zip(out[text_col], out["sentiment"], out["topic"])]
    return out


def ingest_dataframe(raw_df, filename="Manual entry", default_source="Manual Upload"):
    """Clean + analyse + store a raw DataFrame. Returns a report dict."""
    clean_df, report = clean_dataframe(raw_df, default_source=default_source)
    analysed = analyze_dataframe(clean_df)
    result = database.insert_feedback(analysed, filename=filename, rows_received=report["rows_received"])
    report.update(result)
    report["raw_preview"] = raw_df.head(10)
    report["clean_preview"] = clean_df.head(10)
    return report


def ingest_file(file, filename=None, default_source="Manual Upload"):
    """Read an uploaded CSV/Excel file and ingest it."""
    name = filename or getattr(file, "name", "uploaded file")
    raw = load_file(file, filename=name)
    return ingest_dataframe(raw, filename=name, default_source=default_source)


def ingest_manual(text, source, date):
    """Ingest a single feedback typed in by the user."""
    raw = pd.DataFrame({"feedback": [text], "source": [source], "date": [pd.Timestamp(date)]})
    return ingest_dataframe(raw, filename="Manual entry", default_source=source)


def reanalyze_all():
    """Re-run the analysis on everything in the database (after changing rules)."""
    stored = database.load_feedback()
    if stored.empty:
        return 0
    analysed = analyze_dataframe(stored)
    database.update_analysis(analysed[["id", "sentiment", "polarity", "category", "topic"]])
    return len(analysed)
