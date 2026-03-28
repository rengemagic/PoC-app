import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection
import base64, datetime, re

# ─────────────────────────────────────────────────────────────────
#  PAGE CONFIG  ※ must be first Streamlit call
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="入札 PoC Board",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────
#  SESSION STATE INIT
# ─────────────────────────────────────────────────────────────────
_defaults = {
    "logged_in": False,
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
#  GLOBAL CSS  — dark fintech / data-viz aesthetic
#  Font stack: Syne (display) + Geist Mono (numbers) + Outfit (body)
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=Outfit:wght@300;400;500;600&family=Geist+Mono:wght@400;500&display=swap');

/* ── CSS Variables ───────────────────────────────────────────── */
:root {
  --bg:        #080C14;
  --bg2:       #0D1320;
  --bg3:       #131B2E;
  --bg4:       #1A2540;
  --line:      rgba(255,255,255,0.07);
  --line2:     rgba(255,255,255,0.13);
  --text:      #E8EDF5;
  --muted:     #6B7A99;
  --hint:      #3D4F70;
  --accent:    #3B82F6;
  --accent2:   #06B6D4;
  --green:     #10B981;
  --amber:     #F59E0B;
  --red:       #EF4444;
  --radius:    10px;
  --radius-lg: 16px;
}

/* ── Reset / Base ────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="st-"], p, div, span, label {
  font-family: 'Outfit', sans-serif !important;
  color: var(--text) !important;
}
h1,h2,h3,h4,h5 { font-family: 'Syne', sans-serif !important; font-weight: 700 !important; }

/* ── Hide Streamlit chrome ───────────────────────────────────── */
[data-testid="stHeader"],
[data-testid="stToolbar"],
#MainMenu, footer { display: none !important; }

/* ── App background ──────────────────────────────────────────── */
[data-testid="stAppViewContainer"] {
  background: var(--bg) !important;
}
[data-testid="block-container"] {
  padding: 2rem 2.5rem 4rem !important;
  max-width: 1400px;
}

/* ── Sidebar ─────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: var(--bg2) !important;
  border-right: 1px solid var(--line) !important;
}
[data-testid="stSidebar"] > div:first-child {
  padding-top: 0 !important;
}
/* sidebar text override */
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div { color: var(--muted) !important; }

/* Radio nav items */
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label > div:first-child {
  display: none !important;
}
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label {
  padding: 10px 16px !important;
  margin-bottom: 2px !important;
  border-radius: 8px !important;
  transition: background 0.15s;
  cursor: pointer;
}
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover {
  background: var(--bg4) !important;
}
[data-testid="stSidebar"] div.stRadio p {
  font-family: 'Outfit', sans-serif !important;
  font-size: 13.5px !important;
  font-weight: 500 !important;
  color: #8B9EC7 !important;
  margin: 0 !important;
}

/* Toggle */
[data-testid="stSidebar"] .stToggle span { color: var(--muted) !important; }

/* ── Buttons ─────────────────────────────────────────────────── */
div.stButton > button,
div[data-testid="stFormSubmitButton"] > button {
  background: var(--accent) !important;
  border: none !important;
  border-radius: 8px !important;
  padding: 0.6rem 1.5rem !important;
  font-family: 'Outfit', sans-serif !important;
  font-weight: 600 !important;
  font-size: 14px !important;
  color: #fff !important;
  letter-spacing: 0.3px;
  transition: all 0.2s !important;
  box-shadow: 0 0 0 0 rgba(59,130,246,0);
  width: 100%;
}
div.stButton > button p,
div[data-testid="stFormSubmitButton"] > button p {
  color: #fff !important;
  font-weight: 600 !important;
}
div.stButton > button:hover {
  background: #2563EB !important;
  box-shadow: 0 0 24px rgba(59,130,246,0.4) !important;
  transform: translateY(-1px) !important;
}

/* ── Form inputs ─────────────────────────────────────────────── */
div[data-baseweb="input"] > div,
div[data-baseweb="textarea"] > div,
div[data-baseweb="select"] > div {
  background: var(--bg3) !important;
  border: 1px solid var(--line2) !important;
  border-radius: 8px !important;
}
div[data-baseweb="input"] > div:focus-within,
div[data-baseweb="textarea"] > div:focus-within {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important;
}
input, textarea, select {
  color: var(--text) !important;
  font-family: 'Outfit', sans-serif !important;
}

/* ── Streamlit containers ────────────────────────────────────── */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--bg2) !important;
  border: 1px solid var(--line) !important;
  border-radius: var(--radius-lg) !important;
  padding: 0.5rem !important;
  transition: border-color 0.2s, box-shadow 0.2s !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
  border-color: var(--line2) !important;
  box-shadow: 0 4px 24px rgba(0,0,0,0.3) !important;
}

/* ── Dataframe ───────────────────────────────────────────────── */
[data-testid="stDataFrame"] { border-radius: var(--radius) !important; }

/* ── Alerts ──────────────────────────────────────────────────── */
[data-testid="stAlert"] {
  background: var(--bg3) !important;
  border-radius: var(--radius) !important;
  border-left: 3px solid var(--accent) !important;
}

/* ── Number input ────────────────────────────────────────────── */
[data-testid="stNumberInput"] input { color: var(--text) !important; }

/* ── Selectbox ───────────────────────────────────────────────── */
[data-baseweb="select"] * { background: var(--bg3) !important; color: var(--text) !important; }

/* ── Metric ──────────────────────────────────────────────────── */
[data-testid="stMetric"] {
  background: var(--bg3);
  border-radius: var(--radius);
  padding: 1rem;
  border: 1px solid var(--line);
}
[data-testid="stMetricLabel"] { color: var(--muted) !important; font-size: 11px !important; }
[data-testid="stMetricValue"] { font-family: 'Geist Mono', monospace !important; color: var(--accent) !important; }

/* ── Checkbox ────────────────────────────────────────────────── */
[data-testid="stCheckbox"] span { color: var(--text) !important; }

/* ── Expander ────────────────────────────────────────────────── */
[data-testid="stExpander"] {
  background: var(--bg3) !important;
  border: 1px solid var(--line) !important;
  border-radius: var(--radius) !important;
}

/* ── Tabs ─────────────────────────────────────────────────────── */
[data-testid="stTabs"] button {
  font-family: 'Outfit', sans-serif !important;
  color: var(--muted) !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
  color: var(--accent) !important;
  border-bottom-color: var(--accent) !important;
}

/* ══════════════════════════════════════════════════════════════
   CUSTOM COMPONENT STYLES
══════════════════════════════════════════════════════════════ */

/* Page header */
.ph {
  display: flex; align-items: flex-start; justify-content: space-between;
  margin-bottom: 2rem; padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--line);
}
.ph-title {
  font-family: 'Syne', sans-serif; font-size: 1.75rem; font-weight: 800;
  color: var(--text) !important; letter-spacing: -0.5px; margin: 0;
  line-height: 1.1;
}
.ph-sub { font-size: 13px; color: var(--muted) !important; margin-top: 5px; }
.ph-badge {
  background: var(--bg4); border: 1px solid var(--line2);
  border-radius: 20px; padding: 4px 12px;
  font-size: 11px; font-weight: 600; color: var(--accent) !important;
  letter-spacing: 0.5px; text-transform: uppercase;
}

/* KPI cards */
.kpi-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 1.75rem; }
.kpi {
  background: var(--bg3); border: 1px solid var(--line);
  border-radius: var(--radius-lg); padding: 1.25rem 1.25rem 1rem;
  position: relative; overflow: hidden;
  transition: border-color 0.2s, transform 0.2s;
}
.kpi::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0;
  height: 2px; background: linear-gradient(90deg, var(--accent), var(--accent2));
  opacity: 0;  transition: opacity 0.2s;
}
.kpi:hover { border-color: var(--line2); transform: translateY(-2px); }
.kpi:hover::before { opacity: 1; }
.kpi-lbl {
  font-size: 10px; font-weight: 600; letter-spacing: 1px;
  text-transform: uppercase; color: var(--muted) !important; margin-bottom: 10px;
}
.kpi-val {
  font-family: 'Geist Mono', monospace; font-size: 2.1rem; font-weight: 500;
  color: var(--text) !important; line-height: 1; letter-spacing: -1px;
}
.kpi-val .unit { font-size: 1rem; color: var(--muted) !important; margin-left: 3px; }
.kpi-sub { font-size: 11px; color: var(--muted) !important; margin-top: 8px; }
.kpi-tag {
  display: inline-block; margin-top: 8px; padding: 2px 8px;
  border-radius: 4px; font-size: 10px; font-weight: 700;
}
.tag-up { background: rgba(16,185,129,0.15); color: var(--green) !important; }
.tag-dn { background: rgba(239,68,68,0.12); color: var(--red) !important; }
.tag-neu { background: var(--bg4); color: var(--muted) !important; }

/* Section header */
.sec {
  font-family: 'Syne', sans-serif; font-size: 1rem; font-weight: 700;
  color: var(--text) !important; margin-bottom: 1rem; letter-spacing: -0.2px;
}
.sec-sm {
  font-size: 11px; font-weight: 600; letter-spacing: 1px;
  text-transform: uppercase; color: var(--muted) !important;
  margin-bottom: 0.75rem; padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--line);
}

/* Form section dividers */
.form-div {
  display: flex; align-items: center; gap: 12px; margin: 1.75rem 0 1.25rem;
}
.form-div-line { flex: 1; height: 1px; background: var(--line); }
.form-div-label {
  font-size: 11px; font-weight: 700; letter-spacing: 1.5px;
  text-transform: uppercase; color: var(--accent) !important;
  white-space: nowrap;
}

/* Required label */
.rl { font-size: 13px; font-weight: 600; color: var(--text) !important; margin-bottom: 4px; }
.rl .req { color: #EF4444 !important; font-size: 11px; margin-left: 5px; }

/* Status pills */
.pill { display: inline-flex; align-items: center; gap: 5px; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; }
.pill::before { content: ''; width: 5px; height: 5px; border-radius: 50%; display: inline-block; }
.pill-win  { background: rgba(16,185,129,0.12); color: var(--green) !important; }
.pill-win::before  { background: var(--green); }
.pill-lose { background: rgba(239,68,68,0.10); color: var(--red) !important; }
.pill-lose::before { background: var(--red); }
.pill-skip { background: var(--bg4); color: var(--muted) !important; }
.pill-skip::before { background: var(--hint); }

/* Tool tags */
.ttag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 700; margin-right: 3px; }
.ttag-nj { background: rgba(59,130,246,0.15); color: #60A5FA !important; }
.ttag-ki { background: rgba(6,182,212,0.12); color: #22D3EE !important; }

/* OCR panel */
.ocr-box {
  background: linear-gradient(135deg, rgba(59,130,246,0.06), rgba(6,182,212,0.04));
  border: 1px dashed rgba(59,130,246,0.35);
  border-radius: var(--radius-lg); padding: 1.5rem;
  margin-bottom: 1.5rem;
}
.ocr-title { font-family: 'Syne',sans-serif; font-size: 1rem; font-weight: 700; color: var(--accent) !important; margin-bottom: 6px; }
.ocr-sub { font-size: 13px; color: var(--muted) !important; line-height: 1.6; }

/* Code block */
.code-block {
  background: var(--bg); border: 1px solid var(--line2);
  border-radius: var(--radius); padding: 1rem 1.25rem;
  font-family: 'Geist Mono', monospace; font-size: 12px;
  color: #93C5FD !important; line-height: 1.7; overflow-x: auto;
  white-space: pre; margin: 0.75rem 0;
}

/* Verdict */
.verdict {
  background: linear-gradient(135deg, rgba(59,130,246,0.08), rgba(6,182,212,0.05));
  border: 1px solid rgba(59,130,246,0.3); border-radius: var(--radius-lg);
  padding: 1.25rem 1.5rem;
}
.verdict-title { font-family:'Syne',sans-serif; font-size:1.1rem; font-weight:800; color: var(--accent) !important; margin-bottom:6px; }
.verdict-body { font-size:13px; color: var(--muted) !important; line-height:1.6; }

/* Step list for manual */
.step { display:flex; gap:16px; margin-bottom:1.5rem; }
.step-num {
  width:32px; height:32px; border-radius:50%; border:1px solid var(--accent);
  display:flex; align-items:center; justify-content:center; flex-shrink:0;
  font-family:'Geist Mono',monospace; font-size:13px; font-weight:500;
  color: var(--accent) !important;
}
.step-body h4 { font-family:'Syne',sans-serif; font-size:14px; font-weight:700; color:var(--text) !important; margin:0 0 4px; }
.step-body p { font-size:13px; color:var(--muted) !important; margin:0; line-height:1.55; }

/* Login page */
.login-wrap {
  min-height:85vh; display:flex; align-items:center; justify-content:center;
}
.login-card {
  background:var(--bg2); border:1px solid var(--line2); border-radius:20px;
  padding:2.5rem 2rem; width:100%; max-width:420px; text-align:center;
}
.login-icon { font-size:2.5rem; margin-bottom:1rem; }
.login-title { font-family:'Syne',sans-serif; font-size:1.6rem; font-weight:800; color:var(--text) !important; margin-bottom:4px; }
.login-sub { font-size:13px; color:var(--muted) !important; margin-bottom:2rem; }

</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
#  LOGIN
# ─────────────────────────────────────────────────────────────────
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown("""
        <div style="min-height:80vh;display:flex;align-items:center;justify-content:center;">
          <div style="width:100%;">
            <div style="text-align:center;margin-bottom:2rem;">
              <div style="font-size:2.5rem;margin-bottom:1rem;">⬡</div>
              <div style="font-family:'Syne',sans-serif;font-size:1.8rem;font-weight:800;color:#E8EDF5;letter-spacing:-0.5px;">入札 PoC Board</div>
              <div style="font-size:13px;color:#6B7A99;margin-top:6px;">データドリブン入札ツール評価プラットフォーム</div>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("<br>", unsafe_allow_html=True)
            uid = st.text_input("ログインID", placeholder="admin").strip()
            pwd = st.text_input("パスワード", type="password", placeholder="パスワードを入力").strip()
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("サインイン　⟶"):
                if uid == "admin" and pwd == "admin":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("IDまたはパスワードが正しくありません。")
            st.markdown("<br>", unsafe_allow_html=True)
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
        rows.append({"年": y, "NJSS累積コスト": nc, "NJSS利益": rev - nc,
                     "入札王累積コスト": kc, "入札王利益": rev - kc, "累積売上": rev})
    return pd.DataFrame(rows), ap


# ─────────────────────────────────────────────────────────────────
#  PLOTLY THEME
# ─────────────────────────────────────────────────────────────────
PLY = dict(
    template="plotly_dark",
    font=dict(family="Outfit, sans-serif", color="#8B9EC7"),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=16, r=16, t=28, b=16),
    legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5,
                font=dict(size=11), bgcolor="rgba(0,0,0,0)"),
)
C1, C2, C3 = "#3B82F6", "#06B6D4", "#10B981"


# ─────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────
def page_header(title, sub="", badge=""):
    b = f'<span class="ph-badge">{badge}</span>' if badge else ""
    s = f'<div class="ph-sub">{sub}</div>' if sub else ""
    st.markdown(f"""
    <div class="ph">
      <div>
        <div class="ph-title">{title}</div>
        {s}
      </div>
      {b}
    </div>""", unsafe_allow_html=True)

def kpi(label, value, unit="", sub="", tag="", tag_type="neu"):
    t = f'<div class="kpi-tag tag-{tag_type}">{tag}</div>' if tag else ""
    s = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    u = f'<span class="unit">{unit}</span>' if unit else ""
    st.markdown(f"""
    <div class="kpi">
      <div class="kpi-lbl">{label}</div>
      <div class="kpi-val">{value}{u}</div>
      {s}{t}
    </div>""", unsafe_allow_html=True)

def req_label(text):
    st.markdown(f'<div class="rl">{text}<span class="req">必須</span></div>', unsafe_allow_html=True)

def form_div(text):
    st.markdown(f'<div class="form-div"><div class="form-div-line"></div><div class="form-div-label">{text}</div><div class="form-div-line"></div></div>', unsafe_allow_html=True)

def sec(text):
    st.markdown(f'<div class="sec">{text}</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
#  OCR  (Google Vision API or demo)
# ─────────────────────────────────────────────────────────────────
def ocr_extract(uploaded_file) -> dict:
    if uploaded_file is None:
        return {}
    raw = uploaded_file.read()
    # ── Try Google Vision ──
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
                    try:
                        raw_v = str(int(raw_v.replace(",", "")) // 1000)
                    except:
                        pass
                result[field] = raw_v
        return result if result else _demo_ocr()
    except Exception:
        return _demo_ocr()

def _demo_ocr():
    st.warning("**OCRデモモード** — Google Vision APIキー未設定のためサンプルデータを表示しています。")
    return {
        "自治体名": "（デモ）東京都",
        "案件概要": "情報システム調達支援業務",
        "予算(千円)": "5000",
        "入札方式": "公募型プロポーザル",
        "参加資格": "情報処理 Aランク",
    }


# ─────────────────────────────────────────────────────────────────
#  SIDEBAR  ※ ハンバーガーメニューで閉じても選択状態を保持
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    # ロゴ
    st.markdown("""
    <div style="padding:24px 20px 16px;border-bottom:1px solid rgba(255,255,255,0.07);margin-bottom:8px;">
      <div style="display:flex;align-items:center;gap:10px;">
        <div style="font-size:22px;">⬡</div>
        <div>
          <div style="font-family:'Syne',sans-serif;font-size:16px;font-weight:800;color:#E8EDF5;letter-spacing:-0.3px;">PoC Board</div>
          <div style="font-size:10px;color:#3D4F70;letter-spacing:1px;text-transform:uppercase;">入札ツール評価</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div style="font-size:10px;font-weight:700;letter-spacing:1.5px;color:#3D4F70;text-transform:uppercase;padding:12px 20px 4px;">Navigation</div>', unsafe_allow_html=True)

    menu_options = ["ダッシュボード", "案件データ入力", "ワード検索数", "ROI分析", "マニュアル"]

    test_mode = st.toggle("管理モード", key="admin_toggle")
    if test_mode:
        menu_options.append("データ管理")

    # ※ ハンバーガーで閉じても st.session_state でページ選択が保持される
    if "current_page" not in st.session_state:
        st.session_state.current_page = menu_options[0]

    page = st.radio(
        "ページ",
        menu_options,
        key="nav_radio",
        label_visibility="collapsed",
    )
    st.session_state.current_page = page

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="padding:0 20px;font-size:11px;color:#3D4F70;line-height:1.8;">
      <div style="font-weight:700;color:#6B7A99;margin-bottom:6px;">検証フロー</div>
      1. 案件入力 → 2. ワード検索 → 3. ROI設定 → 4. ダッシュボード確認
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("ログアウト"):
        st.session_state.logged_in = False
        st.rerun()


# ─────────────────────────────────────────────────────────────────
#  PAGE: DASHBOARD
# ─────────────────────────────────────────────────────────────────
if page == "ダッシュボード":
    page_header("PoC Dashboard", "入札ツール導入前検証 — データ統合ビュー", "LIVE")

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

    # ── KPI row ──
    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: kpi("対象案件数", total, "件", sub="登録済み総案件")
    with c2: kpi("NJSS 網羅率", f"{nj_c/total*100:.1f}", "%", sub=f"{nj_c}件捕捉", tag="NJSS", tag_type="up" if nj_c >= ki_c else "dn")
    with c3: kpi("入札王 網羅率", f"{ki_c/total*100:.1f}", "%", sub=f"{ki_c}件捕捉", tag="入札王", tag_type="up" if ki_c >= nj_c else "dn")
    with c4: kpi("NJSS 5年利益", f"{int(n_p5/10000):,}", "万円", sub="累積期待利益", tag_type="neu")
    with c5: kpi("入札王 5年利益", f"{int(k_p5/10000):,}", "万円", sub="累積期待利益", tag_type="neu")

    # ── Row 1: bar charts ──
    r1l, r1r = st.columns(2)
    with r1l:
        with st.container(border=True):
            sec("案件捕捉数の比較")
            fig = px.bar(
                x=["NJSS","入札王"], y=[nj_c, ki_c],
                color=["NJSS","入札王"],
                color_discrete_map={"NJSS": C1, "入札王": C2},
                text=[nj_c, ki_c],
            )
            fig.update_traces(marker_line_width=0, textposition="outside", textfont_size=13)
            fig.update_layout(**PLY, showlegend=False, height=240)
            fig.update_yaxes(title="", gridcolor="rgba(255,255,255,0.05)", zeroline=False)
            fig.update_xaxes(title="")
            st.plotly_chart(fig, use_container_width=True)

    with r1r:
        with st.container(border=True):
            sec("競合出現シェア")
            comp = pd.concat([vd["落札企業"], vd["競合1"], vd["競合2"], vd["競合3"]])
            comp_df = comp[comp.notna() & (comp != "")].value_counts().head(6).reset_index()
            comp_df.columns = ["企業名", "回数"]
            fig2 = px.bar(comp_df, x="回数", y="企業名", orientation="h",
                          text="回数", color_discrete_sequence=[C1])
            fig2.update_traces(marker_line_width=0, textposition="outside", textfont_size=11)
            fig2.update_layout(**PLY, showlegend=False, height=240)
            fig2.update_xaxes(title="", gridcolor="rgba(255,255,255,0.05)", zeroline=False)
            fig2.update_yaxes(title="")
            st.plotly_chart(fig2, use_container_width=True)

    # ── Row 2: keyword + ROI ──
    r2l, r2r = st.columns([1.1, 0.9])
    with r2l:
        with st.container(border=True):
            sec("キーワード検索精度比較")
            if st.session_state.search_words and st.session_state.search_counts:
                sw_df = pd.DataFrame([
                    {"ワード": w,
                     "NJSS": st.session_state.search_counts.get(w,{}).get("NJSS",0),
                     "入札王": st.session_state.search_counts.get(w,{}).get("入札王",0)}
                    for w in st.session_state.search_words
                ])
                fig3 = px.bar(sw_df, x="ワード", y=["NJSS","入札王"], barmode="group",
                              color_discrete_map={"NJSS": C1, "入札王": C2})
                fig3.update_traces(marker_line_width=0)
                fig3.update_layout(**PLY, height=260, legend_title_text="")
                fig3.update_yaxes(title="ヒット件数", gridcolor="rgba(255,255,255,0.05)", zeroline=False)
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.caption("「ワード検索数」画面からデータを追加してください。")

    with r2r:
        with st.container(border=True):
            sec("総合評価レーダー")
            cov_w = "NJSS" if nj_c > ki_c else "入札王" if ki_c > nj_c else "同等"
            nj_sw = sum(1 for v in st.session_state.search_counts.values() if v.get("NJSS",0) > v.get("入札王",0))
            ki_sw = sum(1 for v in st.session_state.search_counts.values() if v.get("入札王",0) > v.get("NJSS",0))
            sw_w  = "NJSS" if nj_sw > ki_sw else "入札王" if ki_sw > nj_sw else "同等"
            roi_w = "NJSS" if n_p5 > k_p5 else "入札王" if k_p5 > n_p5 else "同等"

            nj_cov = nj_c/total*100 if total else 0
            ki_cov = ki_c/total*100 if total else 0
            tot_sw = nj_sw + ki_sw
            nj_s   = nj_sw/tot_sw*100 if tot_sw else 50
            ki_s   = ki_sw/tot_sw*100 if tot_sw else 50
            mx     = max(n_p5, k_p5, 1)
            nj_ps, ki_ps = max(0, n_p5/mx*100), max(0, k_p5/mx*100)

            cats = ["網羅率","検索精度","5年ROI","網羅率"]
            fig_r = go.Figure()
            fig_r.add_trace(go.Scatterpolar(
                r=[nj_cov,nj_s,nj_ps,nj_cov], theta=cats, fill="toself", name="NJSS",
                line=dict(color=C1, width=2), fillcolor="rgba(59,130,246,0.12)"))
            fig_r.add_trace(go.Scatterpolar(
                r=[ki_cov,ki_s,ki_ps,ki_cov], theta=cats, fill="toself", name="入札王",
                line=dict(color=C2, width=2, dash="dash"), fillcolor="rgba(6,182,212,0.08)"))
            fig_r.update_layout(
                polar=dict(
                    bgcolor="rgba(0,0,0,0)",
                    radialaxis=dict(visible=True, range=[0,100], gridcolor="rgba(255,255,255,0.08)", color="#3D4F70"),
                    angularaxis=dict(gridcolor="rgba(255,255,255,0.08)", color="#6B7A99"),
                ),
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Outfit,sans-serif", color="#6B7A99"),
                legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center", bgcolor="rgba(0,0,0,0)"),
                height=240, margin=dict(t=16,b=36,l=16,r=16),
            )
            st.plotly_chart(fig_r, use_container_width=True)

    # ── Verdict ──
    with st.container(border=True):
        sec("総合判定レポート")
        nj_sc = (cov_w=="NJSS") + (sw_w=="NJSS") + (roi_w=="NJSS")
        ki_sc = (cov_w=="入札王") + (sw_w=="入札王") + (roi_w=="入札王")

        v1, v2, v3 = st.columns(3)
        with v1:
            label = f"{'✦ ' if cov_w=='NJSS' else ''}NJSS" if cov_w=="NJSS" else f"{'✦ ' if cov_w=='入札王' else ''}入札王" if cov_w=="入札王" else "同等"
            color = C1 if cov_w=="NJSS" else C2 if cov_w=="入札王" else "#6B7A99"
            st.markdown(f'<div style="font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#6B7A99;margin-bottom:8px;">① 網羅率</div><div style="font-size:1.5rem;font-weight:800;font-family:\'Syne\',sans-serif;color:{color};">{label}</div><div style="font-size:12px;color:#6B7A99;margin-top:4px;">NJSS {int(nj_cov)}% / 入札王 {int(ki_cov)}%</div>', unsafe_allow_html=True)
        with v2:
            label2 = sw_w if sw_w != "同等" else "同等"
            color2 = C1 if sw_w=="NJSS" else C2 if sw_w=="入札王" else "#6B7A99"
            st.markdown(f'<div style="font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#6B7A99;margin-bottom:8px;">② 検索精度</div><div style="font-size:1.5rem;font-weight:800;font-family:\'Syne\',sans-serif;color:{color2};">{label2}</div><div style="font-size:12px;color:#6B7A99;margin-top:4px;">優位ワード数で比較</div>', unsafe_allow_html=True)
        with v3:
            label3 = roi_w if roi_w != "同等" else "同等"
            color3 = C1 if roi_w=="NJSS" else C2 if roi_w=="入札王" else "#6B7A99"
            st.markdown(f'<div style="font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#6B7A99;margin-bottom:8px;">③ 5年ROI</div><div style="font-size:1.5rem;font-weight:800;font-family:\'Syne\',sans-serif;color:{color3};">{label3}</div><div style="font-size:12px;color:#6B7A99;margin-top:4px;">NJSS {int(n_p5/10000):,}万 / 入札王 {int(k_p5/10000):,}万</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if nj_sc > ki_sc:
            st.markdown(f'<div class="verdict"><div class="verdict-title">最終推奨ツール：NJSS ({nj_sc}/3項目)</div><div class="verdict-body">各検証データを総合した結果、NJSSの導入を推奨します。過去案件の網羅性と機会損失防止の観点で優位性が確認されました。</div></div>', unsafe_allow_html=True)
        elif ki_sc > nj_sc:
            st.markdown(f'<div class="verdict"><div class="verdict-title">最終推奨ツール：入札王 ({ki_sc}/3項目)</div><div class="verdict-body">各検証データを総合した結果、入札王の導入を推奨します。コストパフォーマンスと早期損益分岐点の優位性により、ROI最大化が期待できます。</div></div>', unsafe_allow_html=True)
        else:
            st.info("両者拮抗 (引き分け)。UIの使いやすさや営業サポート体制など定性要素で最終判断してください。")

    # ── ROI forecast ──
    with st.container(border=True):
        sec("累積期待利益の予測推移（5カ年）")
        fig4 = px.line(p_df, x="年", y=["NJSS利益","入札王利益"],
                       color_discrete_map={"NJSS利益": C1, "入札王利益": C2})
        fig4.update_traces(line_width=2.5)
        fig4.update_layout(**PLY, height=250)
        fig4.update_yaxes(title="累積利益 (円)", gridcolor="rgba(255,255,255,0.05)", zeroline=False)
        fig4.update_xaxes(title="経過年数")
        st.plotly_chart(fig4, use_container_width=True)


# ─────────────────────────────────────────────────────────────────
#  PAGE: DATA INPUT + OCR
# ─────────────────────────────────────────────────────────────────
elif page == "案件データ入力":
    page_header("案件データ入力", "仕様書・公告OCR読み取り + 手動入力")

    # OCR box
    st.markdown("""
    <div class="ocr-box">
      <div class="ocr-title">📄 仕様書・公告ファイルから自動入力（OCR）</div>
      <div class="ocr-sub">
        PNG / JPG / PDF をアップロードすると主要項目を自動解析してフォームへ反映します。<br>
        Google Cloud Vision API を設定すると実際のファイルから読み取れます。<br>
        未設定の場合はデモモードで動作します。設定方法は「マニュアル」を参照。
      </div>
    </div>""", unsafe_allow_html=True)

    ocr_file = st.file_uploader(
        "ファイルをアップロード（PNG / JPG / PDF）",
        type=["png","jpg","jpeg","pdf"],
        key="ocr_up",
    )
    if ocr_file:
        with st.spinner("OCR解析中..."):
            st.session_state.ocr_result = ocr_extract(ocr_file)
        if st.session_state.ocr_result:
            st.success(f"{len(st.session_state.ocr_result)} 項目を読み取りました。フォームに反映しています。")

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
                                    placeholder="例: 横浜市", value=ocr.get("自治体名",""))
            with c2:
                st.markdown('<div class="rl">担当部署名</div>', unsafe_allow_html=True)
                dep = st.text_input("dep", label_visibility="collapsed",
                                    placeholder="例: デジタル統括本部", value=ocr.get("担当部署名",""))
            req_label("案件名・案件概要")
            smm = st.text_input("smm", label_visibility="collapsed",
                                placeholder="例: 交通データ連携基盤構築業務", value=ocr.get("案件概要",""))

            form_div("スケジュール・要件")
            c3,c4,c5 = st.columns(3)
            pub_d  = c3.date_input("公示日", value=None)
            bid_d  = c4.date_input("入札日", value=None)
            per_d  = c5.text_input("履行期間", placeholder="2025-06-01 〜 2026-03-31",
                                   value=ocr.get("履行期間",""))
            c6,c7  = st.columns(2)
            methods = ["","公募型プロポーザル","一般競争入札","指名競争入札","随意契約","その他"]
            m_idx  = methods.index(ocr.get("入札方式","")) if ocr.get("入札方式","") in methods else 0
            method = c6.selectbox("入札方式", methods, index=m_idx)
            qual   = c7.text_input("参加資格", placeholder="情報処理 Aランク",
                                   value=ocr.get("参加資格",""))

            form_div("結果・金額")
            c8,c9,c10 = st.columns(3)
            bv = 0
            try: bv = int(ocr.get("予算(千円)", 0))
            except: pass
            budget   = c8.number_input("予算額 (千円)", min_value=0, step=100, value=bv)
            with c9:
                req_label("落札金額 (千円)")
                wbid = st.number_input("wbid", label_visibility="collapsed", min_value=0, step=100)
            our_res  = c10.selectbox("自社結果", ["","受注","失注","見送り","辞退"])
            c11,c12  = st.columns(2)
            wnr = c11.text_input("落札企業")
            b1  = c12.text_input("競合1")
            b2  = c11.text_input("競合2")
            b3  = c12.text_input("競合3")

            form_div("ツール掲載確認（PoC）")
            st.caption("両ツールで見つかった場合は両方チェック")
            cx1,cx2,cx3 = st.columns(3)
            spc = cx1.checkbox("仕様書あり")
            njl = cx2.checkbox("NJSSに掲載")
            kil = cx3.checkbox("入札王に掲載")

            form_div("参考URL")
            cu1,cu2 = st.columns(2)
            url1 = cu1.text_input("URL 1")
            url2 = cu2.text_input("URL 2")
            cu3,cu4 = st.columns(2)
            url3 = cu3.text_input("URL 3")
            url4 = cu4.text_input("URL 4")
            url5 = st.text_input("URL 5")

            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("この案件を保存する　→"):
                if mun and smm and wbid > 0:
                    new_rec = pd.DataFrame([{
                        "ID": len(vd)+1, "自治体名": mun, "担当部署名": dep, "案件概要": smm,
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
                    st.error("「自治体名」「案件名」「落札金額(1以上)」は必須です。")

    if not vd.empty:
        with st.container(border=True):
            sec("登録済みデータ一覧")
            st.dataframe(vd, hide_index=True, use_container_width=True)


# ─────────────────────────────────────────────────────────────────
#  PAGE: KEYWORD
# ─────────────────────────────────────────────────────────────────
elif page == "ワード検索数":
    page_header("ワード検索数比較", "同一キーワードで両ツールを実測→件数を入力")

    with st.container(border=True):
        sec("キーワードの追加")
        ca1,ca2,ca3 = st.columns([2,1,1])
        nw = ca1.text_input("キーワード", placeholder="例: BIツール、DX推進", label_visibility="collapsed")
        if ca2.button("追加"):
            if nw and nw not in st.session_state.search_words:
                st.session_state.search_words.append(nw); st.rerun()
        if ca3.button("クリア"):
            st.session_state.search_words = []; st.session_state.search_counts = {}; st.rerun()

    with st.container(border=True):
        sec("ヒット件数テーブル（セル直接編集可）")
        if st.session_state.search_words:
            df_sw = pd.DataFrame([{
                "検索ワード": w,
                "NJSS (件)":  st.session_state.search_counts.get(w,{}).get("NJSS",0),
                "入札王 (件)": st.session_state.search_counts.get(w,{}).get("入札王",0),
            } for w in st.session_state.search_words])
            edited = st.data_editor(df_sw, num_rows="dynamic", use_container_width=True, hide_index=True, key="kw_ed")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("件数を保存してダッシュボードへ反映"):
                st.session_state.search_words = edited["検索ワード"].dropna().tolist()
                st.session_state.search_counts = {
                    row["検索ワード"]: {
                        "NJSS":  int(row.get("NJSS (件)",0)  or 0),
                        "入札王": int(row.get("入札王 (件)",0) or 0),
                    }
                    for _, row in edited.iterrows() if pd.notna(row["検索ワード"])
                }
                st.success("保存しました。")
        else:
            st.info("上の欄からキーワードを追加してください。")


# ─────────────────────────────────────────────────────────────────
#  PAGE: ROI
# ─────────────────────────────────────────────────────────────────
elif page == "ROI分析":
    page_header("コスト・ROI分析設定", "費用と営業指標を設定してシミュレーション")

    with st.container(border=True):
        c1,c2 = st.columns(2)
        with c1:
            st.markdown("#### NJSS 費用見積")
            ni = st.number_input("初期費用 (円)", value=st.session_state.costs["n_init"], key="ni")
            nm = st.number_input("月額費用 (円)", value=st.session_state.costs["n_month"], key="nm")
            no = st.number_input("年間オプション (円)", value=st.session_state.costs["n_opt"], key="no")
            st.metric("初年度合計", f"¥{ni+nm*12+no:,}")
        with c2:
            st.markdown("#### 入札王 費用見積")
            ki = st.number_input("初期費用 (円)", value=st.session_state.costs["k_init"], key="ki")
            km = st.number_input("月額費用 (円)", value=st.session_state.costs["k_month"], key="km")
            ko = st.number_input("年間オプション (円)", value=st.session_state.costs["k_opt"], key="ko")
            st.metric("初年度合計", f"¥{ki+km*12+ko:,}")

        st.markdown("---")
        st.markdown("#### 営業シミュレーション設定")
        s1,s2,s3 = st.columns(3)
        wr = s1.number_input("平均受注率 (%)", value=st.session_state.costs["win_rate"])
        mg = s2.number_input("平均粗利率 (%)", value=st.session_state.costs["margin"])
        ab = s3.number_input("年間想定応札数 (件)", value=st.session_state.costs["annual_bids"])
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("設定を保存してグラフを更新"):
            st.session_state.costs.update({"n_init":ni,"n_month":nm,"n_opt":no,
                                            "k_init":ki,"k_month":km,"k_opt":ko,
                                            "margin":mg,"win_rate":wr,"annual_bids":ab})
            st.success("更新しました。"); st.rerun()

    p_df, _ = calc_proj()

    with st.container(border=True):
        sec("損益分岐点 & 5年収益推移")
        fb = go.Figure()
        fb.add_trace(go.Scatter(x=p_df["年"], y=p_df["累積売上"], name="累積売上期待値",
                                line=dict(color=C3, width=3)))
        fb.add_trace(go.Scatter(x=p_df["年"], y=p_df["NJSS累積コスト"], name="NJSS累積コスト",
                                line=dict(color=C1, dash="dash", width=2)))
        fb.add_trace(go.Scatter(x=p_df["年"], y=p_df["入札王累積コスト"], name="入札王累積コスト",
                                line=dict(color=C2, dash="dot", width=2)))
        fb.update_layout(**PLY, height=300)
        fb.update_yaxes(title="金額 (円)", gridcolor="rgba(255,255,255,0.05)", zeroline=False)
        fb.update_xaxes(title="経過年数")
        st.plotly_chart(fb, use_container_width=True)

    with st.container(border=True):
        sec("各年の累積利益比較")
        fp = px.bar(p_df, x="年", y=["NJSS利益","入札王利益"], barmode="group",
                    color_discrete_map={"NJSS利益": C1, "入札王利益": C2})
        fp.update_traces(marker_line_width=0)
        fp.update_layout(**PLY, height=280)
        fp.update_yaxes(title="累積利益 (円)", gridcolor="rgba(255,255,255,0.05)", zeroline=False)
        st.plotly_chart(fp, use_container_width=True)


# ─────────────────────────────────────────────────────────────────
#  PAGE: MANUAL
# ─────────────────────────────────────────────────────────────────
elif page == "マニュアル":
    page_header("自走式 PoC評価マニュアル", "検証フロー・OCR設定ガイド")

    tabs = st.tabs(["📋 検証フロー", "📄 OCR設定方法", "💼 営業DB活用"])

    with tabs[0]:
        with st.container(border=True):
            for i, (title, body) in enumerate([
                ("過去案件データの準備",
                 "「案件データ入力」画面に、自社ターゲット案件を10〜20件入力します。仕様書PDFのOCR読み取りも活用できます。"),
                ("ツールでの検索実測",
                 "各ツールのトライアルアカウントで案件を検索し、見つかった場合は「NJSS掲載」「入札王掲載」にチェックを入れます。"),
                ("キーワード検索ボリューム確認",
                 "「ワード検索数」画面で得意領域のキーワードを入力し、ヒット件数を記録・保存します。"),
                ("コストシミュレーション設定",
                 "「ROI分析」画面で各ツールの見積金額・自社の受注率・粗利率を入力してシミュレーションを実行します。"),
                ("ダッシュボードで最終判断",
                 "「ダッシュボード」でレーダーチャートと推奨テキストを確認し、スクリーンショットを稟議書に添付します。"),
            ], 1):
                st.markdown(f"""
                <div class="step">
                  <div class="step-num">{i}</div>
                  <div class="step-body"><h4>{title}</h4><p>{body}</p></div>
                </div>""", unsafe_allow_html=True)

    with tabs[1]:
        with st.container(border=True):
            st.markdown("""
            <div class="sec">Google Cloud Vision API の設定方法</div>
            """, unsafe_allow_html=True)

            st.markdown("**① Google Cloud Console でプロジェクトを作成**")
            st.markdown("https://console.cloud.google.com/ にアクセスし、新規プロジェクトを作成します。")

            st.markdown("**② Cloud Vision API を有効化**")
            st.markdown("「APIとサービス」→「ライブラリ」→ `Cloud Vision API` を検索して「有効にする」をクリック。")

            st.markdown("**③ APIキーを発行**")
            st.markdown("「APIとサービス」→「認証情報」→「認証情報を作成」→「APIキー」でキーを発行。")

            st.markdown("**④ `secrets.toml` にキーを追記**")
            st.markdown("Streamlit アプリのルートディレクトリまたは Streamlit Cloud の Secrets 設定に以下を追加：")
            st.markdown("""
            <div class="code-block">[google_vision]
api_key = "AIzaSy＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿"</div>
            """, unsafe_allow_html=True)

            st.markdown("**Streamlit Cloud の場合（ローカルファイル不要）**")
            st.markdown("""
            <div class="code-block">Streamlit Cloud ダッシュボード
  → アプリ選択 → Settings → Secrets タブ
  → 上記の [google_vision] ブロックを貼り付けて「Save」</div>
            """, unsafe_allow_html=True)

            st.markdown("**⑤ 動作確認**")
            st.markdown("「案件データ入力」画面でPNGまたはPDFをアップロードし、項目が自動入力されれば設定完了です。")

            st.info("APIキーの利用料金：Vision API は月1,000リクエストまで無料。仕様書1件＝1リクエストのため、通常のPoC用途では無料枠内で収まります。")

            st.markdown("**よくあるエラーと対処**")
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                st.error("403 Forbidden → APIが有効化されていません。②を再確認してください。")
            with col_e2:
                st.error("KeyError: google_vision → secrets.toml のセクション名が正しいか確認してください。")

    with tabs[2]:
        with st.container(border=True):
            st.markdown("""
            #### 営業データベースとしての活用方法

            本システムは PoC 評価ツールと同時に、公共営業の案件データベースとして継続活用できます。

            **プロポーザル勝率分析**  
            入札方式・自社結果を蓄積することで、「公募型プロポーザルに強い」「価格競争案件は不利」といった傾向が数値で把握できます。

            **先行営業の起点**  
            履行期間（契約終了日）から逆算し、次回公示の6〜3ヶ月前に担当部署へ直接アプローチするリマインドに活用できます。

            **競合分析**  
            落札企業・競合欄の蓄積により、ターゲット自治体で頻出する競合企業のパターンが把握でき、提案戦略の差別化に繋げられます。
            """)


# ─────────────────────────────────────────────────────────────────
#  PAGE: DATA MANAGEMENT
# ─────────────────────────────────────────────────────────────────
elif page == "データ管理":
    page_header("データ一括管理・初期化", "CSVインポート / データリセット", "ADMIN")

    with st.container(border=True):
        sec("万能サンプルCSVダウンロード")
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
             "落札金額(千円)":15000,"NJSS掲載":True,"入札王掲載":False,"自社結果":"受注","落札企業":"株式会社テクノサンプル"},
            {"ID":2,"自治体名":"大阪府","担当部署名":"スマートシティ戦略部","案件概要":"BIツールライセンス更新",
             "落札金額(千円)":8000,"NJSS掲載":True,"入札王掲載":True,"自社結果":"失注"},
        ]
        st.download_button(
            "万能サンプルCSVをダウンロード",
            data=pd.DataFrame(sample).to_csv(index=False).encode("utf-8-sig"),
            file_name="database_sample.csv", mime="text/csv",
        )

    with st.container(border=True):
        sec("CSV一括インポート")
        uf = st.file_uploader("CSVをアップロード", type="csv")
        if uf:
            im = pd.read_csv(uf, encoding="utf-8-sig")
            st.dataframe(im.head(), use_container_width=True)
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("このデータを書き込む"):
                try:
                    new_p = []
                    for _, row in im.iterrows():
                        tag = str(row.get("ID",""))
                        if tag == "SETTING_COST":
                            item = str(row.get("自治体名",""))
                            val  = int(pd.to_numeric(row.get("落札金額(千円)",0), errors="coerce") or 0)
                            if "NJSS初期"  in item: st.session_state.costs["n_init"]     = val
                            elif "NJSS月額" in item: st.session_state.costs["n_month"]   = val
                            elif "入札王初期" in item: st.session_state.costs["k_init"]  = val
                            elif "入札王月額" in item: st.session_state.costs["k_month"] = val
                            elif "受注率"  in item: st.session_state.costs["win_rate"]   = val
                            elif "粗利率"  in item: st.session_state.costs["margin"]     = val
                            elif "応札数"  in item: st.session_state.costs["annual_bids"]= val
                        elif tag == "SETTING_WORD":
                            w = str(row.get("自治体名",""))
                            if w:
                                if w not in st.session_state.search_words:
                                    st.session_state.search_words.append(w)
                                st.session_state.search_counts[w] = {
                                    "NJSS":  int(pd.to_numeric(row.get("案件概要",0), errors="coerce") or 0),
                                    "入札王": int(pd.to_numeric(row.get("落札企業",0), errors="coerce") or 0),
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
        with st.expander("⚠️ 危険操作：全データの初期化"):
            st.caption("スプレッドシートの全案件・設定・ワードを完全消去します。元に戻せません。")
            ok = st.checkbox("すべてのデータを消去することを確認します")
            if st.button("全データを初期化する"):
                if ok:
                    try:
                        save_data(pd.DataFrame(columns=COLS))
                        st.session_state.update({
                            "search_words": [], "search_counts": {},
                            "costs": {"n_init":0,"n_month":0,"n_opt":0,"k_init":0,"k_month":0,
                                      "k_opt":0,"margin":20,"win_rate":20,"annual_bids":50},
                        })
                        st.success("初期化完了。")
                    except Exception as e:
                        st.error(f"エラー: {e}")
                else:
                    st.error("確認チェックを入れてください。")
