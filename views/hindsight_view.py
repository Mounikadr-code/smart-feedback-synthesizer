"""Hindsight Memory page: connect, retain (sync), recall and reflect."""
import streamlit as st

from modules import database
from modules.hindsight_memory import CLOUD_URL, LOCAL_URL, SDK_INSTALLED
from views import ui

SETUP = f"""
**Option A - run Hindsight locally (Docker)**
```bash
export OPENAI_API_KEY=sk-xxx          # or another supported LLM provider key
docker run -it --pull always --name hindsight --restart unless-stopped -p 8888:8888 -p 9999:9999 \\
  -e HINDSIGHT_API_LLM_API_KEY=$OPENAI_API_KEY \\
  -v hindsight-data:/home/hindsight/.pg0 \\
  ghcr.io/vectorize-io/hindsight:latest
```
Then use base URL `{LOCAL_URL}` below. (The Hindsight UI runs on port 9999.)

**Option B - Hindsight Cloud**
Sign up at https://ui.hindsight.vectorize.io, create an API key and use base URL `{CLOUD_URL}`.

**Install the Python client in this project's environment**
```bash
pip install hindsight-client
```
You can also set `HINDSIGHT_BASE_URL`, `HINDSIGHT_API_KEY` and `HINDSIGHT_BANK_ID` as environment variables
before running `streamlit run app.py`.
"""


def render(df, df_all):
    ui.header("🧠 Hindsight Memory",
              "Long-term agent memory: retain customer feedback, then recall similar past feedback and reason over it.")
    ui.show_flash()
    memory = ui.get_memory()

    if memory.live:
        st.success(f"✅ {memory.message}")
    else:
        st.warning(f"⚠️ {memory.message}  \nUntil Hindsight is connected, recall uses a **local keyword-match demo** "
                   "over the SQLite table. That demo is **not** Hindsight memory.")
        if not SDK_INSTALLED:
            st.caption("SDK status: `hindsight-client` is not installed in this environment.")

    with st.expander("⚙️ Connection settings", expanded=not memory.live):
        c1, c2, c3 = st.columns(3)
        base_url = c1.text_input("Base URL", value=memory.base_url or LOCAL_URL,
                                 help=f"Local: {LOCAL_URL}   |   Cloud: {CLOUD_URL}")
        api_key = c2.text_input("API key (Cloud)", value=memory.api_key, type="password")
        bank_id = c3.text_input("Memory bank ID", value=memory.bank_id)
        if st.button("🔌 Connect and test", type="primary"):
            memory.base_url, memory.api_key, memory.bank_id = base_url.strip(), api_key.strip(), bank_id.strip()
            ok, msg = memory.connect()
            (st.success if ok else st.error)(msg)
            if ok:
                st.rerun()
        st.caption("The API key is kept only in this browser session and is never written to the database.")
    with st.expander("📘 How to set up real Hindsight"):
        st.markdown(SETUP)

    st.subheader("1. Retain - send feedback to Hindsight")
    pending = database.count_unsynced()
    total = len(df_all)
    st.write(f"**{total - pending:,}** of **{total:,}** stored feedback have been sent to Hindsight. "
             "Hindsight extracts facts from each item with an LLM, so large syncs take time and may cost LLM credits.")
    batch = st.slider("Items to send per click", 5, 100, 25, 5)
    if st.button(f"📤 Send next {min(batch, pending)} feedback to Hindsight", disabled=(not memory.live or pending == 0)):
        rows = database.get_unsynced(batch)
        with st.spinner("Retaining feedback in Hindsight..."):
            sent, errors = memory.retain_feedback(rows)
        database.mark_synced(sent)
        if sent:
            ui.set_flash("success", f"Sent {len(sent)} feedback to Hindsight.")
        for err in errors:
            ui.set_flash("error", err)
        st.rerun()
    if not memory.live:
        st.caption("Retain is disabled in demo mode - nothing is sent anywhere.")

    st.subheader("2. Recall - find similar earlier feedback")
    query = st.text_input("Describe a complaint", placeholder="e.g. payment keeps failing at checkout")
    if st.button("🔎 Recall similar feedback") and query.strip():
        result = memory.recall_similar(query, local_df=df_all, k=6)
        st.markdown(f"**Source: {result['mode']}**")
        if result["error"]:
            st.error(f"Recall failed: {result['error']}")
        elif not result["items"]:
            st.info("Nothing similar found.")
        else:
            for item in result["items"]:
                st.markdown(f"- {item['text']}  \n  <small>{item['detail']}</small>", unsafe_allow_html=True)

    st.subheader("3. Reflect - ask Hindsight a question")
    question = st.text_input("Question", value="What do customers repeatedly complain about, and is it getting worse?")
    if st.button("💭 Reflect", disabled=not memory.live):
        with st.spinner("Hindsight is reasoning over its memories..."):
            answer, error = memory.reflect(question)
        if error:
            st.error(error)
        else:
            st.markdown(answer)
    if not memory.live:
        st.caption("Reflect needs a live Hindsight connection. It is not simulated in demo mode.")
