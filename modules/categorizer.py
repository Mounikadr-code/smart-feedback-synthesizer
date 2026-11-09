"""Rule-based categorisation and topic detection (no paid APIs, no training needed).

Category = the TYPE of feedback (bug, feature request, complaint ...).
Topic    = WHAT the feedback is about (payments, login, delivery ...).
Topics are what let the app spot repeated complaints and emerging concerns.
"""
import re

CATEGORIES = [
    "Technical Issues",
    "Product Improvements",
    "Complaints",
    "Feature Requests",
    "Positive Feedback",
    "General Feedback",
]

# ---- topics (regex fragments, matched at the start of a word) ----------------
TOPIC_KEYWORDS = {
    "App Crashes & Freezing": [r"crash", r"freez", r"force close", r"app (?:is )?not responding", r"\bhangs?\b"],
    "Slow Performance": [r"slow", r"lag(?:gy|ging|s)?\b", r"takes forever", r"takes too long",
                         r"sluggish", r"loading", r"performance"],
    "Login & Account Problems": [r"login", r"log in", r"sign in", r"signin", r"password", r"\botp\b",
                                 r"verification", r"account"],
    "Payment & Billing Issues": [r"payment", r"transaction", r"deducted", r"charged", r"refund",
                                 r"billing", r"gateway"],
    "Delivery & Shipping": [r"deliver", r"shipping", r"shipped", r"arrived", r"courier", r"tracking",
                            r"damaged", r"late\b", r"delayed"],
    "Customer Support": [r"customer (?:support|service|care)", r"support team", r"support staff",
                         r"helpline", r"agent", r"representative", r"chat\b", r"repl(?:y|ied)"],
    "Pricing & Charges": [r"price", r"pricing", r"expensive", r"overpriced", r"costly", r"subscription",
                          r"charges", r"fees?\b", r"too high"],
    "Notifications": [r"notification", r"\balerts?\b"],
    "UI & Usability": [r"design", r"interface", r"\bui\b", r"\bux\b", r"layout", r"navigation",
                       r"menu", r"confusing", r"easy to use", r"simpl", r"clean"],
    "Search & Discovery": [r"search", r"filter", r"recommendation"],
    "Dark Mode / Themes": [r"dark mode", r"dark theme", r"theme"],
    "Data Export": [r"export", r"\bcsv\b", r"excel", r"\bpdf\b"],
    "Language Support": [r"language", r"hindi", r"regional", r"translat", r"multilingual"],
    "Wishlist & Saved Items": [r"wishlist", r"save for later", r"save items", r"favou?rites?"],
    "Offline Mode": [r"offline"],
    "Voice Features": [r"\bvoice\b"],
    "Product Quality": [r"quality", r"defective", r"\bbroke\b", r"durable", r"build"],
    "Onboarding & Help": [r"tutorial", r"onboarding", r"\bguide\b", r"help center", r"documentation"],
}
_TOPIC_PATTERNS = {
    topic: [re.compile(r"\b" + kw if not kw.startswith(r"\b") else kw, re.IGNORECASE) for kw in kws]
    for topic, kws in TOPIC_KEYWORDS.items()
}

# ---- category rules ------------------------------------------------------------
_FEATURE_RE = re.compile(
    r"\b(?:please|kindly)\s+(?:add|include|introduce|provide|support|bring)\b"
    r"|\b(?:add|include|introduce)\b.*\b(?:feature|option|mode|support)\b"
    r"|\bwish\b|\bwould (?:love|like|be great|be nice|be helpful)\b"
    r"|\b(?:need|want)\b.*\b(?:feature|option|mode|support)\b"
    r"|\bfeature request\b|\bit would be (?:great|nice|good|helpful)\b"
    r"|\bcan you (?:add|include)\b|\bhope you (?:add|include)\b|\bshould have\b",
    re.IGNORECASE,
)
_BUG_RE = re.compile(
    r"\bcrash|\bbugs?\b|\bbuggy\b|\berrors?\b|\bglitch|\bfreez|\bnot working\b|\bdoesn'?t work\b"
    r"|\bdoes not work\b|\bstopped working\b|\bfail(?:s|ed|ing|ure)?\b|\bbroken\b|\bnot loading\b"
    r"|\bcannot log\b|\bcan'?t log\b|\bunable to (?:log|sign)\b|\botp\b.*\b(?:never|not)\b",
    re.IGNORECASE,
)
_TECH_TOPICS = {"App Crashes & Freezing", "Slow Performance", "Login & Account Problems"}
_SUGGESTION_RE = re.compile(
    r"\bcould be (?:better|improved|simpler|cleaner|easier|more|faster)\b"
    r"|\bshould be\b|\bshould (?:improve|make|redesign|show|allow)\b|\bimprov(?:e|ement)\b"
    r"|\bsuggest|\bwould help\b|\bneeds? (?:to be|better|more|improv)\b|\bredesign|\bbetter\b",
    re.IGNORECASE,
)
_COMPLAINT_RE = re.compile(
    r"\brude\b|\bdisappoint|\bdelayed?\b|\blate\b|\bdamaged\b|\boverpriced\b|\brefund\b"
    r"|\bnever replied\b|\bunhelpful\b|\bterrible\b|\bworst\b|\bhidden charges\b|\bunacceptable\b",
    re.IGNORECASE,
)


def assign_topic(text):
    """Pick the topic with the most keyword hits ('General' if none match)."""
    best_topic, best_hits = "General", 0
    for topic, patterns in _TOPIC_PATTERNS.items():
        hits = sum(1 for p in patterns if p.search(text))
        if hits > best_hits:           # ties keep the earlier topic in the list
            best_topic, best_hits = topic, hits
    return best_topic


def categorize(text, sentiment, topic):
    """Decide the feedback category. The order of the checks matters."""
    if _FEATURE_RE.search(text):
        return "Feature Requests"
    if _BUG_RE.search(text) or topic in _TECH_TOPICS:
        if sentiment != "Positive" or _BUG_RE.search(text):
            return "Technical Issues"
    if _SUGGESTION_RE.search(text) and sentiment != "Positive":
        return "Product Improvements"
    if sentiment == "Positive":
        return "Positive Feedback"
    if sentiment == "Negative" or _COMPLAINT_RE.search(text):
        return "Complaints"
    return "General Feedback"
