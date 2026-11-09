# 💬 Smart User Feedback Synthesizer

Upload customer feedback (CSV / Excel / manual entry) → it is **cleaned**, **analysed** (sentiment, category, topic),
**stored permanently** in SQLite, compared with earlier feedback to find **repeated and emerging problems**, and
turned into **prioritised product recommendations** on a Streamlit dashboard. Optional **Hindsight** agent memory
is supported (see below). No paid APIs are needed for the core app.

## Folder structure

```
feedback_synthesizer/
├── app.py                      # Streamlit entry point: sidebar navigation + filters
├── requirements.txt
├── generate_sample_data.py     # (re)creates the two larger demo CSVs
├── .streamlit/config.toml      # theme
├── data/
│   ├── sample_feedback.csv         # 40 hand-written records (quick demo)
│   ├── sample_feedback_part1.csv   # Jun-Aug 2026, messy on purpose
│   ├── sample_feedback_part2.csv   # Sep-Nov 2026, with new problems
│   └── feedback.db                 # created on first run = the persistent memory
├── modules/                    # the "brain" (no Streamlit code here)
│   ├── database.py             # SQLite storage, duplicate protection, upload log
│   ├── cleaning.py             # file reading + data cleaning
│   ├── sentiment.py            # Positive / Negative / Neutral (+ TextBlob if installed)
│   ├── categorizer.py          # category + topic detection (rule-based)
│   ├── pipeline.py             # clean -> analyse -> save
│   ├── trends.py               # monthly trends, period comparison, repeated / emerging problems
│   ├── recommendations.py      # priority ranking + suggested improvements
│   ├── hindsight_memory.py     # Hindsight SDK wrapper (+ clearly labelled demo mode)
│   └── charts.py               # all Plotly charts
└── views/                      # one file per dashboard page
    ├── home.py  upload.py  cleaning_view.py  analysis.py
    ├── sentiment_view.py  hindsight_view.py  trends_view.py  recommendations_view.py
    └── ui.py                   # shared styling/helpers
```

## Install and run

Requires Python 3.9+.

```bash
cd feedback_synthesizer
python -m venv venv
# Windows:  venv\Scripts\activate        macOS/Linux:  source venv/bin/activate
pip install -r requirements.txt
python -m textblob.download_corpora      # optional, only if you want TextBlob (the app works without it)
streamlit run app.py
```

The app opens at http://localhost:8501.

## 5-minute demo script

1. **Home** → click **Quick sample (40 rows)** (or **Sample Part 1**). The dashboard fills with KPIs and charts.
2. **Data Cleaning** → before/after table, duplicates and blanks removed.
3. **Feedback Analysis / Sentiment Analysis** → categories, topics, satisfaction gauge.
4. **Upload Feedback → Data tools → Sample Part 2.** Part 1 is still remembered; open **Trend Analysis**:
   payment/login problems show up as *Rising*, sentiment turns *Declining*.
5. **Recommendations** → ranked problems with suggested fixes and owners.
6. Restart the app: the data is still there (`data/feedback.db`).

## How it works

| Step | What happens |
|---|---|
| Cleaning | trims spaces, strips URLs/HTML/emojis/special characters, fills missing source/date, drops empty text and duplicates (same text + source + date, also against what is already stored) |
| Sentiment | built-in word list tuned for customer feedback (handles "not good", "very slow", "takes forever"); blended with TextBlob when installed. Score −1…+1 → Positive ≥ 0.10, Negative ≤ −0.10, else Neutral |
| Category | Technical Issues · Complaints · Feature Requests · Product Improvements · Positive Feedback (+ General Feedback for neutral remarks), via keyword rules |
| Topic | what it is about (Payment, Login, Delivery, Dark mode …) – this is what makes repeated/emerging problems detectable |
| Trends | latest N days vs the N days before, anchored on the newest feedback date |
| Priority score | `mentions × (0.5 + negativity) × (1 + 0.5 × share that is recent)`, scaled to 0–100 |

## Hindsight memory (optional, real integration)

The **🧠 Hindsight Memory** page uses the official [`hindsight-client`](https://docs.hindsight.vectorize.io/python-sdk)
SDK: `retain()` stores feedback, `recall()` finds similar earlier feedback, `reflect()` answers questions over memory.

**The page shows LIVE only after a real connection test succeeds. Otherwise it shows DEMO MODE**, where recall is a
simple local keyword match on SQLite — labelled as *not Hindsight*. Retain and Reflect are disabled in demo mode.

To enable real Hindsight:

```bash
pip install hindsight-client

# Option A: run Hindsight locally (needs Docker and an LLM key)
export OPENAI_API_KEY=sk-xxx
docker run -it --pull always --name hindsight --restart unless-stopped -p 8888:8888 -p 9999:9999 \
  -e HINDSIGHT_API_LLM_API_KEY=$OPENAI_API_KEY \
  -v hindsight-data:/home/hindsight/.pg0 \
  ghcr.io/vectorize-io/hindsight:latest
# then in the app: Base URL = http://localhost:8888

# Option B: Hindsight Cloud – create an API key at https://ui.hindsight.vectorize.io
# then in the app: Base URL = https://api.hindsight.vectorize.io + your API key
```

Open **Hindsight Memory → Connection settings → Connect and test**. You can also set `HINDSIGHT_BASE_URL`,
`HINDSIGHT_API_KEY`, `HINDSIGHT_BANK_ID` before launching. Then click **Send next N feedback to Hindsight**.
When you add manual feedback, similar earlier feedback is recalled automatically.

## Input file format

Any CSV / Excel file with a text column named `feedback`, `review`, `comment` (or similar). Optional: `date`
(ISO `2026-10-05` or day-first `05/10/2026`), `source`. If the text column has another name, the longest text
column is used.

## Limitations (be honest in your demo)

* Sentiment and categories are rule-based, tuned for English — good for a prototype, not a production NLP model.
* Excel `.xls` needs `xlrd` (included in requirements).
* Hindsight needs its own server/key; it was **not** connected during development of this project.
