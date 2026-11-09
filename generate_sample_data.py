"""Creates two realistic sample files so the demo works out of the box.

    data/sample_feedback_part1.csv   (Jun - Aug 2026)  -> upload this first
    data/sample_feedback_part2.csv   (Sep - Nov 2026)  -> upload this second

The data is deliberately messy (duplicates, blanks, extra spaces, emojis) and
contains planted trends so the dashboard has something interesting to show:
  * "App Crashes" and "Payment Failures" grow strongly in part 2 (emerging concerns)
  * "Delivery Delays" were common in part 1 and improve in part 2
  * "Dark Mode" and "Data Export" feature requests keep coming
  * Overall sentiment dips in part 2

Run:  python generate_sample_data.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

OUT_DIR = Path(__file__).resolve().parent / "data"
SOURCES = ["Google Reviews", "Twitter", "Email", "Feedback Form", "Support Chat"]

TEMPLATES = {
    "crash": [
        "The app keeps crashing whenever I open the cart",
        "App crashes every time I try to upload a photo",
        "Constant crashes after the latest update, very frustrating",
        "It freezes and crashes on my Android phone",
        "App closes by itself, crashed three times today",
    ],
    "slow": [
        "The app is so slow, pages take forever to load",
        "Very laggy and slow performance since last week",
        "Checkout takes too long to load",
    ],
    "login": [
        "I cannot log in, the OTP never arrives",
        "Login keeps failing with an error message",
        "Unable to sign in, password reset link does not work",
    ],
    "payment": [
        "Payment failed twice but money was deducted",
        "Payment gateway error at checkout, terrible experience",
        "Transaction failed and no refund yet",
        "Payment keeps failing on UPI, please fix this",
    ],
    "delivery": [
        "Delivery was late by three days",
        "My order arrived damaged and very delayed",
        "Shipping is too slow and no tracking updates",
    ],
    "support": [
        "Customer support never replied to my email",
        "Support team was rude and unhelpful",
        "Waited 40 minutes in chat and nobody helped",
    ],
    "pricing": [
        "Prices are too high compared to competitors",
        "Subscription is overpriced for what you get",
        "Hidden charges at checkout, very disappointed",
    ],
    "notif": [
        "Too many notifications, it is annoying",
        "Notifications stopped working after the update",
    ],
    "dark": [
        "Please add a dark mode, the white screen hurts at night",
        "Would love a dark theme option",
    ],
    "export": [
        "Please add an option to export reports to Excel",
        "I wish I could export my data as CSV",
    ],
    "language": [
        "Please add Hindi language support",
        "Need regional language support in the app",
    ],
    "wishlist": ["Add a wishlist feature so I can save items for later"],
    "voice": ["It would be great to have a voice search feature"],
    "offline": ["Please add offline mode, I travel a lot"],
    "ui": [
        "The checkout page could be simpler and cleaner",
        "The menu layout is confusing, should be redesigned",
        "Better navigation would improve the app a lot",
    ],
    "search": ["Search results should be more accurate, could be improved"],
    "onboarding": ["A tutorial for new users would help, the app needs better onboarding"],
    "positive": [
        "Love the new design, super easy to use",
        "Excellent customer service, quick response",
        "Great app, fast delivery and good quality",
        "Amazing experience, highly recommend",
        "Very happy with the product quality",
        "The latest update is fantastic and smooth",
        "Best shopping app I have used, really reliable",
    ],
    "neutral": [
        "I received the order on Tuesday",
        "Used the app for the first time today",
        "The product is okay, nothing special",
        "Average experience overall",
    ],
}

# relative weights per period: part 1 -> part 2
WEIGHTS_P1 = {"crash": 3, "slow": 4, "login": 3, "payment": 2, "delivery": 9, "support": 5,
              "pricing": 4, "notif": 3, "dark": 4, "export": 3, "language": 2, "wishlist": 2,
              "voice": 1, "offline": 2, "ui": 5, "search": 3, "onboarding": 2,
              "positive": 24, "neutral": 8}
WEIGHTS_P2 = {"crash": 14, "slow": 5, "login": 4, "payment": 11, "delivery": 3, "support": 5,
              "pricing": 4, "notif": 3, "dark": 6, "export": 5, "language": 2, "wishlist": 2,
              "voice": 2, "offline": 2, "ui": 4, "search": 3, "onboarding": 2,
              "positive": 16, "neutral": 7}


def make_part(start, end, n_rows, weights, seed):
    rng = np.random.default_rng(seed)
    keys = list(weights)
    probs = np.array([weights[k] for k in keys], dtype=float)
    probs /= probs.sum()
    days = (pd.Timestamp(end) - pd.Timestamp(start)).days
    rows = []
    for _ in range(n_rows):
        key = rng.choice(keys, p=probs)
        text = str(rng.choice(TEMPLATES[key]))
        if rng.random() < 0.25:                      # small variations so rows are not identical
            text += str(rng.choice([" !!", " honestly", " please fix", " thanks", " :("]))
        date = pd.Timestamp(start) + pd.Timedelta(days=int(rng.integers(0, days + 1)))
        rows.append({"date": date.strftime("%Y-%m-%d"), "source": str(rng.choice(SOURCES)), "feedback": text})
    df = pd.DataFrame(rows)

    # --- make it messy on purpose, to demonstrate the cleaning step ---
    dupes = df.sample(8, random_state=seed)
    df = pd.concat([df, dupes], ignore_index=True)                     # exact duplicates
    df.loc[df.sample(4, random_state=seed + 1).index, "feedback"] = np.nan   # missing text
    df.loc[df.sample(5, random_state=seed + 2).index, "source"] = np.nan     # missing source
    df.loc[df.sample(3, random_state=seed + 3).index, "date"] = "not available"  # bad date
    idx = df.sample(10, random_state=seed + 4).index
    df.loc[idx, "feedback"] = "   " + df.loc[idx, "feedback"].fillna("") + "   \U0001F621 #fail @company  "
    return df.sample(frac=1, random_state=seed + 5).reset_index(drop=True)


if __name__ == "__main__":
    OUT_DIR.mkdir(exist_ok=True)
    part1 = make_part("2026-06-01", "2026-08-31", 190, WEIGHTS_P1, seed=11)
    part2 = make_part("2026-09-01", "2026-11-08", 170, WEIGHTS_P2, seed=22)
    part1.to_csv(OUT_DIR / "sample_feedback_part1.csv", index=False)
    part2.to_csv(OUT_DIR / "sample_feedback_part2.csv", index=False)
    print(f"Created {len(part1)} rows (part 1) and {len(part2)} rows (part 2) in {OUT_DIR}")
