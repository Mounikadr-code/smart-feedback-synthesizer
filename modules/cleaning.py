"""Reading uploaded files and cleaning feedback data."""
import re
import warnings

import pandas as pd

TEXT_COLS = ["feedback", "feedback_text", "review", "review_text", "comment", "comments",
             "text", "message", "response", "description", "content", "remarks"]
DATE_COLS = ["date", "feedback_date", "review_date", "created_at", "timestamp",
             "time", "submitted_at", "datetime"]
SOURCE_COLS = ["source", "channel", "platform", "origin"]

MIN_TEXT_LEN = 3

_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_EMAIL_RE = re.compile(r"\S+@\S+\.\S+")
_HTML_RE = re.compile(r"<[^>]+>")
_SPECIAL_RE = re.compile(r"[^\w\s.,!?'\-]")   # drops emojis and symbols like #, @, *, ~
_REPEAT_PUNCT_RE = re.compile(r"([.,!?])\1+")


def _norm(name):
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def clean_text(value):
    """Remove URLs, HTML, emojis, special characters and extra spaces."""
    if pd.isna(value):
        return ""
    text = str(value)
    text = text.replace("’", "'").replace("‘", "'")
    text = _HTML_RE.sub(" ", text)
    text = _URL_RE.sub(" ", text)
    text = _EMAIL_RE.sub(" ", text)
    text = _SPECIAL_RE.sub(" ", text)
    text = text.replace("_", " ")
    text = _REPEAT_PUNCT_RE.sub(r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def clean_source(value):
    """Tidy a source name ('  google   reviews ' -> 'Google Reviews'). Returns None if empty."""
    if pd.isna(value):
        return None
    text = re.sub(r"\s+", " ", _SPECIAL_RE.sub(" ", str(value))).strip()
    return text.title() if text else None


def parse_dates(series):
    """Convert many date formats to datetime. Unreadable values become NaT.

    ISO dates (2026-07-12) are read strictly as year-month-day. Everything else
    (12/07/2026, 12 Jul 2026 ...) is read day-first, the common format in India/UK.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        parsed = pd.to_datetime(series, errors="coerce", format="ISO8601")
        leftover = series[parsed.isna() & series.notna()]
        if len(leftover):
            other = pd.to_datetime(leftover, errors="coerce", format="mixed", dayfirst=True)
            parsed = parsed.where(parsed.notna(), other)
    return parsed.dt.normalize()


def load_file(file, filename=None):
    """Read a CSV / Excel upload into a DataFrame with friendly error messages."""
    name = (filename or getattr(file, "name", str(file))).lower()
    try:
        if name.endswith(".csv"):
            try:
                df = pd.read_csv(file)
            except UnicodeDecodeError:
                if hasattr(file, "seek"):
                    file.seek(0)
                df = pd.read_csv(file, encoding="latin-1")
        elif name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file)
        else:
            raise ValueError("Unsupported file type. Please upload a .csv, .xlsx or .xls file.")
    except pd.errors.EmptyDataError:
        raise ValueError("The file is empty.")
    except ValueError:
        raise
    except Exception as exc:  # corrupt file, missing xlrd, etc.
        raise ValueError(f"Could not read '{name}': {exc}") from exc
    if df.empty:
        raise ValueError("The file has no rows.")
    return df


def detect_columns(df):
    """Find which columns hold the feedback text, date and source."""
    lookup = {_norm(c): c for c in df.columns}

    def find(candidates):
        for cand in candidates:
            if cand in lookup:
                return lookup[cand]
        return None

    date_col, source_col = find(DATE_COLS), find(SOURCE_COLS)
    text_col = find(TEXT_COLS)
    if text_col is None:  # fall back to the column with the longest text
        best, best_len = None, 0
        for col in df.columns:
            if col in (date_col, source_col):
                continue
            if pd.api.types.is_numeric_dtype(df[col]) or pd.api.types.is_datetime64_any_dtype(df[col]):
                continue
            avg = df[col].dropna().astype(str).str.len().mean()
            if avg == avg and avg > best_len:  # avg == avg filters NaN
                best, best_len = col, avg
        text_col = best
    if text_col is None:
        raise ValueError(
            "Could not find a feedback text column. Please name it 'feedback', 'review' or 'comment'."
        )
    return {"text": text_col, "date": date_col, "source": source_col}


def clean_dataframe(df, default_source="Manual Upload"):
    """Full cleaning pipeline. Returns (clean_df, report).

    clean_df has exactly three columns: feedback_text, source, feedback_date.
    """
    if df is None or df.empty:
        raise ValueError("There is no data to clean.")
    cols = detect_columns(df)
    report = {"rows_received": len(df), "missing_text_removed": 0, "duplicates_removed": 0,
              "sources_filled": 0, "dates_filled": 0, "rows_final": 0}

    work = pd.DataFrame({"feedback_text": df[cols["text"]].map(clean_text)})
    work["source"] = df[cols["source"]].map(clean_source) if cols["source"] else None
    work["feedback_date"] = parse_dates(df[cols["date"]]) if cols["date"] else pd.NaT

    # 1. missing / empty text
    keep = work["feedback_text"].str.len() >= MIN_TEXT_LEN
    report["missing_text_removed"] = int((~keep).sum())
    work = work[keep].copy()

    # 2. missing source and date
    default_source = clean_source(default_source) or "Manual Upload"
    missing_src = work["source"].isna()
    report["sources_filled"] = int(missing_src.sum())
    work["source"] = work["source"].where(~missing_src, default_source)

    missing_date = work["feedback_date"].isna()
    report["dates_filled"] = int(missing_date.sum())
    work["feedback_date"] = work["feedback_date"].fillna(pd.Timestamp.today().normalize())

    # 3. duplicates (same text + source + day)
    key = (work["feedback_text"].str.lower() + "|" + work["source"].str.lower()
           + "|" + work["feedback_date"].dt.strftime("%Y-%m-%d"))
    dup = key.duplicated()
    report["duplicates_removed"] = int(dup.sum())
    work = work[~dup]

    work = work.reset_index(drop=True)
    report["rows_final"] = len(work)
    if work.empty:
        raise ValueError("No usable feedback rows were found after cleaning.")
    return work, report
