import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection
import base64, datetime, re

# ─────────────────────────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="入札 PoC Board",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────
#  SESSION STATE INIT
# ─────────────────────────────────────────────────────────────────
_defaults = {
    "logged_in": False,
    "current_page": "ダッシュボード",
    "search_words": [],
    "search_counts": {},
    "ocr_result": None,
    "costs": {
        "n_init": 0, "n_month": 0, "n_opt": 0,
        "k_init": 0, "k_month": 0, "k_opt": 0,
        "margin": 20, "win_rate": 20, "annual_bids": 50,
    },
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────────
#  GLOBAL CSS
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Google Fonts ────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ── Design Tokens ───────────────────────────────────────────── */
:root {
  /* Surface */
  --canvas:    #F0F2F7;
  --surface:   #FFFFFF;
  --surface-2: #F7F8FB;
  --surface-3: #EEF0F6;

  /* Sidebar */
  --sb:        #111827;
  --sb-2:      #1C2535;
  --sb-3:      #243044;
  --sb-line:   rgba(255,255,255,0.06);
  --sb-text:   #6B7FA8;
  --sb-active-bg: rgba(99,102,241,0.18);
  --sb-active-text: #A5B4FC;

  /* Typography */
  --ink:       #0F172A;
  --ink-2:     #334155;
  --ink-3:     #64748B;
  --ink-4:     #94A3B8;

  /* Border */
  --border:    #E2E8F0;
  --border-2:  #CBD5E1;

  /* Brand */
  --indigo:    #4F46E5;
  --indigo-2:  #6366F1;
  --indigo-lt: #EEF2FF;
  --indigo-md: #C7D2FE;

  /* Semantic */
  --emerald:   #059669;
  --emerald-lt:#D1FAE5;
  --rose:      #E11D48;
  --rose-lt:   #FFE4E6;
  --amber:     #D97706;
  --amber-lt:  #FEF3C7;
  --sky:       #0284C7;
  --sky-lt:    #E0F2FE;

  /* Radius */
  --r-sm:  6px;
  --r-md:  10px;
  --r-lg:  14px;
  --r-xl:  20px;

  /* Shadow */
  --shadow-sm: 0 1px 3px rgba(15,23,42,0.06), 0 1px 2px rgba(15,23,42,0.04);
  --shadow-md: 0 4px 16px rgba(15,23,42,0.08), 0 2px 4px rgba(15,23,42,0.04);
  --shadow-lg: 0 12px 32px rgba(15,23,42,0.10), 0 4px 8px rgba(15,23,42,0.06);
  --shadow-focus: 0 0 0 3px rgba(99,102,241,0.20);
}

/* ── Reset ───────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }

/* ── Base Typography ─────────────────────────────────────────── */
html, body, [class*="st-"], p, div, span, label,
input, textarea, select, button, table, th, td {
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont,
    'Hiragino Kaku Gothic ProN', 'Yu Gothic', sans-serif !important;
  color: var(--ink);
  -webkit-font-smoothing: antialiased;
}
h1,h2,h3,h4,h5 {
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont,
    'Hiragino Kaku Gothic ProN', 'Yu Gothic', sans-serif !important;
  font-weight: 700 !important;
  color: var(--ink);
  letter-spacing: -0.03em;
}

/* ── Hide Streamlit Chrome ───────────────────────────────────── */
[data-testid="stHeader"] { background: transparent !important; }
footer { display: none !important; }
[data-testid="stAppViewContainer"] { background: var(--canvas) !important; }
[data-testid="block-container"] {
  padding: 2rem 2.5rem 5rem !important;
  max-width: 1440px;
}

/* ── Sidebar ─────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: var(--sb) !important;
  border-right: none !important;
  box-shadow: 4px 0 24px rgba(0,0,0,0.12) !important;
}
[data-testid="stSidebar"] > div:first-child { padding-top: 0 !important; }
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div { color: var(--sb-text) !important; }

/* Nav radio */
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label > div:first-child {
  display: none !important;
}
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label {
  display: flex !important;
  align-items: center !important;
  padding: 10px 14px !important;
  margin: 1px 8px !important;
  border-radius: var(--r-md) !important;
  transition: background 0.15s, color 0.15s !important;
  cursor: pointer !important;
  background: transparent !important;
  border: none !important;
}
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover {
  background: var(--sb-3) !important;
}
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label[data-checked="true"] {
  background: var(--sb-active-bg) !important;
}
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label p {
  font-size: 13.5px !important;
  font-weight: 500 !important;
  color: #94A3B8 !important;
  margin: 0 !important;
  letter-spacing: -0.01em;
}
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label[data-checked="true"] p {
  color: var(--sb-active-text) !important;
  font-weight: 700 !important;
}

/* Toggle */
[data-testid="stSidebar"] .stToggle { padding: 0 8px !important; }
[data-testid="stSidebar"] .stToggle span { font-size: 12px !important; }

/* ── Main Buttons ─────────────────────────────────────────────── */
div.stButton > button,
div[data-testid="stFormSubmitButton"] > button {
  background: var(--indigo) !important;
  border: none !important;
  border-radius: var(--r-md) !important;
  padding: 0.6rem 1.4rem !important;
  font-weight: 600 !important;
  font-size: 13.5px !important;
  color: #FFF !important;
  letter-spacing: -0.01em !important;
  transition: background 0.18s, transform 0.15s, box-shadow 0.18s !important;
  box-shadow: 0 2px 8px rgba(79,70,229,0.28), 0 1px 2px rgba(79,70,229,0.2) !important;
  width: 100%;
}
div.stButton > button p,
div[data-testid="stFormSubmitButton"] > button p {
  color: #FFF !important;
  font-weight: 600 !important;
  margin: 0 !important;
}
div.stButton > button:hover {
  background: #4338CA !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 6px 16px rgba(79,70,229,0.36), 0 2px 4px rgba(79,70,229,0.2) !important;
}
div.stButton > button:active { transform: translateY(0) !important; }

/* ── Inputs ──────────────────────────────────────────────────── */
div[data-baseweb="input"] > div,
div[data-baseweb="textarea"] > div,
div[data-baseweb="select"] > div {
  background: var(--surface) !important;
  border: 1.5px solid var(--border) !important;
  border-radius: var(--r-md) !important;
  box-shadow: var(--shadow-sm) !important;
  transition: border-color 0.15s, box-shadow 0.15s !important;
}
div[data-baseweb="input"] > div:focus-within,
div[data-baseweb="textarea"] > div:focus-within {
  border-color: var(--indigo-2) !important;
  box-shadow: var(--shadow-focus) !important;
}
input, textarea { color: var(--ink) !important; }
input::placeholder, textarea::placeholder { color: var(--ink-4) !important; }

/* ── Containers ──────────────────────────────────────────────── */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--surface) !important;
  border: 1.5px solid var(--border) !important;
  border-radius: var(--r-lg) !important;
  padding: 0.75rem !important;
  box-shadow: var(--shadow-sm) !important;
  transition: border-color 0.2s, box-shadow 0.2s !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
  border-color: var(--border-2) !important;
  box-shadow: var(--shadow-md) !important;
}

/* ── Tabs ────────────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"] {
  border-bottom: 2px solid var(--border) !important;
  gap: 4px;
}
[data-testid="stTabs"] button {
  color: var(--ink-3) !important;
  font-weight: 500 !important;
  font-size: 13.5px !important;
  padding: 8px 16px !important;
  border-radius: var(--r-sm) var(--r-sm) 0 0 !important;
  transition: color 0.15s, background 0.15s !important;
}
[data-testid="stTabs"] button:hover { background: var(--surface-3) !important; }
[data-testid="stTabs"] button[aria-selected="true"] {
  color: var(--indigo) !important;
  font-weight: 700 !important;
  border-bottom: 2px solid var(--indigo) !important;
}

/* ── Metric ──────────────────────────────────────────────────── */
[data-testid="stMetric"] {
  background: var(--surface-2);
  border-radius: var(--r-md);
  padding: 1rem 1.25rem;
  border: 1.5px solid var(--border);
}
[data-testid="stMetricLabel"] span { color: var(--ink-3) !important; font-size: 12px !important; font-weight: 600 !important; }
[data-testid="stMetricValue"] { font-family: 'JetBrains Mono', monospace !important; color: var(--indigo) !important; }

/* ── Info/Success/Error overrides ───────────────────────────── */
[data-testid="stAlert"] {
  border-radius: var(--r-md) !important;
  border: 1.5px solid !important;
}

/* ── Dataframe ───────────────────────────────────────────────── */
[data-testid="stDataFrame"] { border-radius: var(--r-md) !important; }

/* ── Checkbox ────────────────────────────────────────────────── */
[data-testid="stCheckbox"] span { font-size: 13.5px !important; }

/* ── Number input ────────────────────────────────────────────── */
[data-testid="stNumberInput"] input {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 14px !important;
  font-weight: 500 !important;
}

/* ══════════════════════════════════════════════════════════════
   CUSTOM COMPONENT STYLES
══════════════════════════════════════════════════════════════ */

/* ── Top Page Header ─────────────────────────────────────────── */
.ph-wrap {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding-bottom: 1.5rem;
  margin-bottom: 1.75rem;
  border-bottom: 1.5px solid var(--border);
}
.ph-left {}
.ph-eyebrow {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.ph-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: var(--indigo-lt);
  color: var(--indigo) !important;
  border: 1.5px solid var(--indigo-md);
  border-radius: 20px;
  padding: 3px 10px;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.ph-badge-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--indigo);
  animation: blink 2s ease-in-out infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }
.ph-title {
  font-size: 1.9rem !important;
  font-weight: 800 !important;
  color: var(--ink) !important;
  letter-spacing: -0.04em;
  line-height: 1.1;
  margin: 0 0 6px !important;
}
.ph-sub {
  font-size: 14px;
  color: var(--ink-3) !important;
  font-weight: 400;
  line-height: 1.5;
}

/* ── KPI Cards ───────────────────────────────────────────────── */
.kpi-card {
  background: var(--surface);
  border: 1.5px solid var(--border);
  border-radius: var(--r-lg);
  padding: 1.25rem 1.25rem 1.1rem;
  position: relative;
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  cursor: default;
}
.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-color: var(--border-2);
}
.kpi-accent-bar {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  border-radius: var(--r-lg) var(--r-lg) 0 0;
}
.kpi-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--ink-3) !important;
  margin-bottom: 10px;
}
.kpi-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 2.4rem;
  font-weight: 600;
  line-height: 1;
  letter-spacing: -0.03em;
  margin-bottom: 8px;
}
.kpi-value .unit {
  font-size: 1rem;
  font-weight: 500;
  margin-left: 2px;
  color: var(--ink-3) !important;
}
.kpi-sub {
  font-size: 11.5px;
  color: var(--ink-3) !important;
  font-weight: 500;
}
.kpi-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 9px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 700;
  margin-top: 10px;
}
.kpi-pill-up   { background: var(--emerald-lt); color: var(--emerald) !important; }
.kpi-pill-down { background: var(--rose-lt);    color: var(--rose) !important; }
.kpi-pill-neu  { background: var(--surface-3);  color: var(--ink-3) !important; }

/* ── Section Header ──────────────────────────────────────────── */
.sec-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 1.25rem;
}
.sec-icon {
  width: 28px; height: 28px;
  border-radius: var(--r-sm);
  background: var(--indigo-lt);
  display: flex; align-items: center; justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
}
.sec-title {
  font-size: 15px !important;
  font-weight: 700 !important;
  color: var(--ink) !important;
  letter-spacing: -0.02em;
  margin: 0;
}

/* ── Form Divider ────────────────────────────────────────────── */
.form-div {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 2rem 0 1.25rem;
}
.form-div-line { flex: 1; height: 1.5px; background: var(--border); }
.form-div-label {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--indigo-lt);
  border: 1.5px solid var(--indigo-md);
  border-radius: 20px;
  padding: 3px 12px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--indigo) !important;
  white-space: nowrap;
}

/* ── Required Label ──────────────────────────────────────────── */
.req-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink) !important;
  margin-bottom: 5px;
  display: flex;
  align-items: center;
  gap: 5px;
}
.req-badge {
  background: var(--rose-lt);
  color: var(--rose) !important;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 4px;
  letter-spacing: 0.04em;
}

/* ── Verdict Box ─────────────────────────────────────────────── */
.verdict-box {
  position: relative;
  background: linear-gradient(135deg, var(--indigo-lt) 0%, #FFF 60%);
  border: 2px solid var(--indigo-md);
  border-radius: var(--r-lg);
  padding: 1.5rem 1.75rem;
  overflow: hidden;
}
.verdict-box::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: radial-gradient(ellipse at top left, rgba(99,102,241,0.08) 0%, transparent 60%);
  pointer-events: none;
}
.verdict-title {
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--indigo) !important;
  margin-bottom: 6px;
  letter-spacing: -0.02em;
}
.verdict-body {
  font-size: 13.5px;
  color: var(--ink-2) !important;
  line-height: 1.65;
}

/* ── Score Tile ──────────────────────────────────────────────── */
.score-tile {
  background: var(--surface-2);
  border: 1.5px solid var(--border);
  border-radius: var(--r-md);
  padding: 1.25rem;
  transition: border-color 0.15s;
}
.score-tile:hover { border-color: var(--border-2); }
.score-cat {
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-3) !important;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.score-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.6rem;
  font-weight: 600;
  letter-spacing: -0.03em;
  margin-bottom: 4px;
}
.score-detail {
  font-size: 11.5px;
  color: var(--ink-3) !important;
}

/* ── OCR Banner ──────────────────────────────────────────────── */
.ocr-banner {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  background: linear-gradient(135deg, var(--sky-lt), #FFF 60%);
  border: 1.5px solid #BAE6FD;
  border-radius: var(--r-lg);
  padding: 1.25rem 1.5rem;
  margin-bottom: 1.5rem;
}
.ocr-icon-wrap {
  width: 40px; height: 40px;
  border-radius: var(--r-md);
  background: var(--sky);
  display: flex; align-items: center; justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}
.ocr-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--sky) !important;
  margin-bottom: 4px;
}
.ocr-sub {
  font-size: 13px;
  color: var(--ink-2) !important;
  line-height: 1.55;
}

/* ── Code Block ──────────────────────────────────────────────── */
.code-block {
  background: var(--sb);
  color: #A5B4FC !important;
  border: 1.5px solid #374151;
  border-radius: var(--r-md);
  padding: 1rem 1.25rem;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12.5px;
  line-height: 1.75;
  white-space: pre;
  overflow-x: auto;
  margin: 0.75rem 0;
}

/* ── Step Item ───────────────────────────────────────────────── */
.step-item {
  display: flex;
  gap: 16px;
  padding: 1.25rem;
  border-radius: var(--r-md);
  background: var(--surface-2);
  border: 1.5px solid var(--border);
  margin-bottom: 10px;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.step-item:hover {
  border-color: var(--indigo-md);
  box-shadow: 0 0 0 3px var(--indigo-lt);
}
.step-num {
  width: 34px; height: 34px;
  border-radius: 50%;
  background: var(--indigo);
  color: #FFF !important;
  display: flex; align-items: center; justify-content: center;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}
.step-body h4 {
  font-size: 14px !important;
  font-weight: 700 !important;
  color: var(--ink) !important;
  margin: 0 0 5px !important;
  letter-spacing: -0.01em;
}
.step-body p {
  font-size: 13px !important;
  color: var(--ink-3) !important;
  margin: 0 !important;
  line-height: 1.6;
}

/* ── Sidebar Logo ────────────────────────────────────────────── */
.sb-logo {
  padding: 22px 16px 16px;
  border-bottom: 1px solid var(--sb-line);
  margin-bottom: 6px;
}
.sb-logo-title {
  font-size: 17px;
  font-weight: 800;
  color: #F1F5F9 !important;
  letter-spacing: -0.03em;
  line-height: 1.2;
}
.sb-logo-sub {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #475569 !important;
  margin-top: 3px;
}
.sb-section {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #374151 !important;
  padding: 14px 22px 5px;
}
.sb-divider {
  height: 1px;
  background: var(--sb-line);
  margin: 8px 16px;
}

/* ── Horizontal Rule ─────────────────────────────────────────── */
.ph-hr {
  border: none;
  border-top: 1.5px solid var(--border);
  margin: 0 0 1.75rem;
}

/* ── Small tag / pill ────────────────────────────────────────── */
.tag-njss {
  display: inline-block;
  background: var(--indigo-lt);
  color: var(--indigo) !important;
  border-radius: 4px;
  padding: 1px 7px;
  font-size: 10.5px;
  font-weight: 700;
}
.tag-ki {
  display: inline-block;
  background: var(--emerald-lt);
  color: var(--emerald) !important;
  border-radius: 4px;
  padding: 1px 7px;
  font-size: 10.5px;
  font-weight: 700;
}

/* ── Plotly chart container ──────────────────────────────────── */
.js-plotly-plot .plotly, .js-plotly-plot .plotly div {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
}

</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
#  LOGIN
# ─────────────────────────────────────────────────────────────────
if not st.session_state.logged_in:
    # Login page CSS override
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
      background: linear-gradient(140deg, #1E1B4B 0%, #1E3A5F 50%, #0F172A 100%) !important;
    }
    </style>""", unsafe_allow_html=True)

    st.markdown("<br>" * 3, unsafe_allow_html=True)
    _, col, _ = st.columns([1.5, 1, 1.5])
    with col:
        st.markdown("""
        <div style="text-align:center; margin-bottom:2rem;">
          <div style="
            display:inline-flex; align-items:center; justify-content:center;
            width:60px; height:60px; border-radius:16px;
            background:linear-gradient(135deg,#6366F1,#4F46E5);
            box-shadow:0 8px 24px rgba(99,102,241,0.4);
            margin-bottom:1.25rem;
          ">
            <span style="font-size:28px;">📊</span>
          </div>
          <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:1.75rem; font-weight:800; color:#F1F5F9; letter-spacing:-0.04em; line-height:1.2; margin-bottom:6px;">
            入札 PoC Board
          </div>
          <div style="font-size:13px; color:#64748B; font-weight:500;">
            入札ツール導入前検証プラットフォーム
          </div>
        </div>""", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("""
            <style>
            [data-testid="stVerticalBlockBorderWrapper"] {
              background: rgba(30,27,75,0.6) !important;
              border: 1.5px solid rgba(99,102,241,0.3) !important;
              backdrop-filter: blur(12px);
            }
            </style>""", unsafe_allow_html=True)
            st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

            st.markdown('<div style="font-size:12px;font-weight:700;color:#6366F1;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px;">ログインID</div>', unsafe_allow_html=True)
            uid = st.text_input("ID", placeholder="admin", label_visibility="collapsed").strip()
            st.markdown('<div style="font-size:12px;font-weight:700;color:#6366F1;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px;margin-top:12px;">パスワード</div>', unsafe_allow_html=True)
            pwd = st.text_input("PW", type="password", placeholder="••••••••", label_visibility="collapsed").strip()
            st.markdown("<div style='height:0.75rem;'></div>", unsafe_allow_html=True)
            if st.button("サインイン →"):
                if uid == "admin" and pwd == "admin":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("IDまたはパスワードが正しくありません。")
            st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

        st.markdown('<div style="text-align:center;margin-top:1rem;font-size:12px;color:#334155;">admin / admin でログイン可能</div>', unsafe_allow_html=True)
    st.stop()


# ─────────────────────────────────────────────────────────────────
#  DATA LAYER
# ─────────────────────────────────────────────────────────────────
conn = st.connection("gsheets", type=GSheetsConnection)
COLS = [
    "ID","自治体名","担当部署名","案件概要","公示日","入札日","履行期間",
    "入札方式","参加資格","予算(千円)","落札金額(千円)","自社結果",
    "落札企業","競合1","競合2","競合3","仕様書","NJSS掲載","入札王掲載",
    "URL1","URL2","URL3","URL4","URL5",
]

@st.cache_data(ttl=0)
def load_data():
    try:
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        df = conn.read(spreadsheet=url, ttl="0s")
        return df if "URL1" in df.columns else pd.DataFrame(columns=COLS)
    except:
        return pd.DataFrame(columns=COLS)

def vdf(df):
    return df[df["自治体名"].notna() & (df["自治体名"].astype(str).str.strip() != "")].copy()

def save_data(df_new):
    conn.update(
        spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"],
        data=df_new.fillna(""),
    )
    load_data.clear()

def calc_proj():
    df = vdf(load_data())
    avg_bid = 0
    if not df.empty and "落札金額(千円)" in df.columns:
        nums = pd.to_numeric(df["落札金額(千円)"], errors="coerce").fillna(0)
        if (nums > 0).any():
            avg_bid = nums[nums > 0].mean() * 1000
    c = st.session_state.costs
    ap = avg_bid * (c["margin"] / 100) * (c["win_rate"] / 100) * c["annual_bids"]
    rows = []
    for y in range(6):
        nc = c["n_init"] + (c["n_month"] * 12 + c["n_opt"]) * y
        kc = c["k_init"] + (c["k_month"] * 12 + c["k_opt"]) * y
        rev = ap * y
        rows.append({
            "年": y, "NJSS累積コスト": nc, "NJSS利益": rev - nc,
            "入札王累積コスト": kc, "入札王利益": rev - kc, "累積売上": rev,
        })
    return pd.DataFrame(rows), ap


# ─────────────────────────────────────────────────────────────────
#  PLOTLY THEME
# ─────────────────────────────────────────────────────────────────
_FONT = "'Plus Jakarta Sans', -apple-system, 'Hiragino Kaku Gothic ProN', sans-serif"
PLY = dict(
    template="plotly_white",
    font=dict(family=_FONT, color="#64748B", size=12),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=16, r=16, t=32, b=16),
    legend=dict(
        orientation="h", yanchor="bottom", y=-0.38,
        xanchor="center", x=0.5,
        font=dict(size=11.5), bgcolor="rgba(0,0,0,0)",
        bordercolor="rgba(0,0,0,0)",
    ),
)
# Color palette
C_INDIGO = "#4F46E5"
C_TEAL   = "#0D9488"
C_VIOLET = "#7C3AED"
C_ROSE   = "#E11D48"
C_EMERALD= "#059669"

GRID_COLOR = "rgba(0,0,0,0.04)"


# ─────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────
def go_to_dashboard():
    st.session_state.current_page = "ダッシュボード"
    st.session_state.nav_radio = "ダッシュボード"

def page_header(title, sub="", badge="", live=False):
    col_l, col_r = st.columns([3, 1])
    with col_l:
        badge_html = ""
        if badge or live:
            dot = '<div class="ph-badge-dot"></div>' if live else ""
            badge_html = f'<div class="ph-badge">{dot}{badge}</div>'
        sub_html = f'<div class="ph-sub">{sub}</div>' if sub else ""
        st.markdown(f"""
        <div class="ph-wrap">
          <div class="ph-left">
            <div class="ph-eyebrow">{badge_html}</div>
            <h1 class="ph-title">{title}</h1>
            {sub_html}
          </div>
        </div>""", unsafe_allow_html=True)
    with col_r:
        st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
        if title != "PoC Dashboard":
            st.button("← ダッシュボードへ", key=f"back_{title}",
                      on_click=go_to_dashboard, use_container_width=True)

def kpi_card(label, value, unit="", sub="", pill="", pill_type="neu", accent="#4F46E5"):
    pill_html = ""
    if pill:
        pill_html = f'<div class="kpi-pill kpi-pill-{pill_type}">{pill}</div>'
    unit_html = f'<span class="unit">{unit}</span>' if unit else ""
    sub_html  = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-accent-bar" style="background:{accent};"></div>
      <div class="kpi-label">{label}</div>
      <div class="kpi-value" style="color:{accent} !important;">{value}{unit_html}</div>
      {sub_html}
      {pill_html}
    </div>""", unsafe_allow_html=True)

def sec_header(icon, title):
    st.markdown(f"""
    <div class="sec-header">
      <div class="sec-icon">{icon}</div>
      <span class="sec-title">{title}</span>
    </div>""", unsafe_allow_html=True)

def form_div(label):
    st.markdown(f"""
    <div class="form-div">
      <div class="form-div-line"></div>
      <div class="form-div-label">{label}</div>
      <div class="form-div-line"></div>
    </div>""", unsafe_allow_html=True)

def req_label(text):
    st.markdown(f"""
    <div class="req-label">
      {text}
      <span class="req-badge">必須</span>
    </div>""", unsafe_allow_html=True)

def score_tile(category_num, category, winner, detail, c1=C_INDIGO, c2=C_TEAL):
    color = c1 if winner == "NJSS" else c2 if winner == "入札王" else "#64748B"
    st.markdown(f"""
    <div class="score-tile">
      <div class="score-cat"><span>{category_num}</span> {category}</div>
      <div class="score-num" style="color:{color} !important;">{winner}</div>
      <div class="score-detail">{detail}</div>
    </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
#  OCR
# ─────────────────────────────────────────────────────────────────
def ocr_extract(uploaded_file) -> dict:
    if uploaded_file is None:
        return {}
    raw = uploaded_file.read()
    try:
        api_key = st.secrets["google_vision"]["api_key"]
        import requests
        b64 = base64.b64encode(raw).decode()
        payload = {"requests": [{"image": {"content": b64},
                                  "features": [{"type": "DOCUMENT_TEXT_DETECTION"}]}]}
        resp = requests.post(
            f"https://vision.googleapis.com/v1/images:annotate?key={api_key}",
            json=payload, timeout=20,
        )
        text = resp.json()["responses"][0].get("fullTextAnnotation", {}).get("text", "")
        result = {}
        patterns = {
            "自治体名":   r"((?:東京都|北海道|(?:大阪|京都)府|.+?[都道府県])[\s　]*(?:[^\s　]+[市区町村])?)",
            "案件概要":   r"(?:業務名|件名|案件名)\s*[：:]\s*(.+)",
            "予算(千円)": r"(?:予算額?|上限額?|限度額?)[^\d]*(\d[\d,]+)",
            "入札方式":   r"(公募型プロポーザル|一般競争入札|指名競争入札|随意契約)",
            "参加資格":   r"(?:参加資格|資格要件)\s*[：:]\s*(.+)",
        }
        for field, pat in patterns.items():
            m = re.search(pat, text)
            if m:
                raw_v = (m.group(1) if m.lastindex else m.group(0)).strip()
                if field == "予算(千円)":
                    try: raw_v = str(int(raw_v.replace(",", "")) // 1000)
                    except: pass
                result[field] = raw_v
        return result if result else _demo_ocr()
    except:
        return _demo_ocr()

def _demo_ocr():
    st.warning("**OCR デモモード** — Google Vision APIキー未設定のためサンプルデータを表示しています。")
    return {
        "自治体名": "東京都",
        "案件概要": "情報システム調達支援業務",
        "予算(千円)": "5000",
        "入札方式": "公募型プロポーザル",
        "参加資格": "情報処理 Aランク",
    }


# ─────────────────────────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sb-logo">
      <div style="display:flex;align-items:center;gap:10px;">
        <div style="width:36px;height:36px;border-radius:10px;
          background:linear-gradient(135deg,#6366F1,#4F46E5);
          display:flex;align-items:center;justify-content:center;
          font-size:18px;flex-shrink:0;">📊</div>
        <div>
          <div class="sb-logo-title">PoC Board</div>
          <div class="sb-logo-sub">入札ツール評価</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="sb-section">Navigation</div>', unsafe_allow_html=True)

    menu_options = ["ダッシュボード", "案件データ入力", "ワード検索数", "ROI分析", "マニュアル"]
    test_mode = st.toggle("管理モード", key="admin_toggle")
    if test_mode:
        menu_options.append("データ管理")

    def on_nav_change():
        st.session_state.current_page = st.session_state.nav_radio

    current_index = 0
    if st.session_state.current_page in menu_options:
        current_index = menu_options.index(st.session_state.current_page)
    else:
        st.session_state.current_page = menu_options[0]

    st.radio(
        "ページ",
        menu_options,
        index=current_index,
        key="nav_radio",
        label_visibility="collapsed",
        on_change=on_nav_change,
    )
    current_page = st.session_state.current_page

    st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="padding:10px 20px; font-size:11.5px; color:#374151; line-height:1.9;">
      <div style="font-weight:700;color:#4B5563;margin-bottom:5px;">検証フロー</div>
      <div>① 案件入力</div>
      <div>② ワード検索</div>
      <div>③ ROI設定</div>
      <div>④ ダッシュボード確認</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("ログアウト"):
        st.session_state.logged_in = False
        st.rerun()


# ─────────────────────────────────────────────────────────────────
#  PAGE: DASHBOARD
# ─────────────────────────────────────────────────────────────────
if current_page == "ダッシュボード":
    page_header(
        "PoC Dashboard",
        "入札ツール導入前検証 — データ統合ビュー",
        badge="LIVE",
        live=True,
    )

    df  = load_data()
    vd  = vdf(df)
    p_df, _ = calc_proj()

    if vd.empty:
        with st.container(border=True):
            st.info("データがありません。「案件データ入力」から登録してください。")
        st.stop()

    total = len(vd)
    nj_c  = vd["NJSS掲載"].astype(str).str.upper().isin(["TRUE","1","1.0","YES"]).sum()
    ki_c  = vd["入札王掲載"].astype(str).str.upper().isin(["TRUE","1","1.0","YES"]).sum()
    n_p5  = p_df.iloc[-1]["NJSS利益"]  if not p_df.empty else 0
    k_p5  = p_df.iloc[-1]["入札王利益"] if not p_df.empty else 0

    # ── KPI Row ──────────────────────────────────────────────────
    cols = st.columns(5)
    with cols[0]:
        kpi_card("対象案件数", total, "件",
                 sub="登録済み総案件", accent="#0F172A")
    with cols[1]:
        pct_nj = f"{nj_c/total*100:.1f}"
        kpi_card("NJSS 網羅率", pct_nj, "%",
                 sub=f"{nj_c} 件捕捉",
                 pill="NJSS優位" if nj_c > ki_c else ("同等" if nj_c == ki_c else "入札王優位"),
                 pill_type="up" if nj_c >= ki_c else "down",
                 accent=C_INDIGO)
    with cols[2]:
        pct_ki = f"{ki_c/total*100:.1f}"
        kpi_card("入札王 網羅率", pct_ki, "%",
                 sub=f"{ki_c} 件捕捉",
                 pill="入札王優位" if ki_c > nj_c else ("同等" if ki_c == nj_c else "NJSS優位"),
                 pill_type="up" if ki_c >= nj_c else "down",
                 accent=C_TEAL)
    with cols[3]:
        kpi_card("NJSS 5年利益", f"{int(n_p5/10000):,}", "万円",
                 sub="累積期待利益予測", accent=C_VIOLET)
    with cols[4]:
        kpi_card("入札王 5年利益", f"{int(k_p5/10000):,}", "万円",
                 sub="累積期待利益予測", accent=C_ROSE)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 1: Capture + Competitor ──────────────────────────────
    r1l, r1r = st.columns(2)
    with r1l:
        with st.container(border=True):
            sec_header("📊", "案件捕捉数の比較")
            fig = px.bar(
                x=["NJSS", "入札王"], y=[nj_c, ki_c],
                color=["NJSS", "入札王"],
                color_discrete_map={"NJSS": C_INDIGO, "入札王": C_TEAL},
                text=[nj_c, ki_c],
            )
            fig.update_traces(
                marker_line_width=0,
                textposition="outside",
                textfont=dict(size=14, weight=700),
                width=0.55,
            )
            fig.update_layout(**PLY, showlegend=False, height=260,
                              bargap=0.4)
            fig.update_yaxes(title="捕捉件数", gridcolor=GRID_COLOR, zeroline=False,
                             showline=False, tickfont=dict(size=11))
            fig.update_xaxes(title="", tickfont=dict(size=13, color="#0F172A"))
            st.plotly_chart(fig, use_container_width=True)

    with r1r:
        with st.container(border=True):
            sec_header("🏢", "競合出現シェア Top 6")
            comp = pd.concat([vd["落札企業"], vd["競合1"], vd["競合2"], vd["競合3"]])
            comp_df = comp[comp.notna() & (comp != "")].value_counts().head(6).reset_index()
            comp_df.columns = ["企業名", "回数"]
            fig2 = px.bar(
                comp_df, x="回数", y="企業名", orientation="h",
                text="回数", color_discrete_sequence=[C_VIOLET],
            )
            fig2.update_traces(
                marker_line_width=0,
                textposition="outside",
                textfont=dict(size=11, weight=600),
            )
            fig2.update_layout(**PLY, showlegend=False, height=260)
            fig2.update_xaxes(title="出現回数", gridcolor=GRID_COLOR, zeroline=False,
                              showline=False, tickfont=dict(size=11))
            fig2.update_yaxes(title="", tickfont=dict(size=11))
            st.plotly_chart(fig2, use_container_width=True)

    # ── Row 2: Keyword + Radar ────────────────────────────────────
    r2l, r2r = st.columns([1.15, 0.85])
    with r2l:
        with st.container(border=True):
            sec_header("🔍", "キーワード検索精度比較")
            if st.session_state.search_words and st.session_state.search_counts:
                sw_df = pd.DataFrame([
                    {"ワード": w,
                     "NJSS":  st.session_state.search_counts.get(w, {}).get("NJSS", 0),
                     "入札王": st.session_state.search_counts.get(w, {}).get("入札王", 0)}
                    for w in st.session_state.search_words
                ])
                fig3 = px.bar(
                    sw_df, x="ワード", y=["NJSS", "入札王"],
                    barmode="group",
                    color_discrete_map={"NJSS": C_INDIGO, "入札王": C_TEAL},
                )
                fig3.update_traces(marker_line_width=0)
                fig3.update_layout(**PLY, height=280, legend_title_text="")
                fig3.update_yaxes(title="ヒット件数", gridcolor=GRID_COLOR,
                                  zeroline=False, tickfont=dict(size=11))
                fig3.update_xaxes(tickfont=dict(size=11))
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.markdown("""
                <div style="
                  display:flex; flex-direction:column; align-items:center;
                  justify-content:center; height:200px; color:#94A3B8;
                ">
                  <div style="font-size:2rem; margin-bottom:12px;">🔍</div>
                  <div style="font-size:13px; font-weight:500;">「ワード検索数」画面からデータを追加してください</div>
                </div>""", unsafe_allow_html=True)

    with r2r:
        with st.container(border=True):
            sec_header("🎯", "総合評価レーダー")
            cov_w = "NJSS" if nj_c > ki_c else "入札王" if ki_c > nj_c else "同等"
            nj_sw = sum(1 for v in st.session_state.search_counts.values()
                        if v.get("NJSS", 0) > v.get("入札王", 0))
            ki_sw = sum(1 for v in st.session_state.search_counts.values()
                        if v.get("入札王", 0) > v.get("NJSS", 0))
            sw_w  = "NJSS" if nj_sw > ki_sw else "入札王" if ki_sw > nj_sw else "同等"
            roi_w = "NJSS" if n_p5 > k_p5 else "入札王" if k_p5 > n_p5 else "同等"

            nj_cov = nj_c/total*100 if total else 0
            ki_cov = ki_c/total*100 if total else 0
            tot_sw = nj_sw + ki_sw
            nj_s   = nj_sw/tot_sw*100 if tot_sw else 50
            ki_s   = ki_sw/tot_sw*100 if tot_sw else 50
            mx     = max(n_p5, k_p5, 1)
            nj_ps, ki_ps = max(0, n_p5/mx*100), max(0, k_p5/mx*100)

            cats = ["網羅率", "検索精度", "5年ROI", "網羅率"]
            fig_r = go.Figure()
            fig_r.add_trace(go.Scatterpolar(
                r=[nj_cov, nj_s, nj_ps, nj_cov], theta=cats,
                fill="toself", name="NJSS",
                line=dict(color=C_INDIGO, width=2.5),
                fillcolor="rgba(79,70,229,0.12)",
            ))
            fig_r.add_trace(go.Scatterpolar(
                r=[ki_cov, ki_s, ki_ps, ki_cov], theta=cats,
                fill="toself", name="入札王",
                line=dict(color=C_TEAL, width=2.5, dash="dot"),
                fillcolor="rgba(13,148,136,0.10)",
            ))
            fig_r.update_layout(
                polar=dict(
                    bgcolor="rgba(0,0,0,0)",
                    radialaxis=dict(visible=True, range=[0,100],
                                   gridcolor="rgba(0,0,0,0.06)",
                                   color="#94A3B8", tickfont=dict(size=9)),
                    angularaxis=dict(gridcolor="rgba(0,0,0,0.06)",
                                     color="#334155", tickfont=dict(size=11, weight=600)),
                ),
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family=_FONT, size=11, color="#64748B"),
                legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center",
                            bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
                height=280, margin=dict(t=16, b=48, l=16, r=16),
            )
            st.plotly_chart(fig_r, use_container_width=True)

    # ── Verdict ──────────────────────────────────────────────────
    with st.container(border=True):
        sec_header("⚖️", "総合判定レポート")
        nj_sc = (cov_w=="NJSS") + (sw_w=="NJSS") + (roi_w=="NJSS")
        ki_sc = (cov_w=="入札王") + (sw_w=="入札王") + (roi_w=="入札王")

        s1, s2, s3 = st.columns(3)
        with s1:
            score_tile("①", "網羅率（過去案件）", cov_w,
                       f"NJSS {int(nj_cov)}% ／ 入札王 {int(ki_cov)}%")
        with s2:
            score_tile("②", "キーワード検索精度", sw_w, "優位ワード数で比較")
        with s3:
            score_tile("③", "5年 ROI", roi_w,
                       f"NJSS {int(n_p5/10000):,}万 ／ 入札王 {int(k_p5/10000):,}万")

        st.markdown("<br>", unsafe_allow_html=True)
        if nj_sc > ki_sc:
            st.markdown(f"""
            <div class="verdict-box">
              <div class="verdict-title">✦ 最終推奨ツール：NJSS（{nj_sc}/3 項目で優位）</div>
              <div class="verdict-body">
                各検証データを総合した結果、NJSSの導入を推奨します。
                過去案件の網羅性と機会損失防止の観点で優位性が確認されました。
                確実な案件捕捉により事業成長への貢献が最も高いと判断されます。
              </div>
            </div>""", unsafe_allow_html=True)
        elif ki_sc > nj_sc:
            st.markdown(f"""
            <div class="verdict-box">
              <div class="verdict-title">✦ 最終推奨ツール：入札王（{ki_sc}/3 項目で優位）</div>
              <div class="verdict-body">
                各検証データを総合した結果、入札王の導入を推奨します。
                コストパフォーマンスと早期損益分岐点の優位性により、
                ROI最大化が期待できる運用に最適と判断されます。
              </div>
            </div>""", unsafe_allow_html=True)
        else:
            st.info("両者拮抗（引き分け）。UIの使いやすさや営業サポート体制などの定性要素で最終判断してください。")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── ROI Forecast ─────────────────────────────────────────────
    with st.container(border=True):
        sec_header("📈", "累積期待利益の予測推移（5カ年）")
        fig4 = px.line(
            p_df, x="年", y=["NJSS利益", "入札王利益"],
            color_discrete_map={"NJSS利益": C_INDIGO, "入札王利益": C_TEAL},
        )
        fig4.update_traces(line_width=2.5)
        fig4.update_layout(**PLY, height=260)
        fig4.update_yaxes(title="累積利益 (円)", gridcolor=GRID_COLOR,
                          zeroline=False, tickfont=dict(size=11))
        fig4.update_xaxes(title="経過年数", tickfont=dict(size=11))
        st.plotly_chart(fig4, use_container_width=True)


# ─────────────────────────────────────────────────────────────────
#  PAGE: DATA INPUT + OCR
# ─────────────────────────────────────────────────────────────────
elif current_page == "案件データ入力":
    page_header("案件データ入力", "仕様書・公告OCR読み取り ＋ 手動入力")

    # OCR Banner
    st.markdown("""
    <div class="ocr-banner">
      <div class="ocr-icon-wrap">📄</div>
      <div>
        <div class="ocr-title">仕様書・公告ファイルから自動入力（OCR）</div>
        <div class="ocr-sub">
          PNG / JPG / PDF をアップロードすると主要項目を自動解析してフォームへ反映します。<br>
          アップロードされたファイルは OCR処理のみに使用され、サーバーには保存されません。
          Google Cloud Vision APIキーを設定すると本番動作します（設定方法は「マニュアル」参照）。
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    ocr_file = st.file_uploader(
        "ファイルをアップロード（PNG / JPG / PDF）",
        type=["png", "jpg", "jpeg", "pdf"],
        key="ocr_up",
    )
    if ocr_file:
        with st.spinner("OCR 解析中..."):
            st.session_state.ocr_result = ocr_extract(ocr_file)
        if st.session_state.ocr_result:
            st.success(f"✓  {len(st.session_state.ocr_result)} 項目を読み取りました。フォームに反映しています。")

    ocr = st.session_state.ocr_result or {}
    df_cur = load_data()
    vd     = vdf(df_cur)

    with st.container(border=True):
        with st.form("entry_form", clear_on_submit=True):
            form_div("基本情報")
            c1, c2 = st.columns(2)
            with c1:
                req_label("自治体名・発注機関")
                mun = st.text_input("mun", label_visibility="collapsed",
                                    placeholder="例：横浜市", value=ocr.get("自治体名",""))
            with c2:
                st.markdown('<div class="req-label">担当部署名</div>', unsafe_allow_html=True)
                dep = st.text_input("dep", label_visibility="collapsed",
                                    placeholder="例：デジタル統括本部", value=ocr.get("担当部署名",""))
            req_label("案件名・案件概要")
            smm = st.text_input("smm", label_visibility="collapsed",
                                placeholder="例：交通データ連携基盤構築業務", value=ocr.get("案件概要",""))

            form_div("スケジュール・要件")
            c3, c4, c5 = st.columns(3)
            pub_d  = c3.date_input("公示日", value=None)
            bid_d  = c4.date_input("入札日", value=None)
            per_d  = c5.text_input("履行期間", placeholder="2025-06-01 〜 2026-03-31",
                                   value=ocr.get("履行期間",""))
            c6, c7 = st.columns(2)
            methods = ["","公募型プロポーザル","一般競争入札","指名競争入札","随意契約","その他"]
            m_idx   = methods.index(ocr.get("入札方式","")) if ocr.get("入札方式","") in methods else 0
            method  = c6.selectbox("入札方式", methods, index=m_idx)
            qual    = c7.text_input("参加資格", placeholder="情報処理 Aランク",
                                    value=ocr.get("参加資格",""))

            form_div("結果・金額")
            c8, c9, c10 = st.columns(3)
            bv = 0
            try: bv = int(ocr.get("予算(千円)", 0))
            except: pass
            budget  = c8.number_input("予算額 (千円)", min_value=0, step=100, value=bv)
            with c9:
                req_label("落札金額 (千円)")
                wbid = st.number_input("wbid", label_visibility="collapsed",
                                       min_value=0, step=100)
            our_res = c10.selectbox("自社結果", ["","受注","失注","見送り","辞退"])
            c11, c12 = st.columns(2)
            wnr = c11.text_input("落札企業")
            b1  = c12.text_input("競合1")
            b2  = c11.text_input("競合2")
            b3  = c12.text_input("競合3")

            form_div("ツール掲載確認（PoC）")
            st.caption("両ツールで見つかった場合は両方にチェックを入れてください")
            cx1, cx2, cx3 = st.columns(3)
            spc = cx1.checkbox("仕様書あり")
            njl = cx2.checkbox("NJSS に掲載")
            kil = cx3.checkbox("入札王に掲載")

            form_div("参考URL")
            cu1, cu2 = st.columns(2)
            url1 = cu1.text_input("URL 1")
            url2 = cu2.text_input("URL 2")
            cu3, cu4 = st.columns(2)
            url3 = cu3.text_input("URL 3")
            url4 = cu4.text_input("URL 4")
            url5 = st.text_input("URL 5")

            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("✓  この案件を保存する"):
                if mun and smm and wbid > 0:
                    new_rec = pd.DataFrame([{
                        "ID": len(vd)+1, "自治体名": mun, "担当部署名": dep,
                        "案件概要": smm,
                        "公示日": pub_d.strftime("%Y-%m-%d") if pub_d else "",
                        "入札日": bid_d.strftime("%Y-%m-%d") if bid_d else "",
                        "履行期間": per_d, "入札方式": method, "参加資格": qual,
                        "予算(千円)": budget, "落札金額(千円)": wbid, "自社結果": our_res,
                        "落札企業": wnr, "競合1": b1, "競合2": b2, "競合3": b3,
                        "仕様書": spc, "NJSS掲載": njl, "入札王掲載": kil,
                        "URL1": url1, "URL2": url2, "URL3": url3, "URL4": url4, "URL5": url5,
                    }])
                    try:
                        save_data(pd.concat([vd, new_rec], ignore_index=True))
                        st.session_state.ocr_result = None
                        st.success("保存しました。")
                    except Exception as e:
                        st.error(f"保存失敗: {e}")
                else:
                    st.error("「自治体名」「案件名」「落札金額（1以上）」は必須です。")

    if not vd.empty:
        with st.container(border=True):
            sec_header("📋", "登録済みデータ一覧")
            st.dataframe(vd, hide_index=True, use_container_width=True)


# ─────────────────────────────────────────────────────────────────
#  PAGE: KEYWORD SEARCH
# ─────────────────────────────────────────────────────────────────
elif current_page == "ワード検索数":
    page_header("ワード検索数比較", "同一キーワードで両ツールを実測 → 件数を入力してダッシュボードへ反映")

    today_str = datetime.date.today().strftime("%Y-%m-%d")

    with st.container(border=True):
        sec_header("➕", "キーワードの追加")
        ca1, ca2, ca3 = st.columns([2, 1, 1])
        nw = ca1.text_input("キーワード", placeholder="例：BIツール、DX推進",
                            label_visibility="collapsed")
        if ca2.button("追加"):
            if nw and nw not in st.session_state.search_words:
                st.session_state.search_words.append(nw)
                st.session_state.search_counts[nw] = {
                    "NJSS": 0, "入札王": 0, "登録日": today_str,
                }
                st.rerun()
        if ca3.button("リストをクリア"):
            st.session_state.search_words = []
            st.session_state.search_counts = {}
            st.rerun()

    with st.container(border=True):
        sec_header("📝", "ヒット件数テーブル（セル直接編集可）")
        if st.session_state.search_words:
            df_sw = pd.DataFrame([{
                "検索ワード": w,
                "登録日":    st.session_state.search_counts.get(w, {}).get("登録日", today_str),
                "NJSS (件)":  st.session_state.search_counts.get(w, {}).get("NJSS", 0),
                "入札王 (件)": st.session_state.search_counts.get(w, {}).get("入札王", 0),
            } for w in st.session_state.search_words])
            edited = st.data_editor(df_sw, num_rows="dynamic",
                                    use_container_width=True, hide_index=True, key="kw_ed")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✓  件数を保存してダッシュボードへ反映"):
                st.session_state.search_words = edited["検索ワード"].dropna().tolist()
                st.session_state.search_counts = {
                    row["検索ワード"]: {
                        "NJSS":  int(row.get("NJSS (件)", 0)  or 0),
                        "入札王": int(row.get("入札王 (件)", 0) or 0),
                        "登録日": str(row.get("登録日", today_str)),
                    }
                    for _, row in edited.iterrows() if pd.notna(row["検索ワード"])
                }
                st.success("保存しました。ダッシュボードに反映されています。")
        else:
            st.info("上の欄からキーワードを追加してください。")


# ─────────────────────────────────────────────────────────────────
#  PAGE: ROI ANALYSIS
# ─────────────────────────────────────────────────────────────────
elif current_page == "ROI分析":
    page_header("コスト・ROI分析設定", "費用と営業指標を設定してシミュレーションを実行します")

    with st.container(border=True):
        sec_header("💰", "費用見積と営業シミュレーション")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### NJSS 費用見積")
            ni = st.number_input("初期費用 (円)", value=st.session_state.costs["n_init"], key="ni")
            nm = st.number_input("月額費用 (円)", value=st.session_state.costs["n_month"], key="nm")
            no = st.number_input("年間オプション (円)", value=st.session_state.costs["n_opt"], key="no")
            st.metric("NJSS 初年度合計", f"¥{ni + nm*12 + no:,}")
        with c2:
            st.markdown("#### 入札王 費用見積")
            ki = st.number_input("初期費用 (円)", value=st.session_state.costs["k_init"], key="ki")
            km = st.number_input("月額費用 (円)", value=st.session_state.costs["k_month"], key="km")
            ko = st.number_input("年間オプション (円)", value=st.session_state.costs["k_opt"], key="ko")
            st.metric("入札王 初年度合計", f"¥{ki + km*12 + ko:,}")

        st.markdown("---")
        st.markdown("#### 営業シミュレーション設定")
        s1, s2, s3 = st.columns(3)
        wr = s1.number_input("平均受注率 (%)", value=st.session_state.costs["win_rate"])
        mg = s2.number_input("平均粗利率 (%)", value=st.session_state.costs["margin"])
        ab = s3.number_input("年間想定応札数 (件)", value=st.session_state.costs["annual_bids"])
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✓  設定を保存してグラフを更新"):
            st.session_state.costs.update({
                "n_init": ni, "n_month": nm, "n_opt": no,
                "k_init": ki, "k_month": km, "k_opt": ko,
                "margin": mg, "win_rate": wr, "annual_bids": ab,
            })
            st.success("更新しました。")
            st.rerun()

    p_df, _ = calc_proj()

    with st.container(border=True):
        sec_header("📉", "損益分岐点 ＆ 5年収益推移")
        fb = go.Figure()
        fb.add_trace(go.Scatter(x=p_df["年"], y=p_df["累積売上"],
                                name="累積売上期待値",
                                line=dict(color=C_EMERALD, width=3)))
        fb.add_trace(go.Scatter(x=p_df["年"], y=p_df["NJSS累積コスト"],
                                name="NJSS累積コスト",
                                line=dict(color=C_INDIGO, dash="dash", width=2)))
        fb.add_trace(go.Scatter(x=p_df["年"], y=p_df["入札王累積コスト"],
                                name="入札王累積コスト",
                                line=dict(color=C_TEAL, dash="dot", width=2)))
        fb.update_layout(**PLY, height=300)
        fb.update_yaxes(title="金額 (円)", gridcolor=GRID_COLOR,
                        zeroline=False, tickfont=dict(size=11))
        fb.update_xaxes(title="経過年数", tickfont=dict(size=11))
        st.plotly_chart(fb, use_container_width=True)

    with st.container(border=True):
        sec_header("📊", "各年の累積利益比較")
        fp = px.bar(
            p_df, x="年", y=["NJSS利益", "入札王利益"],
            barmode="group",
            color_discrete_map={"NJSS利益": C_INDIGO, "入札王利益": C_TEAL},
        )
        fp.update_traces(marker_line_width=0)
        fp.update_layout(**PLY, height=280)
        fp.update_yaxes(title="累積利益 (円)", gridcolor=GRID_COLOR,
                        zeroline=False, tickfont=dict(size=11))
        fp.update_xaxes(tickfont=dict(size=11))
        st.plotly_chart(fp, use_container_width=True)


# ─────────────────────────────────────────────────────────────────
#  PAGE: MANUAL
# ─────────────────────────────────────────────────────────────────
elif current_page == "マニュアル":
    page_header("自走式 PoC 評価マニュアル", "検証フロー・OCR設定ガイド・営業DB活用法")

    tabs = st.tabs(["検証フロー", "OCR設定方法", "営業DB活用"])

    with tabs[0]:
        with st.container(border=True):
            sec_header("🗺️", "5ステップ検証フロー")
            steps = [
                ("過去案件データの準備",
                 "「案件データ入力」画面に、自社ターゲット案件を10〜20件入力します。"
                 "仕様書PDFのOCR読み取りも活用できます。"),
                ("ツールでの検索実測",
                 "各ツールのトライアルアカウントで案件を検索し、見つかった場合は"
                 "「NJSS掲載」「入札王掲載」にチェックを入れます。"),
                ("キーワード検索ボリューム確認",
                 "「ワード検索数」画面で得意領域のキーワードを入力し、"
                 "ヒット件数を記録・保存します。"),
                ("コストシミュレーション設定",
                 "「ROI分析」画面で各ツールの見積金額・自社の受注率・粗利率を"
                 "入力してシミュレーションを実行します。"),
                ("ダッシュボードで最終判断",
                 "「ダッシュボード」でレーダーチャートと推奨テキストを確認し、"
                 "スクリーンショットを稟議書に添付します。"),
            ]
            for i, (title, body) in enumerate(steps, 1):
                st.markdown(f"""
                <div class="step-item">
                  <div class="step-num">{i}</div>
                  <div class="step-body">
                    <h4>{title}</h4>
                    <p>{body}</p>
                  </div>
                </div>""", unsafe_allow_html=True)

    with tabs[1]:
        with st.container(border=True):
            sec_header("⚙️", "Google Cloud Vision API の設定方法")

            st.markdown("**ステップ 1 — Google Cloud Console でプロジェクトを作成**")
            st.markdown("https://console.cloud.google.com/ にアクセスし、新規プロジェクトを作成します。")

            st.markdown("**ステップ 2 — Cloud Vision API を有効化**")
            st.markdown("「APIとサービス」→「ライブラリ」→ `Cloud Vision API` を検索して「有効にする」をクリック。")

            st.markdown("**ステップ 3 — APIキーを発行**")
            st.markdown("「APIとサービス」→「認証情報」→「認証情報を作成」→「APIキー」でキーを発行します。")

            st.markdown("**ステップ 4 — `secrets.toml` にキーを追記（ローカル開発）**")
            st.markdown('<div class="code-block">[google_vision]\napi_key = "AIzaSy＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿"</div>', unsafe_allow_html=True)

            st.markdown("**Streamlit Cloud の場合**")
            st.markdown('<div class="code-block">Streamlit Cloud ダッシュボード\n  → アプリ選択 → Settings → Secrets タブ\n  → 上記の [google_vision] ブロックを貼り付けて「Save」</div>', unsafe_allow_html=True)

            st.markdown("**ステップ 5 — 動作確認**")
            st.markdown("「案件データ入力」画面でPNGまたはPDFをアップロードし、項目が自動入力されれば設定完了です。")

            st.info("💡 料金目安：Cloud Vision API は月1,000リクエストまで無料。仕様書1件 ＝ 1リクエストのため、通常のPoC用途では無料枠内で収まります。")

            st.markdown("**よくあるエラーと対処**")
            e1, e2 = st.columns(2)
            with e1:
                st.error("403 Forbidden → APIが有効化されていません。ステップ2を再確認してください。")
            with e2:
                st.error("KeyError: google_vision → secrets.toml のセクション名 [google_vision] が正しいか確認してください。")

    with tabs[2]:
        with st.container(border=True):
            sec_header("💼", "営業データベースとしての活用方法")
            st.markdown("""
本システムは PoC 評価ツールと同時に、公共営業の案件データベースとして継続活用できます。

**プロポーザル勝率分析**
入札方式・自社結果を蓄積することで、「公募型プロポーザルに強い」「価格競争案件は不利」といった
傾向が数値で把握できます。

**先行営業の起点**
履行期間（契約終了日）から逆算し、次回公示の6〜3ヶ月前に担当部署へ
直接アプローチするリマインドに活用できます。

**競合分析**
落札企業・競合欄の蓄積により、ターゲット自治体で頻出する競合企業のパターンが把握でき、
提案戦略の差別化に繋げられます。
            """)


# ─────────────────────────────────────────────────────────────────
#  PAGE: DATA MANAGEMENT
# ─────────────────────────────────────────────────────────────────
elif current_page == "データ管理":
    page_header("データ一括管理・初期化", "CSVインポート ／ データリセット")

    with st.container(border=True):
        sec_header("⬇️", "万能サンプルCSVダウンロード")
        st.caption("このCSVをアップロードするだけでコスト・検索ワード・案件データが一括セットアップされます。")
        sample = [
            {"ID":"SETTING_COST","自治体名":"NJSS初期費用","落札金額(千円)":100000},
            {"ID":"SETTING_COST","自治体名":"NJSS月額費用","落札金額(千円)":50000},
            {"ID":"SETTING_COST","自治体名":"入札王初期費用","落札金額(千円)":0},
            {"ID":"SETTING_COST","自治体名":"入札王月額費用","落札金額(千円)":30000},
            {"ID":"SETTING_COST","自治体名":"平均受注率","落札金額(千円)":25},
            {"ID":"SETTING_COST","自治体名":"平均粗利率","落札金額(千円)":30},
            {"ID":"SETTING_COST","自治体名":"年間想定応札数","落札金額(千円)":50},
            {"ID":"SETTING_WORD","自治体名":"データ分析基盤","案件概要":"150","落札企業":"120"},
            {"ID":"SETTING_WORD","自治体名":"BIツール","案件概要":"80","落札企業":"90"},
            {"ID":1,"自治体名":"東京都","担当部署名":"デジタルサービス局","案件概要":"ダッシュボード構築業務",
             "落札金額(千円)":15000,"NJSS掲載":True,"入札王掲載":False,
             "自社結果":"受注","落札企業":"株式会社テクノサンプル"},
            {"ID":2,"自治体名":"大阪府","担当部署名":"スマートシティ戦略部","案件概要":"BIツールライセンス更新",
             "落札金額(千円)":8000,"NJSS掲載":True,"入札王掲載":True,"自社結果":"失注"},
        ]
        st.download_button(
            "万能サンプルCSVをダウンロード",
            data=pd.DataFrame(sample).to_csv(index=False).encode("utf-8-sig"),
            file_name="database_sample.csv",
            mime="text/csv",
        )

    with st.container(border=True):
        sec_header("⬆️", "CSV 一括インポート")
        uf = st.file_uploader("CSVをアップロード", type="csv")
        if uf:
            im = pd.read_csv(uf, encoding="utf-8-sig")
            st.dataframe(im.head(), use_container_width=True)
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✓  このデータをシステムへ書き込む"):
                try:
                    new_p = []
                    today_str = datetime.date.today().strftime("%Y-%m-%d")
                    for _, row in im.iterrows():
                        tag = str(row.get("ID",""))
                        if tag == "SETTING_COST":
                            item = str(row.get("自治体名",""))
                            val  = int(pd.to_numeric(row.get("落札金額(千円)",0), errors="coerce") or 0)
                            if   "NJSS初期"   in item: st.session_state.costs["n_init"]      = val
                            elif "NJSS月額"   in item: st.session_state.costs["n_month"]     = val
                            elif "入札王初期" in item: st.session_state.costs["k_init"]      = val
                            elif "入札王月額" in item: st.session_state.costs["k_month"]     = val
                            elif "受注率"     in item: st.session_state.costs["win_rate"]    = val
                            elif "粗利率"     in item: st.session_state.costs["margin"]      = val
                            elif "応札数"     in item: st.session_state.costs["annual_bids"] = val
                        elif tag == "SETTING_WORD":
                            w = str(row.get("自治体名",""))
                            if w:
                                if w not in st.session_state.search_words:
                                    st.session_state.search_words.append(w)
                                st.session_state.search_counts[w] = {
                                    "NJSS":  int(pd.to_numeric(row.get("案件概要",0), errors="coerce") or 0),
                                    "入札王": int(pd.to_numeric(row.get("落札企業",0), errors="coerce") or 0),
                                    "登録日": today_str,
                                }
                        else:
                            if pd.notna(row.get("自治体名")) and str(row.get("自治体名")).strip():
                                new_p.append(row)
                    if new_p:
                        save_data(pd.concat([load_data(), pd.DataFrame(new_p)], ignore_index=True))
                    st.success("全データを正常に読み込み・保存しました。")
                except Exception as e:
                    st.error(f"エラー: {e}")

    with st.container(border=True):
        with st.expander("⚠️  危険操作：全データの初期化"):
            st.caption("スプレッドシートの全案件・設定・ワードを完全消去します。この操作は元に戻せません。")
            ok = st.checkbox("すべてのデータを消去することを確認します")
            if st.button("全データを初期化する"):
                if ok:
                    try:
                        save_data(pd.DataFrame(columns=COLS))
                        st.session_state.update({
                            "search_words": [], "search_counts": {},
                            "costs": {
                                "n_init":0, "n_month":0, "n_opt":0,
                                "k_init":0, "k_month":0, "k_opt":0,
                                "margin":20, "win_rate":20, "annual_bids":50,
                            },
                        })
                        st.success("初期化が完了しました。")
                    except Exception as e:
                        st.error(f"エラー: {e}")
                else:
                    st.error("確認チェックを入れてください。")
