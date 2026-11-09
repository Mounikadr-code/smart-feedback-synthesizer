"""Recommendations page."""
import streamlit as st

from modules import recommendations as rec
from views import ui


def render(df, df_all):
    ui.header("💡 Recommendations",
              "Problems ranked by how often they are reported, how negative customers are and how recent they are.")
    ui.show_flash()
    if df_all.empty:
        st.info("Upload some feedback first.")
        return
    if df.empty:
        ui.no_data_message()
        return

    days = st.select_slider("Treat the last N days as 'recent'", options=[14, 30, 60, 90], value=30)
    for text in rec.key_insights(df, days):
        ui.insight(text)

    issues = rec.priority_issues(df, days)
    st.subheader("Priority problems")
    if issues.empty:
        st.info("No problems detected - nothing to prioritise.")
    else:
        view = issues[["rank", "topic", "priority", "score", "mentions", "recent_mentions", "avg_negativity", "owner"]].copy()
        view.columns = ["Rank", "Problem", "Priority", "Score", "Reports", "Recent", "Negativity", "Suggested owner"]
        ui.table(view, column_config={
            "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d")})

        st.subheader("Action plan")
        for _, row in issues.head(6).iterrows():
            with st.expander(f"#{row['rank']}  {row['topic']}  -  {row['priority']} priority (score {row['score']})",
                             expanded=row["rank"] == 1):
                st.markdown(f"**Recommended improvement:** {row['recommendation']}")
                st.markdown(f"**Suggested owner:** {row['owner']}")
                st.markdown(f"**Evidence:** {row['mentions']} reports ({row['share_pct']}% of all problems), "
                            f"{row['recent_mentions']} in the last {days} days, average negativity {row['avg_negativity']}.")
                st.markdown(f"**Most negative comment:** _{row['example']}_")
        export = issues[["rank", "topic", "priority", "score", "mentions", "recommendation", "owner"]]
        st.download_button("⬇️ Download recommendations (CSV)", export.to_csv(index=False).encode("utf-8"),
                           "recommendations.csv", "text/csv")

    st.subheader("Feature requests")
    feats = rec.feature_requests(df, days)
    if feats.empty:
        st.info("No feature requests found.")
    else:
        view = feats[["rank", "feature", "requests", "recent_requests", "recommendation", "owner"]].copy()
        view.columns = ["Rank", "Feature", "Requests", "Recent", "Suggestion", "Suggested owner"]
        ui.table(view)
