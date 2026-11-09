"""Trend Analysis page: compares current feedback with stored history."""
import numpy as np
import pandas as pd
import streamlit as st

from modules import charts, trends
from views import ui


def _num(value, digits=2):
    return None if value is None or (isinstance(value, float) and np.isnan(value)) else round(float(value), digits)


def render(df, df_all):
    ui.header("📈 Trend Analysis", "Current feedback compared with everything the system remembers from earlier uploads.")
    ui.show_flash()
    if df_all.empty:
        st.info("Upload some feedback first.")
        return
    if df.empty:
        ui.no_data_message()
        return

    days = st.select_slider("Compare the latest period with the one before it (days)", options=[14, 30, 60, 90], value=30)
    cmp = trends.compare_periods(df, days)
    cur, prev = cmp["current"], cmp["previous"]
    st.caption(f"Latest period: {cmp['current_start']:%d %b} - {cmp['anchor']:%d %b %Y}  |  "
               f"Previous period: {cmp['previous_start']:%d %b} - {(cmp['current_start'] - pd.Timedelta(days=1)):%d %b %Y}")

    has_prev = prev["total"] > 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Feedback (latest period)", cur["total"], f"{cur['total'] - prev['total']:+d}" if has_prev else None,
              delta_color="off")
    c2.metric("Average sentiment", _num(cur["avg_polarity"], 2) if cur["total"] else "n/a",
              f"{cmp['delta']:+.2f}" if cmp["delta"] is not None else None)
    c3.metric("Positive %", f"{_num(cur['positive_pct'], 1)}%" if cur["total"] else "n/a",
              f"{cur['positive_pct'] - prev['positive_pct']:+.1f}" if has_prev and cur["total"] else None)
    c4.metric("Negative %", f"{_num(cur['negative_pct'], 1)}%" if cur["total"] else "n/a",
              f"{cur['negative_pct'] - prev['negative_pct']:+.1f}" if has_prev and cur["total"] else None,
              delta_color="inverse")
    if not has_prev:
        st.info("There is no earlier period to compare with yet. Upload older feedback or reduce the period length.")
    else:
        st.markdown(f"**Overall customer sentiment is {cmp['direction'].lower()}.**")

    monthly = trends.monthly_trend(df)
    t1, t2 = st.columns(2)
    with t1:
        ui.chart(charts.monthly_volume_sentiment(monthly), "tr_vol")
    with t2:
        ui.chart(charts.monthly_sentiment_stack(monthly), "tr_stack")

    st.subheader("🚨 Emerging concerns")
    st.caption("Problem topics that are new or growing compared with the previous period.")
    emerging = trends.emerging_concerns(df, days)
    if emerging.empty:
        st.info("No problem reports in these periods.")
    else:
        e1, e2 = st.columns([1, 1])
        with e1:
            ui.chart(charts.emerging_bar(emerging), "tr_emerging")
        with e2:
            show = emerging.copy()
            show["growth_pct"] = show["growth_pct"].map(lambda v: "New" if pd.isna(v) else f"{v:+.0f}%")
            show.columns = ["Topic", "Previous", "Current", "Change", "Growth", "Status"]
            ui.table(show)

    st.subheader("🔁 Repeated complaints")
    st.caption("Problems reported at least 3 times across at least 2 different months.")
    repeated = trends.repeated_complaints(df)
    if repeated.empty:
        st.info("No repeated complaints found with the current filters.")
    else:
        show = repeated.copy()
        show["first_seen"] = show["first_seen"].dt.strftime("%d %b %Y")
        show["last_seen"] = show["last_seen"].dt.strftime("%d %b %Y")
        show.columns = ["Topic", "Mentions", "Months active", "First seen", "Last seen", "Avg sentiment"]
        ui.table(show)

    matrix = trends.topic_month_matrix(df)
    if not matrix.empty:
        ui.chart(charts.topic_heatmap(matrix), "tr_heat")
