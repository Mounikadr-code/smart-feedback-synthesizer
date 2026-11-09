"""Trend analysis: monthly trends, period comparison, repeated and emerging problems."""
import numpy as np
import pandas as pd

PROBLEM_CATEGORIES = ["Technical Issues", "Complaints"]


def problems(df):
    """Feedback that describes something going wrong (bugs + complaints)."""
    if df.empty:
        return df
    return df[df["category"].isin(PROBLEM_CATEGORIES)]


def monthly_trend(df):
    """One row per month: volume, average sentiment and sentiment percentages."""
    if df.empty:
        return pd.DataFrame(columns=["month", "total", "avg_polarity", "positive", "negative",
                                     "neutral", "positive_pct", "negative_pct", "neutral_pct"])
    work = df.assign(month=df["feedback_date"].dt.to_period("M").dt.to_timestamp())
    grouped = work.groupby("month").agg(
        total=("sentiment", "size"),
        avg_polarity=("polarity", "mean"),
        positive=("sentiment", lambda s: int((s == "Positive").sum())),
        negative=("sentiment", lambda s: int((s == "Negative").sum())),
        neutral=("sentiment", lambda s: int((s == "Neutral").sum())),
    ).reset_index()
    for col in ("positive", "negative", "neutral"):
        grouped[f"{col}_pct"] = (100 * grouped[col] / grouped["total"]).round(1)
    grouped["avg_polarity"] = grouped["avg_polarity"].round(3)
    return grouped


def split_periods(df, days=30):
    """Split into the latest `days` days and the `days` before that.

    The latest feedback date in the data is used as 'today', so the sample
    data works no matter when you run the project.
    """
    anchor = df["feedback_date"].max()
    current = df[df["feedback_date"] > anchor - pd.Timedelta(days=days)]
    previous = df[(df["feedback_date"] > anchor - pd.Timedelta(days=2 * days))
                  & (df["feedback_date"] <= anchor - pd.Timedelta(days=days))]
    return current, previous, anchor


def compare_periods(df, days=30):
    """Compare the latest period with the one before it."""
    if df.empty:
        return None
    cur, prev, anchor = split_periods(df, days)

    def stats(part):
        n = len(part)
        if n == 0:
            return {"total": 0, "avg_polarity": np.nan, "positive_pct": np.nan, "negative_pct": np.nan}
        return {
            "total": n,
            "avg_polarity": round(part["polarity"].mean(), 3),
            "positive_pct": round(100 * (part["sentiment"] == "Positive").mean(), 1),
            "negative_pct": round(100 * (part["sentiment"] == "Negative").mean(), 1),
        }

    c, p = stats(cur), stats(prev)
    delta = None
    direction = "Not enough data"
    if p["total"] > 0 and c["total"] > 0:
        delta = round(c["avg_polarity"] - p["avg_polarity"], 3)
        direction = "Improving" if delta > 0.05 else "Declining" if delta < -0.05 else "Stable"
    return {"current": c, "previous": p, "delta": delta, "direction": direction, "anchor": anchor,
            "current_start": anchor - pd.Timedelta(days=days - 1),
            "previous_start": anchor - pd.Timedelta(days=2 * days - 1)}


def emerging_concerns(df, days=30, min_count=3, min_growth_pct=50):
    """Topics whose problem reports are new or rising compared with the previous period."""
    if df.empty:
        return pd.DataFrame()
    cur, prev, _ = split_periods(df, days)
    c = problems(cur).query("topic != 'General'").groupby("topic").size()
    p = problems(prev).query("topic != 'General'").groupby("topic").size()
    table = pd.DataFrame({"previous": p, "current": c}).fillna(0).astype(int)
    if table.empty:
        return pd.DataFrame()
    table["change"] = table["current"] - table["previous"]
    table["growth_pct"] = np.where(table["previous"] > 0, 100 * table["change"] / table["previous"].replace(0, np.nan), np.nan)

    def status(row):
        if row["previous"] == 0 and row["current"] >= min_count:
            return "New concern"
        if row["previous"] > 0 and row["current"] >= min_count and row["growth_pct"] >= min_growth_pct:
            return "Rising"
        if row["change"] <= -2:
            return "Improving"
        return "Stable"

    table["status"] = table.apply(status, axis=1)
    table = table.reset_index().rename(columns={"index": "topic"})
    return table.sort_values(["change", "current"], ascending=False).reset_index(drop=True)


def repeated_complaints(df, min_count=3, min_months=2):
    """Problems that keep coming back: many mentions spread over several months."""
    prob = problems(df)
    prob = prob[prob["topic"] != "General"] if not prob.empty else prob
    if prob.empty:
        return pd.DataFrame()
    prob = prob.assign(month=prob["feedback_date"].dt.to_period("M"))
    grouped = prob.groupby("topic").agg(
        mentions=("sentiment", "size"),
        months_active=("month", "nunique"),
        first_seen=("feedback_date", "min"),
        last_seen=("feedback_date", "max"),
        avg_polarity=("polarity", "mean"),
    ).reset_index()
    grouped = grouped[(grouped["mentions"] >= min_count) & (grouped["months_active"] >= min_months)]
    grouped["avg_polarity"] = grouped["avg_polarity"].round(2)
    return grouped.sort_values("mentions", ascending=False).reset_index(drop=True)


def topic_month_matrix(df, top_n=8):
    """Topics x months table of problem counts (used for the heatmap)."""
    prob = problems(df)
    prob = prob[prob["topic"] != "General"] if not prob.empty else prob
    if prob.empty:
        return pd.DataFrame()
    prob = prob.assign(month=prob["feedback_date"].dt.strftime("%b %Y"),
                       month_sort=prob["feedback_date"].dt.to_period("M"))
    top = prob["topic"].value_counts().head(top_n).index
    prob = prob[prob["topic"].isin(top)]
    pivot = prob.pivot_table(index="topic", columns="month_sort", values="sentiment", aggfunc="size", fill_value=0)
    pivot.columns = [c.strftime("%b %Y") for c in pivot.columns]
    return pivot.loc[prob["topic"].value_counts().loc[top].index]
