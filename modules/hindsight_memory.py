"""Hindsight agent-memory integration.

Real mode  : uses the official `hindsight-client` SDK (pip install hindsight-client)
             -> client.retain(...), client.recall(...), client.reflect(...)
Demo mode  : used when the SDK is not installed, no server/key is configured, or the
             connection test fails. It is ALWAYS labelled as demo in the UI.
             Demo recall is a plain local keyword match on the SQLite table. It is
             NOT Hindsight and is never presented as such.

Configuration (environment variables or the Hindsight page in the app):
    HINDSIGHT_BASE_URL   e.g. http://localhost:8888  (self-hosted)  or  https://api.hindsight.vectorize.io (Cloud)
    HINDSIGHT_API_KEY    required for Hindsight Cloud, usually not for a local server
    HINDSIGHT_BANK_ID    memory bank name (default: feedback-synthesizer)
"""
import os
import re

import pandas as pd

try:
    from hindsight_client import Hindsight
    SDK_INSTALLED = True
except Exception:
    Hindsight = None
    SDK_INSTALLED = False

DEFAULT_BANK = "feedback-synthesizer"
CLOUD_URL = "https://api.hindsight.vectorize.io"
LOCAL_URL = "http://localhost:8888"

_STOP = set("the a an and or but is are was were be to of in on at for with it its my i we you this that "
            "so very too not no have has had app please add".split())


def _tokens(text):
    return {t for t in re.findall(r"[a-z']+", str(text).lower()) if t not in _STOP and len(t) > 2}


class HindsightMemory:
    """Thin wrapper that hides whether we are talking to real Hindsight or in demo mode."""

    def __init__(self, base_url=None, api_key=None, bank_id=None):
        self.base_url = base_url or os.environ.get("HINDSIGHT_BASE_URL", "")
        self.api_key = api_key or os.environ.get("HINDSIGHT_API_KEY", "")
        self.bank_id = bank_id or os.environ.get("HINDSIGHT_BANK_ID", DEFAULT_BANK)
        self.client = None
        self.live = False          # True ONLY after a successful connection test
        self.message = self._initial_message()

    # ---- status ---------------------------------------------------------------
    def _initial_message(self):
        if not SDK_INSTALLED:
            return "DEMO MODE: the `hindsight-client` package is not installed."
        if not (self.base_url or self.api_key):
            return "DEMO MODE: no Hindsight server or API key configured yet."
        return "Configured but not tested yet. Click 'Connect and test'."

    @property
    def mode_label(self):
        return "LIVE - Hindsight" if self.live else "DEMO MODE - not Hindsight"

    # ---- connection -------------------------------------------------------------
    def connect(self):
        """Try to connect and run a real recall. Returns (ok, message)."""
        self.close()
        self.live = False
        if not SDK_INSTALLED:
            self.message = "DEMO MODE: install the SDK with `pip install hindsight-client`."
            return False, self.message
        if not (self.base_url or self.api_key):
            self.message = "DEMO MODE: enter a Hindsight base URL (and API key for Cloud)."
            return False, self.message
        url = self.base_url or CLOUD_URL
        try:
            kwargs = {"base_url": url, "timeout": 60.0}
            if self.api_key:
                kwargs["api_key"] = self.api_key
            client = Hindsight(**kwargs)
            try:                                   # the bank may already exist - that is fine
                client.create_bank(bank_id=self.bank_id, name="Customer Feedback")
            except Exception:
                pass
            client.recall(bank_id=self.bank_id, query="customer feedback")   # real round-trip
        except Exception as exc:
            self.message = f"DEMO MODE: could not reach Hindsight at {url} ({type(exc).__name__}: {exc})"
            return False, self.message
        self.client, self.live = client, True
        self.message = f"LIVE: connected to Hindsight at {url} (bank '{self.bank_id}')."
        return True, self.message

    def close(self):
        if self.client is not None:
            try:
                self.client.close()
            except Exception:
                pass
        self.client = None

    # ---- retain -------------------------------------------------------------------
    def retain_feedback(self, rows):
        """Send feedback rows to Hindsight. Returns (sent_ids, errors). Live mode only."""
        if not self.live:
            return [], ["Not connected to Hindsight (demo mode) - nothing was sent."]
        sent, errors = [], []
        for r in rows.itertuples(index=False):
            content = (f"Customer feedback received on {pd.Timestamp(r.feedback_date):%Y-%m-%d} "
                       f"via {r.source}: {r.feedback_text}")
            context = (f"customer feedback; category: {r.category}; topic: {r.topic}; "
                       f"sentiment: {r.sentiment}")
            try:
                self.client.retain(bank_id=self.bank_id, content=content, context=context,
                                   timestamp=pd.Timestamp(r.feedback_date).to_pydatetime())
                sent.append(int(r.id))
            except Exception as exc:
                errors.append(f"Row {r.id}: {type(exc).__name__}: {exc}")
                if len(errors) >= 3:               # stop early on repeated failures
                    break
        return sent, errors

    # ---- recall -------------------------------------------------------------------
    def recall_similar(self, query, local_df=None, k=5):
        """Return {'mode': ..., 'items': [{'text':..., 'detail':...}], 'error': str|None}."""
        query = str(query or "").strip()
        if not query:
            return {"mode": self.mode_label, "items": [], "error": None}
        if self.live:
            try:
                result = self.client.recall(bank_id=self.bank_id, query=query)
                items = [{"text": m.text, "detail": str(getattr(m, "type", "") or "memory")}
                         for m in (result.results or [])[:k]]
                return {"mode": self.mode_label, "items": items, "error": None}
            except Exception as exc:
                return {"mode": self.mode_label, "items": [], "error": f"{type(exc).__name__}: {exc}"}
        return {"mode": self.mode_label, "items": self._demo_recall(query, local_df, k), "error": None}

    @staticmethod
    def _demo_recall(query, local_df, k):
        """DEMO ONLY: word-overlap search over locally stored feedback."""
        if local_df is None or local_df.empty:
            return []
        q = _tokens(query)
        if not q:
            return []
        scored = []
        for row in local_df.itertuples(index=False):
            t = _tokens(row.feedback_text)
            overlap = len(q & t)
            if overlap:
                scored.append((overlap / len(q | t), row))
        scored.sort(key=lambda x: x[0], reverse=True)
        seen, items = set(), []
        for score, row in scored:
            key = row.feedback_text.lower()
            if key in seen:
                continue
            seen.add(key)
            items.append({"text": row.feedback_text,
                          "detail": f"{pd.Timestamp(row.feedback_date):%d %b %Y} | {row.source} | {row.topic} | match {score:.0%}"})
            if len(items) >= k:
                break
        return items

    # ---- reflect ------------------------------------------------------------------
    def reflect(self, question):
        """Ask Hindsight to reason over its memories. Returns (answer, error)."""
        if not self.live:
            return None, "Reflect needs a live Hindsight connection (it is not available in demo mode)."
        try:
            response = self.client.reflect(bank_id=self.bank_id, query=question)
            return response.text, None
        except Exception as exc:
            return None, f"{type(exc).__name__}: {exc}"
