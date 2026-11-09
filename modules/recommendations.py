"""Smart recommendations: rank problems and suggest product improvements."""
import numpy as np
import pandas as pd

from modules.trends import problems, split_periods

# topic -> (suggested action, team that should own it)
ACTIONS = {
    "App Crashes & Freezing": ("Run a stability sprint: collect crash logs, fix the top crash causes and add automated regression tests before the next release.", "Engineering / QA"),
    "Slow Performance": ("Profile slow screens, compress images, cache frequent requests and set a page-load budget (for example under 2 seconds).", "Engineering"),
    "Login & Account Problems": ("Fix OTP delivery (add a backup SMS/email provider), add a clear error message and a self-service password reset.", "Engineering / Security"),
    "Payment & Billing Issues": ("Audit the payment gateway failures, add automatic refunds for failed transactions and a backup payment provider.", "Engineering / Finance"),
    "Delivery & Shipping": ("Review courier performance, give customers live tracking and proactive delay notifications, and compensate late orders.", "Operations / Logistics"),
    "Customer Support": ("Reduce first-response time with a chatbot for common questions, support-agent training and clear response-time targets.", "Customer Success"),
    "Pricing & Charges": ("Show the full price (including fees) up front, review plans against competitors and offer a cheaper entry tier.", "Product / Finance"),
    "Notifications": ("Add notification preferences (frequency and type) and fix delivery of important alerts.", "Product / Engineering"),
    "UI & Usability": ("Run quick usability tests on the checkout and menu flows, then simplify navigation and layout.", "Design / UX"),
    "Search & Discovery": ("Improve search relevance with typo tolerance, better filters and personalised suggestions.", "Product / Data"),
    "Product Quality": ("Tighten quality checks with suppliers and review packaging for damaged or defective items.", "Operations / Quality"),
    "Onboarding & Help": ("Add an interactive first-run tutorial and a searchable help centre.", "Product / Design"),
    "Dark Mode / Themes": ("Ship a dark theme (it is also cheap to build and highly visible to users).", "Design / Engineering"),
    "Data Export": ("Add one-click export of reports to CSV and Excel.", "Engineering"),
    "Language Support": ("Add regional language support, starting with the most requested language.", "Product / Localisation"),
    "Wishlist & Saved Items": ("Add a wishlist / save-for-later feature to the product and cart pages.", "Product"),
    "Offline Mode": ("Cache key content so the app stays usable without a network connection.", "Engineering"),
    "Voice Features": ("Prototype voice search to test demand before investing further.", "Product / Engineering"),
}
DEFAULT_ACTION = ("Review these comments manually to find the root cause and decide on an owner.", "Product")


def _priority_label(score):
    return "High" if score >= 60 else "Medium" if score >= 30 else "Low"


def priority_issues(df, days=30):
    """Rank problems. Score = how often * how negative * how recent."""
    prob = problems(df)
    prob = prob[prob["topic"] != "General"] if not prob.empty else prob
    if prob.empty:
        return pd.DataFrame()
    recent_start = df["feedback_date"].max() - pd.Timedelta(days=days)
    rows = []
    for topic, grp in prob.groupby("topic"):
        mentions = len(grp)
        negativity = float(np.clip(-grp["polarity"], 0, 1).mean())
        recent = int((grp["feedback_date"] > recent_start).sum())
        raw = mentions * (0.5 + negativity) * (1 + 0.5 * recent / mentions)
        worst = grp.sort_values("polarity").iloc[0]["feedback_text"]
        action, owner = ACTIONS.get(topic, DEFAULT_ACTION)
        rows.append({"topic": topic, "mentions": mentions, "recent_mentions": recent,
                     "avg_negativity": round(negativity, 2), "raw": raw,
                     "example": worst, "recommendation": action, "owner": owner})
    out = pd.DataFrame(rows)
    out["score"] = (100 * out["raw"] / out["raw"].max()).round(0).astype(int)
    out["priority"] = out["score"].map(_priority_label)
    out["share_pct"] = (100 * out["mentions"] / out["mentions"].sum()).round(1)
    out = out.sort_values("score", ascending=False).drop(columns="raw").reset_index(drop=True)
    out.insert(0, "rank", range(1, len(out) + 1))
    return out


def feature_requests(df, days=30):
    """Most requested features, ranked by number of requests."""
    if df.empty:
        return pd.DataFrame()
    req = df[df["category"] == "Feature Requests"]
    if req.empty:
        return pd.DataFrame()
    recent_start = df["feedback_date"].max() - pd.Timedelta(days=days)
    rows = []
    for topic, grp in req.groupby("topic"):
        action, owner = ACTIONS.get(topic, ("Evaluate this request with the product team.", "Product"))
        rows.append({"feature": topic if topic != "General" else "Other requests",
                     "requests": len(grp),
                     "recent_requests": int((grp["feedback_date"] > recent_start).sum()),
                     "example": grp.iloc[0]["feedback_text"],
                     "recommendation": action, "owner": owner})
    out = pd.DataFrame(rows).sort_values(["requests", "recent_requests"], ascending=False).reset_index(drop=True)
    out.insert(0, "rank", range(1, len(out) + 1))
    return out


def key_insights(df, days=30):
    """A few plain-English headlines for the home page."""
    from modules.trends import compare_periods, emerging_concerns

    insights = []
    issues = priority_issues(df, days)
    if not issues.empty:
        top = issues.iloc[0]
        insights.append(f"Top customer problem: **{top['topic']}** ({top['mentions']} reports, "
                        f"{top['share_pct']}% of all problems). {top['recommendation']}")
    emerging = emerging_concerns(df, days)
    if not emerging.empty:
        hot = emerging[emerging["status"].isin(["New concern", "Rising"])]
        if not hot.empty:
            names = ", ".join(hot["topic"].head(3))
            insights.append(f"Emerging concerns in the last {days} days: **{names}**.")
    comp = compare_periods(df, days)
    if comp and comp["delta"] is not None:
        sign = "+" if comp["delta"] > 0 else ""
        insights.append(f"Customer sentiment is **{comp['direction'].lower()}** "
                        f"({sign}{comp['delta']} average score vs the previous {days} days).")
    feats = feature_requests(df, days)
    if not feats.empty:
        insights.append(f"Most requested feature: **{feats.iloc[0]['feature']}** "
                        f"({feats.iloc[0]['requests']} requests).")
    return insights
