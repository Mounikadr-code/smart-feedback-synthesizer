"""Sentiment analysis (free, offline).

Two engines work together:
  1. A built-in word list tuned for customer feedback (handles "not good",
     "very slow", "takes forever", ...). Always available.
  2. TextBlob, if it is installed. Its score is blended with the word list.

If TextBlob is missing the app still works - it just uses engine 1.
"""
import math
import re

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except Exception:  # not installed or corpora missing
    TEXTBLOB_AVAILABLE = False

POSITIVE_THRESHOLD = 0.10
NEGATIVE_THRESHOLD = -0.10

LEXICON = {
    # positive
    "love": 3.0, "loved": 3.0, "loving": 2.5, "great": 3.0, "good": 1.9, "excellent": 3.2,
    "amazing": 3.2, "awesome": 3.1, "fantastic": 3.2, "wonderful": 3.0, "happy": 2.7,
    "satisfied": 2.0, "easy": 1.8, "smooth": 2.0, "fast": 1.6, "quick": 1.6, "quickly": 1.5,
    "helpful": 2.0, "friendly": 2.0, "best": 3.0, "perfect": 3.0, "nice": 1.8,
    "recommend": 1.8, "recommended": 1.8, "impressive": 2.5, "reliable": 2.0,
    "intuitive": 2.0, "useful": 2.0, "convenient": 2.0, "enjoy": 2.2, "enjoyed": 2.2,
    "pleased": 2.2, "superb": 3.2, "brilliant": 3.0, "responsive": 1.8, "seamless": 2.2,
    "delighted": 3.0, "thanks": 1.5, "thank": 1.5, "worth": 1.5, "fabulous": 3.0,
    # negative
    "bad": -2.5, "terrible": -3.2, "awful": -3.2, "horrible": -3.2, "worst": -3.4,
    "poor": -2.2, "slow": -1.8, "laggy": -2.0, "lag": -1.5, "sluggish": -2.0,
    "crash": -2.5, "crashes": -2.5, "crashing": -2.5, "crashed": -2.5,
    "bug": -2.0, "bugs": -2.0, "buggy": -2.2, "glitch": -1.8, "glitches": -1.8,
    "error": -1.8, "errors": -1.8, "fail": -2.3, "failed": -2.3, "fails": -2.3,
    "failing": -2.3, "failure": -2.3, "broken": -2.5, "useless": -2.8,
    "frustrating": -2.7, "frustrated": -2.5, "annoying": -2.2, "annoyed": -2.0,
    "irritating": -2.2, "disappointed": -2.5, "disappointing": -2.5, "disappointment": -2.5,
    "rude": -2.6, "unhelpful": -2.4, "late": -1.6, "delayed": -2.0, "delay": -1.6,
    "damaged": -2.5, "defective": -2.8, "expensive": -1.8, "overpriced": -2.4,
    "confusing": -1.8, "complicated": -1.5, "difficult": -1.5, "unable": -1.5,
    "freeze": -2.0, "freezes": -2.0, "freezing": -2.0, "stuck": -1.8, "ignored": -2.0,
    "waste": -2.2, "scam": -3.5, "refund": -0.8, "deducted": -1.5, "hidden": -1.5,
    "problem": -1.8, "problems": -1.8, "issue": -1.5, "issues": -1.5, "worse": -2.5,
    "unreliable": -2.4, "missing": -1.2, "wrong": -1.8, "nobody": -1.2, "waited": -1.0,
    "lost": -1.8, "dislike": -2.0, "hate": -3.0, "hated": -3.0, "pathetic": -3.0,
    "ridiculous": -2.2, "unacceptable": -2.8, "mess": -2.0, "poorly": -2.2,
}

# multi-word expressions are checked first and removed from the text
PHRASES = {
    "cannot log": -2.2, "can't log": -2.2, "cant log": -2.2, "unable to log": -2.2,
    "unable to sign": -2.2, "never arrive": -2.0, "not arrive": -1.8, "not received": -1.8,
    "not working": -2.2, "doesn't work": -2.2, "does not work": -2.2, "stopped working": -2.4,
    "not loading": -2.0, "too long": -1.5, "too high": -1.5, "takes forever": -2.2,
    "waste of": -2.5, "no refund": -2.0, "never replied": -2.4, "no response": -2.0,
    "not responding": -2.0, "nothing special": -0.5, "hidden charges": -2.2,
    "too many": -1.2, "nobody helped": -2.0, "keeps failing": -2.0,
}

NEGATIONS = {"not", "no", "never", "don't", "dont", "doesn't", "doesnt", "didn't", "didnt",
             "isn't", "isnt", "wasn't", "wasnt", "can't", "cant", "cannot", "won't", "wont",
             "hardly", "without"}
BOOSTERS = {"very": 1.3, "extremely": 1.5, "really": 1.3, "so": 1.2, "super": 1.3,
            "absolutely": 1.5, "totally": 1.3, "incredibly": 1.5, "too": 1.2,
            "slightly": 0.7, "somewhat": 0.7, "bit": 0.7}

_TOKEN_RE = re.compile(r"[a-z']+")


def _lexicon_polarity(text):
    """Score text in the range -1 .. +1 using the built-in word list."""
    lowered = text.lower().replace("’", "'")
    total = 0.0
    for phrase, score in PHRASES.items():
        if phrase in lowered:
            total += score
            lowered = lowered.replace(phrase, " ")
    tokens = _TOKEN_RE.findall(lowered)
    for i, tok in enumerate(tokens):
        score = LEXICON.get(tok)
        if score is None:
            continue
        for prev in tokens[max(0, i - 2):i]:          # booster just before the word
            if prev in BOOSTERS:
                score *= BOOSTERS[prev]
        if any(prev in NEGATIONS for prev in tokens[max(0, i - 3):i]):
            score *= -0.74                              # "not good" -> negative
        total += score
    return total / math.sqrt(total * total + 15)       # squash into -1 .. +1


def get_polarity(text):
    """Return a polarity score between -1 (very negative) and +1 (very positive)."""
    text = str(text or "")
    lex = _lexicon_polarity(text)
    if TEXTBLOB_AVAILABLE:
        try:
            blob = TextBlob(text).sentiment.polarity
            return round(blob if lex == 0 else 0.7 * lex + 0.3 * blob, 4)
        except Exception:
            pass
    return round(lex, 4)


def label_from_polarity(polarity):
    if polarity >= POSITIVE_THRESHOLD:
        return "Positive"
    if polarity <= NEGATIVE_THRESHOLD:
        return "Negative"
    return "Neutral"


def analyze_sentiment(text):
    polarity = get_polarity(text)
    return label_from_polarity(polarity), polarity


def sentiment_percentages(df):
    """Return {'Positive': %, 'Negative': %, 'Neutral': %} for a DataFrame."""
    if df.empty:
        return {"Positive": 0.0, "Negative": 0.0, "Neutral": 0.0}
    counts = df["sentiment"].value_counts()
    return {k: round(100 * counts.get(k, 0) / len(df), 1) for k in ("Positive", "Negative", "Neutral")}


def satisfaction_score(pos_pct, neg_pct):
    """0-100 score: 50 = balanced, 100 = everyone positive, 0 = everyone negative."""
    return round((pos_pct - neg_pct + 100) / 2, 1)


def satisfaction_level(pos_pct, neg_pct):
    """Human-friendly satisfaction label based on net sentiment (positive% - negative%)."""
    net = pos_pct - neg_pct
    if net >= 40:
        return "Highly Satisfied"
    if net >= 10:
        return "Satisfied"
    if net > -10:
        return "Mixed"
    if net > -40:
        return "Dissatisfied"
    return "Highly Dissatisfied"
