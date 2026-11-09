"""Small shared UI helpers: styling, KPI cards, flash messages."""
import inspect

import streamlit as st

CSS = """
<style>
  .block-container {padding-top: 1.6rem; padding-bottom: 2rem; max-width: 1250px;}
  [data-testid="stSidebar"] {background: linear-gradient(180deg, #1e1b4b 0%, #312e81 100%);}
  [data-testid="stSidebar"] * {color: #e0e7ff;}
  [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {color: #ffffff;}
  .page-title {font-size: 1.9rem; font-weight: 800; color: #1e1b4b; margin-bottom: 0;}
  .page-sub {color: #64748b; margin-bottom: 1.1rem;}
  .kpi {background: #ffffff; border-radius: 14px; padding: 16px 18px; border: 1px solid #e2e8f0;
        border-left: 6px solid var(--c); box-shadow: 0 1px 3px rgba(15,23,42,.06);}
  .kpi .label {font-size: .78rem; text-transform: uppercase; letter-spacing: .06em; color: #64748b; font-weight: 600;}
  .kpi .value {font-size: 1.9rem; font-weight: 800; color: #0f172a; line-height: 1.2;}
  .kpi .sub {font-size: .8rem; color: #64748b;}
  .insight {background: #eef2ff; border-left: 5px solid #4f46e5; padding: 10px 14px;
            border-radius: 8px; margin-bottom: 8px; color: #1e1b4b;}
  .pill {display:inline-block; padding: 2px 10px; border-radius: 999px; font-size: .75rem; font-weight: 700; color: #fff;}
  .pill-High {background:#ef4444;} .pill-Medium {background:#f59e0b;} .pill-Low {background:#10b981;}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def header(title, subtitle=""):
    st.markdown(f'<div class="page-title">{title}</div><div class="page-sub">{subtitle}</div>',
                unsafe_allow_html=True)


def kpi(label, value, sub="", color="#4f46e5"):
    st.markdown(
        f'<div class="kpi" style="--c:{color}"><div class="label">{label}</div>'
        f'<div class="value">{value}</div><div class="sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )


def insight(text):
    st.markdown(f'<div class="insight">{text}</div>', unsafe_allow_html=True)


def pill(priority):
    return f'<span class="pill pill-{priority}">{priority} priority</span>'


def set_flash(kind, message):
    """Remember a message across st.rerun() so it can be shown after the page refreshes."""
    st.session_state.setdefault("flash", []).append((kind, message))


def show_flash():
    for kind, message in st.session_state.pop("flash", []):
        getattr(st, kind)(message)


def no_data_message():
    st.info("No feedback matches the current filters. Try widening the date range or sources "
            "in the sidebar, or upload more feedback.")


# Streamlit renamed "use_container_width" to width="stretch" in newer versions.
# These helpers work with both old and new releases.
_NEW_WIDTH_API = "width" in inspect.signature(st.dataframe).parameters


def chart(fig, key):
    """Show a Plotly chart at full width."""
    if "width" in inspect.signature(st.plotly_chart).parameters:
        st.plotly_chart(fig, width="stretch", key=key)
    else:
        st.plotly_chart(fig, use_container_width=True, key=key)


def table(df, **kwargs):
    """Show a DataFrame at full width without the index column."""
    if _NEW_WIDTH_API:
        st.dataframe(df, width="stretch", hide_index=True, **kwargs)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True, **kwargs)


def get_memory():
    """One Hindsight wrapper per browser session (keeps the connection between clicks)."""
    from modules.hindsight_memory import HindsightMemory
    if "hs_memory" not in st.session_state:
        st.session_state["hs_memory"] = HindsightMemory()
    return st.session_state["hs_memory"]
