import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection
import io, base64, traceback, datetime, json, re

# ─────────────────────────────────────────────
#  PAGE CONFIG & GLOBAL CSS
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="入札PoC Board",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Session init
for k, v in {
    "logged_in": False,
    "search_words": [],
    "search_counts": {},
    "costs": {"n_init": 0, "n_month": 0, "n_opt": 0, "k_init": 0, "k_month": 0,
               "k_opt": 0, "margin": 20, "win_rate": 20, "annual_bids": 50},
    "ocr_result": None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

DARK_SIDEBAR = "#0F172A"
ACCENT = "#0176D3"

# ─── Global CSS ───────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

:root {{
  --accent: {ACCENT};
  --accent-light: #E6F1FB;
  --accent-dark: #014486;
  --sidebar-bg: {DARK_SIDEBAR};
  --text-primary: #0F172A;
  --text-secondary: #64748B;
  --text-muted: #94A3B8;
  --surface: #FFFFFF;
  --surface-alt: #F8FAFC;
  --border: rgba(15,23,42,0.08);
  --radius: 10px;
  --radius-lg: 14px;
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
  --shadow-lg: 0 8px 24px rgba(0,0,0,0.10);
}}

* {{ font-family: 'DM Sans', sans-serif !important; }}

/* ── Hide Streamlit chrome ── */
[data-testid="stHeader"], #MainMenu, footer {{ display: none !important; }}
[data-testid="stAppViewContainer"] {{ background: var(--surface-alt) !important; }}
[data-testid="block-container"] {{ padding: 1.5rem 2rem 3rem !important; max-width: 1360px; }}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
  background: var(--sidebar-bg) !important;
  border-right: none !important;
  box-shadow: 4px 0 20px rgba(0,0,0,0.15) !important;
}}
[data-testid="stSidebar"] * {{ color: #94A3B8 !important; font-size: 14px !important; }}
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label > div:first-child {{ display: none !important; }}
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label {{
  padding: 10px 14px !important; margin-bottom: 2px !important;
  border-radius: 8px !important; background: transparent;
  transition: background 0.15s, color 0.15s; cursor: pointer; width: 100%;
}}
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover {{
  background: rgba(255,255,255,0.07) !important;
}}
[data-testid="stSidebar"] div.stRadio p {{
  color: #CBD5E1 !important; font-size: 13.5px !important; font-weight: 400 !important; margin: 0 !important;
}}
.sidebar-nav-label {{
  color: #475569 !important; font-size: 10px !important; font-weight: 600 !important;
  letter-spacing: 1.2px; text-transform: uppercase; padding: 12px 14px 4px;
}}

/* ── Buttons ── */
div.stButton > button, div[data-testid="stFormSubmitButton"] > button {{
  background: var(--accent) !important; border: none !important; border-radius: 8px !important;
  padding: 0.6rem 1.4rem !important; font-weight: 600 !important; font-size: 14px !important;
  color: #fff !important; transition: background 0.2s, transform 0.15s, box-shadow 0.2s !important;
  box-shadow: 0 2px 8px rgba(1,118,211,0.30) !important; width: 100%;
}}
div.stButton > button p, div[data-testid="stFormSubmitButton"] > button p {{ color: #fff !important; font-weight: 600 !important; }}
div.stButton > button:hover {{ background: var(--accent-dark) !important; transform: translateY(-1px) !important; box-shadow: 0 6px 16px rgba(1,118,211,0.35) !important; }}

/* ── Inputs ── */
div[data-baseweb="input"] > div, div[data-baseweb="textarea"] > div, div[data-baseweb="select"] > div {{
  border: 1px solid var(--border) !important; border-radius: 8px !important;
  background: var(--surface) !important; box-shadow: var(--shadow-sm) !important;
  transition: border-color 0.2s, box-shadow 0.2s !important;
}}
div[data-baseweb="input"] > div:focus-within, div[data-baseweb="textarea"] > div:focus-within {{
  border-color: var(--accent) !important; box-shadow: 0 0 0 3px rgba(1,118,211,0.12) !important;
}}

/* ── Cards (container borders) ── */
[data-testid="stVerticalBlockBorderWrapper"] {{
  background: var(--surface) !important; border: 1px solid var(--border) !important;
  border-radius: var(--radius-lg) !important; box-shadow: var(--shadow-sm) !important;
  transition: box-shadow 0.2s !important; padding: 0.25rem 0.5rem !important;
}}
[data-testid="stVerticalBlockBorderWrapper"]:hover {{
  box-shadow: var(--shadow-md) !important;
}}

/* ── Page header ── */
.page-header {{
  background: var(--surface); border-radius: var(--radius-lg);
  border: 1px solid var(--border); padding: 1.25rem 1.75rem;
  margin-bottom: 1.75rem; box-shadow: var(--shadow-sm);
  display: flex; align-items: center; justify-content: space-between;
}}
.page-header h1 {{
  margin: 0; font-size: 1.5rem !important; font-weight: 700 !important;
  color: var(--text-primary) !important; letter-spacing: -0.3px;
}}
.page-header .sub {{ font-size: 13px; color: var(--text-secondary); margin-top: 3px; }}

/* ── Section title ── */
.section-title {{
  font-size: 14px !important; font-weight: 600 !important; color: var(--text-primary) !important;
  letter-spacing: -0.2px; margin-bottom: 0.75rem !important;
}}

/* ── KPI card ── */
.kpi-card {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 1.1rem 1.25rem;
  box-shadow: var(--shadow-sm); height: 100%;
}}
.kpi-label {{
  font-size: 11px; font-weight: 600; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px;
}}
.kpi-value {{ font-size: 2rem; font-weight: 700; color: var(--accent); line-height: 1; }}
.kpi-sub {{ font-size: 12px; color: var(--text-secondary); margin-top: 5px; }}

/* ── Status badges ── */
.badge {{ display: inline-block; padding: 3px 9px; border-radius: 20px; font-size: 11px; font-weight: 600; }}
.badge-win {{ background: #DCFCE7; color: #166534; }}
.badge-lose {{ background: #FEE2E2; color: #991B1B; }}
.badge-pass {{ background: #F1F5F9; color: #475569; }}

/* ── Tool tags ── */
.tag {{ display: inline-block; padding: 2px 7px; border-radius: 5px; font-size: 11px; font-weight: 600; margin-right: 3px; }}
.tag-nj {{ background: var(--accent-light); color: var(--accent); }}
.tag-ki {{ background: #DCFDF7; color: #0D7565; }}

/* ── Form section header ── */
.form-section {{
  background: var(--surface-alt); border-left: 3px solid var(--accent);
  border-radius: 0 6px 6px 0; padding: 0.5rem 1rem;
  margin: 1.5rem 0 1rem; font-size: 14px; font-weight: 600; color: var(--text-primary);
}}

/* ── Required label ── */
.req-label {{ font-size: 14px; font-weight: 600; color: var(--text-primary); margin-bottom: 3px; }}
.req-badge {{ color: #E02424; font-size: 11px; margin-left: 4px; }}

/* ── OCR panel ── */
.ocr-panel {{
  background: linear-gradient(135deg, #EFF6FF 0%, #F0FDF4 100%);
  border: 1.5px dashed rgba(1,118,211,0.35); border-radius: var(--radius-lg);
  padding: 1.25rem 1.5rem; margin-bottom: 1.5rem;
}}
.ocr-title {{ font-size: 14px; font-weight: 700; color: var(--accent); margin-bottom: 6px; }}
.ocr-sub {{ font-size: 13px; color: var(--text-secondary); }}

/* ── Verdict box ── */
.verdict-box {{
  background: #EFF6FF; border: 1px solid #BFDBFE;
  border-radius: var(--radius); padding: 1rem 1.25rem;
}}
.verdict-title {{ font-size: 15px; font-weight: 700; color: #1D4ED8; margin-bottom: 6px; }}
.verdict-body {{ font-size: 13px; color: #1E40AF; line-height: 1.55; }}

/* ── Plotly chart container ── */
.js-plotly-plot .plotly, .js-plotly-plot .plotly div {{
  font-family: 'DM Sans', sans-serif !important;
}}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  LOGIN SCREEN
# ─────────────────────────────────────────────
if not st.session_state.logged_in:
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background: #0F172A !important; }
    [data-testid="block-container"] { display: flex; align-items: center; justify-content: center; min-height: 90vh; }
    </style>""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
        <div style="background:#1E293B;border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:2.5rem 2rem;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,0.4);">
          <div style="font-size:2rem;margin-bottom:0.5rem;">📊</div>
          <p style="color:#F8FAFC;font-size:1.3rem;font-weight:700;margin:0 0 4px;">入札 PoC Board</p>
          <p style="color:#64748B;font-size:13px;margin:0 0 2rem;">データドリブン入札ツール評価システム</p>
        </div>""", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("<br>", unsafe_allow_html=True)
            user_id = st.text_input("ログインID", placeholder="例: admin").strip()
            pwd = st.text_input("パスワード", type="password", placeholder="パスワードを入力").strip()
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("ログイン　→"):
                if user_id == "admin" and pwd == "admin":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("IDまたはパスワードが間違っています。")
            st.markdown("<br>", unsafe_allow_html=True)
    st.stop()

# ─────────────────────────────────────────────
#  DATA LAYER
# ─────────────────────────────────────────────
conn = st.connection("gsheets", type=GSheetsConnection)
COLS = ["ID","自治体名","担当部署名","案件概要","公示日","入札日","履行期間",
        "入札方式","参加資格","予算(千円)","落札金額(千円)","自社結果",
        "落札企業","競合1","競合2","競合3","仕様書","NJSS掲載","入札王掲載",
        "URL1","URL2","URL3","URL4","URL5"]

@st.cache_data(ttl=0)
def load_data():
    try:
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        df = conn.read(spreadsheet=url, ttl="0s")
        return df if "URL1" in df.columns else pd.DataFrame(columns=COLS)
    except:
        return pd.DataFrame(columns=COLS)

def valid_df(df): return df[df["自治体名"].notna() & (df["自治体名"] != "")]

def calculate_projections():
    df = valid_df(load_data())
    avg_bid = 0
    if not df.empty and "落札金額(千円)" in df.columns:
        nums = pd.to_numeric(df["落札金額(千円)"], errors="coerce").fillna(0)
        avg_bid = nums[nums > 0].mean() * 1000 if (nums > 0).any() else 0
    c = st.session_state.costs
    annual_profit = avg_bid * (c["margin"]/100) * (c["win_rate"]/100) * c["annual_bids"]
    rows = []
    for y in range(6):
        nc = c["n_init"] + (c["n_month"]*12 + c["n_opt"]) * y
        kc = c["k_init"] + (c["k_month"]*12 + c["k_opt"]) * y
        rev = annual_profit * y
        rows.append({"年":y,"NJSS累積コスト":nc,"NJSS利益":rev-nc,"入札王累積コスト":kc,"入札王利益":rev-kc,"累積売上":rev})
    return pd.DataFrame(rows), annual_profit

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def kpi_card(title, value, sub=""):
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">{title}</div>
      <div class="kpi-value">{value}</div>
      {"<div class='kpi-sub'>" + sub + "</div>" if sub else ""}
    </div>""", unsafe_allow_html=True)

def req_label(text):
    st.markdown(f'<div class="req-label">{text} <span class="req-badge">※必須</span></div>', unsafe_allow_html=True)

def page_header(title, subtitle=""):
    st.markdown(f"""
    <div class="page-header">
      <div>
        <h1>{title}</h1>
        {"<div class='sub'>" + subtitle + "</div>" if subtitle else ""}
      </div>
    </div>""", unsafe_allow_html=True)

PLOTLY_LAYOUT = dict(
    template="plotly_white",
    font=dict(family="DM Sans, sans-serif", color="#0F172A"),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=16, r=16, t=24, b=16),
    legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
)

# ─────────────────────────────────────────────
#  OCR HELPER (Google Vision API or fallback)
# ─────────────────────────────────────────────
def try_ocr_with_vision(image_bytes: bytes) -> dict | None:
    """
    Google Cloud Vision API を使った OCR。
    secrets に [google_vision] api_key が設定されている場合のみ動作。
    戻り値: {"自治体名":..., "案件概要":..., ...} or None
    """
    try:
        api_key = st.secrets["google_vision"]["api_key"]
        import requests
        b64 = base64.b64encode(image_bytes).decode()
        payload = {"requests":[{"image":{"content":b64},"features":[{"type":"DOCUMENT_TEXT_DETECTION"}]}]}
        resp = requests.post(f"https://vision.googleapis.com/v1/images:annotate?key={api_key}", json=payload, timeout=20)
        text = resp.json()["responses"][0].get("fullTextAnnotation", {}).get("text", "")

        # ── 簡易フィールド抽出ルール ──
        result = {}
        patterns = {
            "自治体名":   r"(都|道|府|県|市|区|町|村)[^\s　]*",
            "案件概要":   r"(?:業務名|件名|案件名)[　\s：:]+(.+)",
            "予算(千円)": r"(?:予算|限度額|上限)[^\d]*(\d[\d,]+)",
            "入札方式":   r"(公募型プロポーザル|一般競争入札|指名競争入札|随意契約)",
        }
        for field, pat in patterns.items():
            m = re.search(pat, text)
            if m:
                raw = m.group(1) if m.lastindex else m.group(0)
                if field == "予算(千円)":
                    raw = raw.replace(",","")
                    try: raw = str(int(raw) // 1000)
                    except: pass
                result[field] = raw.strip()

        return result if result else None
    except Exception:
        return None

def parse_ocr_image(uploaded_file) -> dict:
    """
    アップロードされた画像/PDFから案件情報を抽出。
    Google Vision API が設定されていない場合はデモ用サンプルを返す。
    """
    if uploaded_file is None:
        return {}
    
    image_bytes = uploaded_file.read()
    result = try_ocr_with_vision(image_bytes)

    if result:
        return result
    
    # ── Vision APIなしのデモ応答 ──
    st.warning("""
    **OCRデモモード（実際の解析なし）**  
    Google Cloud Vision APIキーを `secrets.toml` の `[google_vision] api_key` に設定すると
    実際の仕様書・公告PDF/画像から自動で項目を読み取れます。  
    下記はサンプルデータです。""")
    return {
        "自治体名": "（OCRデモ）東京都",
        "案件概要": "情報システム調達業務",
        "予算(千円)": "5000",
        "入札方式": "公募型プロポーザル",
        "参加資格": "情報処理 Aランク",
    }

# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:20px 16px 14px;border-bottom:1px solid rgba(255,255,255,0.07);">
      <div style="font-size:18px;font-weight:700;color:#F8FAFC;">📊 PoC Board</div>
      <div style="font-size:11px;color:#475569;margin-top:3px;">入札ツール精密評価</div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="sidebar-nav-label">ANALYSIS</div>', unsafe_allow_html=True)
    test_mode = st.toggle("データ管理モード", key="test_mode_toggle")

    menu_options = ["ダッシュボード", "過去案件情報入力", "ワード検索数", "コスト・ROI分析", "詳細マニュアル"]
    if test_mode:
        menu_options.append("データ管理")

    page = st.radio("ページ選択", menu_options, label_visibility="collapsed")

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="padding:0 14px;font-size:11px;color:#334155;line-height:1.5;">
      <div style="font-weight:600;color:#475569;margin-bottom:4px;">利用ガイド</div>
      ① 案件入力 → ② ワード検索 → ③ ROI設定 → ④ ダッシュボードで判定
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("ログアウト"):
        st.session_state.logged_in = False
        st.rerun()

# ─────────────────────────────────────────────
#  PAGE: DASHBOARD
# ─────────────────────────────────────────────
if page == "ダッシュボード":
    page_header("PoC 分析ダッシュボード", "入札ツール導入前検証 — データ統合ビュー")
    df = load_data()
    vdf = valid_df(df)

    if vdf.empty:
        with st.container(border=True):
            st.info("データがありません。「過去案件情報入力」からデータを登録してください。")
        st.stop()

    nj_c = vdf["NJSS掲載"].astype(str).str.upper().isin(["TRUE","1","1.0","YES"]).sum()
    ki_c = vdf["入札王掲載"].astype(str).str.upper().isin(["TRUE","1","1.0","YES"]).sum()
    total = len(vdf)
    p_df, _ = calculate_projections()
    n_p5 = p_df.iloc[-1]["NJSS利益"] if not p_df.empty else 0
    k_p5 = p_df.iloc[-1]["入札王利益"] if not p_df.empty else 0

    # ── KPI row ──
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1: kpi_card("分析対象案件", f"{total}件", "登録済み総案件数")
    with k2: kpi_card("NJSS 網羅率", f"{nj_c/total*100:.1f}%", f"{nj_c}件捕捉")
    with k3: kpi_card("入札王 網羅率", f"{ki_c/total*100:.1f}%", f"{ki_c}件捕捉")
    with k4: kpi_card("NJSS 5年利益", f"{int(n_p5/10000):,}万円", "累積期待利益")
    with k5: kpi_card("入札王 5年利益", f"{int(k_p5/10000):,}万円", "累積期待利益")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Charts row ──
    col_l, col_r = st.columns(2)
    with col_l:
        with st.container(border=True):
            st.markdown('<div class="section-title">案件捕捉数の比較</div>', unsafe_allow_html=True)
            fig = px.bar(
                x=["NJSS", "入札王"], y=[nj_c, ki_c],
                color=["NJSS","入札王"],
                color_discrete_map={"NJSS": ACCENT, "入札王": "#10B981"},
                text=[nj_c, ki_c],
            )
            fig.update_traces(marker_line_width=0, textposition="outside")
            fig.update_layout(**PLOTLY_LAYOUT, showlegend=False, height=260)
            fig.update_yaxes(title="捕捉件数", gridcolor="#F1F5F9")
            fig.update_xaxes(title="")
            st.plotly_chart(fig, use_container_width=True)

    with col_r:
        with st.container(border=True):
            st.markdown('<div class="section-title">競合出現シェア Top 6</div>', unsafe_allow_html=True)
            comp = pd.concat([vdf["落札企業"], vdf["競合1"], vdf["競合2"], vdf["競合3"]])
            comp_df = comp[comp.notna() & (comp != "")].value_counts().reset_index().head(6)
            comp_df.columns = ["企業名","回数"]
            fig2 = px.bar(comp_df, x="回数", y="企業名", orientation="h", text="回数")
            fig2.update_traces(marker_color=ACCENT, marker_line_width=0, textposition="outside")
            fig2.update_layout(**PLOTLY_LAYOUT, showlegend=False, height=260)
            fig2.update_xaxes(title="出現回数", gridcolor="#F1F5F9")
            fig2.update_yaxes(title="")
            st.plotly_chart(fig2, use_container_width=True)

    # ── Keyword chart ──
    with st.container(border=True):
        st.markdown('<div class="section-title">キーワード検索精度比較（実測ヒット件数）</div>', unsafe_allow_html=True)
        if st.session_state.search_words and st.session_state.search_counts:
            sw_data = [{"ワード": w, "NJSS": st.session_state.search_counts.get(w,{}).get("NJSS",0),
                        "入札王": st.session_state.search_counts.get(w,{}).get("入札王",0)}
                       for w in st.session_state.search_words]
            fig3 = px.bar(pd.DataFrame(sw_data), x="ワード", y=["NJSS","入札王"], barmode="group",
                          color_discrete_map={"NJSS": ACCENT, "入札王": "#10B981"})
            fig3.update_traces(marker_line_width=0)
            fig3.update_layout(**PLOTLY_LAYOUT, height=280, legend_title_text="ツール")
            fig3.update_yaxes(title="ヒット件数", gridcolor="#F1F5F9")
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.caption("「ワード検索数」画面からデータを追加してください。")

    # ── ROI forecast ──
    with st.container(border=True):
        st.markdown('<div class="section-title">累積期待利益の予測推移（5カ年）</div>', unsafe_allow_html=True)
        fig4 = px.line(p_df, x="年", y=["NJSS利益","入札王利益"],
                       color_discrete_map={"NJSS利益": ACCENT, "入札王利益": "#10B981"})
        fig4.update_traces(line_width=2.5)
        fig4.update_layout(**PLOTLY_LAYOUT, height=260, legend_title_text="ツール")
        fig4.update_yaxes(title="累積利益 (円)", gridcolor="#F1F5F9")
        fig4.update_xaxes(title="経過年数")
        st.plotly_chart(fig4, use_container_width=True)

    # ── Evaluation report ──
    with st.container(border=True):
        st.markdown('<div class="section-title">項目別評価 & 総合判定レポート</div>', unsafe_allow_html=True)

        cov_diff = nj_c - ki_c
        cov_w = "NJSS" if cov_diff > 0 else "入札王" if cov_diff < 0 else "引き分け"
        nj_sw = sum(1 for v in st.session_state.search_counts.values() if v["NJSS"] > v["入札王"])
        ki_sw = sum(1 for v in st.session_state.search_counts.values() if v["入札王"] > v["NJSS"])
        sw_w = "NJSS" if nj_sw > ki_sw else "入札王" if ki_sw > nj_sw else "引き分け"
        roi_w = "NJSS" if n_p5 > k_p5 else "入札王" if k_p5 > n_p5 else "引き分け"
        nj_score = (cov_w=="NJSS") + (sw_w=="NJSS") + (roi_w=="NJSS")
        ki_score = (cov_w=="入札王") + (sw_w=="入札王") + (roi_w=="入札王")

        nj_cov = nj_c/total*100 if total else 0
        ki_cov = ki_c/total*100 if total else 0
        tot_sw = nj_sw + ki_sw
        nj_s = nj_sw/tot_sw*100 if tot_sw else 50
        ki_s = ki_sw/tot_sw*100 if tot_sw else 50
        mx_roi = max(n_p5, k_p5, 1)
        nj_ps, ki_ps = max(0, n_p5/mx_roi*100), max(0, k_p5/mx_roi*100)

        ec1, ec2 = st.columns([1.3, 1])
        with ec1:
            st.markdown("#### 1. 網羅率（過去案件カバレッジ）")
            st.markdown(f"判定: **{cov_w}** の優位")
            st.caption("過去のターゲット案件をどれだけ取りこぼさず捕捉できているかの評価。")

            st.markdown("#### 2. キーワード検索精度")
            st.markdown(f"判定: **{sw_w}** の優位")
            st.caption("得意領域のキーワードで検索した際のヒット件数と情報収集力の広さ。")

            st.markdown("#### 3. 投資対効果（ROI・5年）")
            st.markdown(f"判定: **{roi_w}** の優位")
            st.caption("利用料・想定受注率・粗利率を加味した5年後累積利益の比較。")

            st.markdown("#### 総合判定")
            if nj_score > ki_score:
                st.markdown('<div class="verdict-box"><div class="verdict-title">推奨ツール：NJSS</div><div class="verdict-body">網羅性・機会損失防止の観点でNJSSが優位。確実な案件捕捉により事業成長への貢献が最も高いと判断されます。</div></div>', unsafe_allow_html=True)
            elif ki_score > nj_score:
                st.markdown('<div class="verdict-box"><div class="verdict-title">推奨ツール：入札王</div><div class="verdict-body">コストパフォーマンスと早期損益分岐点の観点で入札王が優位。ROIの最大化に最適と判断されます。</div></div>', unsafe_allow_html=True)
            else:
                st.info("両者拮抗。UIの使いやすさや営業サポート体制などの定性要素で最終決定してください。")

        with ec2:
            cat = ["網羅率","検索精度","収益性(5年)","網羅率"]
            fig_r = go.Figure()
            fig_r.add_trace(go.Scatterpolar(r=[nj_cov,nj_s,nj_ps,nj_cov], theta=cat, fill="toself", name="NJSS",
                                             line=dict(color=ACCENT, width=2), fillcolor=f"rgba(1,118,211,0.12)"))
            fig_r.add_trace(go.Scatterpolar(r=[ki_cov,ki_s,ki_ps,ki_cov], theta=cat, fill="toself", name="入札王",
                                             line=dict(color="#10B981", width=2, dash="dash"), fillcolor="rgba(16,185,129,0.08)"))
            fig_r.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,100], gridcolor="#E2E8F0"),
                                            angularaxis=dict(gridcolor="#E2E8F0")),
                                 legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"),
                                 paper_bgcolor="rgba(0,0,0,0)", font=dict(family="DM Sans"), height=300, margin=dict(t=20,b=40))
            st.plotly_chart(fig_r, use_container_width=True)

# ─────────────────────────────────────────────
#  PAGE: DATA INPUT + OCR
# ─────────────────────────────────────────────
elif page == "過去案件情報入力":
    page_header("過去案件情報入力", "仕様書・公告のOCR読み取りまたは手動入力")
    df_cur = load_data()
    vdf = valid_df(df_cur).copy()

    # ── OCR Panel ──
    st.markdown("""
    <div class="ocr-panel">
      <div class="ocr-title">📄 仕様書・公告ファイルから自動入力（OCR機能）</div>
      <div class="ocr-sub">PDF・画像をアップロードすると、項目を自動で読み取りフォームに反映します。<br>
      ※ Google Cloud Vision APIキーを <code>secrets.toml</code> に設定することで本番動作します。</div>
    </div>""", unsafe_allow_html=True)

    ocr_file = st.file_uploader("仕様書・公告ファイルをアップロード (PNG / JPG / PDF)", type=["png","jpg","jpeg","pdf"], key="ocr_uploader")
    if ocr_file:
        with st.spinner("OCR処理中..."):
            st.session_state.ocr_result = parse_ocr_image(ocr_file)
        if st.session_state.ocr_result:
            st.success(f"読み取り完了！{len(st.session_state.ocr_result)}項目をフォームに反映しました。")

    ocr = st.session_state.ocr_result or {}

    # ── Manual form ──
    with st.container(border=True):
        with st.form("entry_form", clear_on_submit=True):
            st.markdown('<div class="form-section">基本情報</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                req_label("自治体名・発注機関")
                mun = st.text_input("mun", label_visibility="collapsed", placeholder="例: 横浜市", value=ocr.get("自治体名",""))
            with c2:
                st.markdown('<div class="req-label">担当部署名</div>', unsafe_allow_html=True)
                dep = st.text_input("dep", label_visibility="collapsed", placeholder="例: デジタル統括本部", value=ocr.get("担当部署名",""))
            req_label("案件名・案件概要")
            smm = st.text_input("smm", label_visibility="collapsed", placeholder="例: 交通データ連携基盤構築業務", value=ocr.get("案件概要",""))

            st.markdown('<div class="form-section">スケジュール・要件</div>', unsafe_allow_html=True)
            c3, c4, c5 = st.columns(3)
            pub_d = c3.date_input("公示日", value=None)
            bid_d = c4.date_input("入札日", value=None)
            per_d = c5.text_input("履行期間", placeholder="例: 2025-06-01 〜 2026-03-31", value=ocr.get("履行期間",""))
            c6, c7 = st.columns(2)
            methods = ["","公募型プロポーザル","一般競争入札","指名競争入札","随意契約","その他"]
            ocr_method_idx = methods.index(ocr.get("入札方式","")) if ocr.get("入札方式","") in methods else 0
            method = c6.selectbox("入札方式", methods, index=ocr_method_idx)
            qual = c7.text_input("参加資格", placeholder="例: 情報処理 Aランク", value=ocr.get("参加資格",""))

            st.markdown('<div class="form-section">結果・金額</div>', unsafe_allow_html=True)
            c8, c9, c10 = st.columns(3)
            budget_val = 0
            try: budget_val = int(ocr.get("予算(千円)", 0))
            except: pass
            budget = c8.number_input("予算額 (千円)", min_value=0, step=100, value=budget_val)
            with c9:
                req_label("落札金額 (千円)")
                wbid = st.number_input("wbid", label_visibility="collapsed", min_value=0, step=100)
            our_res = c10.selectbox("自社結果", ["","受注","失注","見送り","辞退"])
            c11, c12 = st.columns(2)
            wnr = c11.text_input("落札企業", placeholder="例: 株式会社テクノサンプル")
            b1  = c12.text_input("競合企業1")
            b2  = c11.text_input("競合企業2")
            b3  = c12.text_input("競合企業3")

            st.markdown('<div class="form-section">ツール掲載確認（PoC用）</div>', unsafe_allow_html=True)
            c13, c14, c15 = st.columns(3)
            spc = c13.checkbox("仕様書あり")
            njl = c14.checkbox("NJSSに掲載")
            kil = c15.checkbox("入札王に掲載")

            st.markdown('<div class="form-section">参考URL</div>', unsafe_allow_html=True)
            c16, c17 = st.columns(2)
            url1 = c16.text_input("URL 1")
            url2 = c17.text_input("URL 2")
            c18, c19 = st.columns(2)
            url3 = c18.text_input("URL 3")
            url4 = c19.text_input("URL 4")
            url5 = st.text_input("URL 5")

            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("この案件を保存する　→"):
                if mun and smm and wbid > 0:
                    new_rec = pd.DataFrame([{
                        "ID": len(vdf)+1, "自治体名": mun, "担当部署名": dep, "案件概要": smm,
                        "公示日": pub_d.strftime("%Y-%m-%d") if pub_d else "",
                        "入札日": bid_d.strftime("%Y-%m-%d") if bid_d else "",
                        "履行期間": per_d, "入札方式": method, "参加資格": qual,
                        "予算(千円)": budget, "落札金額(千円)": wbid, "自社結果": our_res,
                        "落札企業": wnr, "競合1": b1, "競合2": b2, "競合3": b3,
                        "仕様書": spc, "NJSS掲載": njl, "入札王掲載": kil,
                        "URL1": url1, "URL2": url2, "URL3": url3, "URL4": url4, "URL5": url5
                    }])
                    try:
                        conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"],
                                    data=pd.concat([vdf, new_rec], ignore_index=True).fillna(""))
                        st.session_state.ocr_result = None
                        st.success("スプレッドシートへ保存しました。")
                        load_data.clear()
                    except Exception as e:
                        st.error(f"保存に失敗しました: {e}")
                else:
                    st.error("「自治体名」「案件名」「落札金額(1以上)」は必須項目です。")

    # ── Existing data ──
    if not vdf.empty:
        with st.container(border=True):
            st.markdown('<div class="section-title">登録済みデータ一覧</div>', unsafe_allow_html=True)
            st.dataframe(vdf, hide_index=True, use_container_width=True)

# ─────────────────────────────────────────────
#  PAGE: KEYWORD SEARCH
# ─────────────────────────────────────────────
elif page == "ワード検索数":
    page_header("ワード検索数比較", "両ツールで同一キーワードを検索し、ヒット件数を入力してください。")

    with st.container(border=True):
        st.markdown('<div class="section-title">キーワードの追加・管理</div>', unsafe_allow_html=True)
        ca1, ca2, ca3 = st.columns([2, 1, 1])
        new_w = ca1.text_input("キーワード", placeholder="例: BIツール、DX推進", key="kw_input", label_visibility="collapsed")
        if ca2.button("追加"):
            if new_w and new_w not in st.session_state.search_words:
                st.session_state.search_words.append(new_w); st.rerun()
        if ca3.button("リストをクリア"):
            st.session_state.search_words = []; st.session_state.search_counts = {}; st.rerun()

    with st.container(border=True):
        st.markdown('<div class="section-title">ヒット件数テーブル（直接編集可）</div>', unsafe_allow_html=True)
        if st.session_state.search_words:
            df_sw = pd.DataFrame([{
                "検索ワード": w,
                "NJSS (件)": st.session_state.search_counts.get(w,{}).get("NJSS",0),
                "入札王 (件)": st.session_state.search_counts.get(w,{}).get("入札王",0)
            } for w in st.session_state.search_words])
            edited = st.data_editor(df_sw, num_rows="dynamic", use_container_width=True, hide_index=True, key="kw_editor")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("テーブルの検索件数を保存する"):
                st.session_state.search_words = edited["検索ワード"].dropna().tolist()
                st.session_state.search_counts = {
                    row["検索ワード"]: {"NJSS": int(row.get("NJSS (件)", 0) or 0), "入札王": int(row.get("入札王 (件)", 0) or 0)}
                    for _, row in edited.iterrows() if pd.notna(row["検索ワード"])
                }
                st.success("検索件数を保存しました。ダッシュボードに反映されます。")
        else:
            st.info("キーワードを追加すると、件数入力テーブルが表示されます。")

# ─────────────────────────────────────────────
#  PAGE: ROI ANALYSIS
# ─────────────────────────────────────────────
elif page == "コスト・ROI分析":
    page_header("コスト・ROI分析設定", "費用と営業指標を設定してシミュレーションを実行します。")

    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### NJSS 費用見積")
            n_i = st.number_input("初期費用 (円)", value=st.session_state.costs["n_init"], key="ni")
            n_m = st.number_input("月額費用 (円)", value=st.session_state.costs["n_month"], key="nm")
            n_o = st.number_input("年間オプション (円)", value=st.session_state.costs["n_opt"], key="no")
            st.metric("NJSS 初年度合計", f"{n_i + n_m*12 + n_o:,} 円")
        with c2:
            st.markdown("#### 入札王 費用見積")
            k_i = st.number_input("初期費用 (円)", value=st.session_state.costs["k_init"], key="ki")
            k_m = st.number_input("月額費用 (円)", value=st.session_state.costs["k_month"], key="km")
            k_o = st.number_input("年間オプション (円)", value=st.session_state.costs["k_opt"], key="ko")
            st.metric("入札王 初年度合計", f"{k_i + k_m*12 + k_o:,} 円")

        st.markdown("---")
        st.markdown("#### 自社営業シミュレーション設定")
        cs1, cs2, cs3 = st.columns(3)
        wr = cs1.number_input("平均受注率 (%)", value=st.session_state.costs["win_rate"])
        mg = cs2.number_input("平均粗利率 (%)", value=st.session_state.costs["margin"])
        ab = cs3.number_input("年間想定応札数 (件)", value=st.session_state.costs["annual_bids"])
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("設定を保存してグラフを更新"):
            st.session_state.costs.update({"n_init":n_i,"n_month":n_m,"n_opt":n_o,
                                            "k_init":k_i,"k_month":k_m,"k_opt":k_o,
                                            "margin":mg,"win_rate":wr,"annual_bids":ab})
            st.success("設定を更新しました。")
            st.rerun()

    p_df, _ = calculate_projections()

    with st.container(border=True):
        st.markdown('<div class="section-title">損益分岐点・5年収益推移シミュレーション</div>', unsafe_allow_html=True)
        fig_bep = go.Figure()
        fig_bep.add_trace(go.Scatter(x=p_df["年"], y=p_df["累積売上"], name="累積売上期待値",
                                     line=dict(color="#10B981", width=3)))
        fig_bep.add_trace(go.Scatter(x=p_df["年"], y=p_df["NJSS累積コスト"], name="NJSS累積コスト",
                                     line=dict(color=ACCENT, dash="dash", width=2)))
        fig_bep.add_trace(go.Scatter(x=p_df["年"], y=p_df["入札王累積コスト"], name="入札王累積コスト",
                                     line=dict(color="#0D9488", dash="dot", width=2)))
        fig_bep.update_layout(**PLOTLY_LAYOUT, height=320)
        fig_bep.update_yaxes(title="金額 (円)", gridcolor="#F1F5F9")
        fig_bep.update_xaxes(title="経過年数")
        st.plotly_chart(fig_bep, use_container_width=True)

    with st.container(border=True):
        st.markdown('<div class="section-title">各年の累積利益比較</div>', unsafe_allow_html=True)
        fig_p = px.bar(p_df, x="年", y=["NJSS利益","入札王利益"], barmode="group",
                       color_discrete_map={"NJSS利益": ACCENT, "入札王利益": "#10B981"})
        fig_p.update_traces(marker_line_width=0)
        fig_p.update_layout(**PLOTLY_LAYOUT, height=300)
        fig_p.update_yaxes(title="累積利益 (円)", gridcolor="#F1F5F9")
        st.plotly_chart(fig_p, use_container_width=True)

# ─────────────────────────────────────────────
#  PAGE: MANUAL
# ─────────────────────────────────────────────
elif page == "詳細マニュアル":
    page_header("自走式 PoC評価マニュアル", "検証フローと本システムの活用ガイド")
    with st.container(border=True):
        st.markdown("""
        本システムは、入札情報サービス（NJSS・入札王等）の導入前検証（PoC）において、
        感覚ではなく**データに基づいた合理的な決裁**を行うための分析ツール兼営業データベースです。

        ---

        ### Step 1：過去案件データの準備
        「過去案件情報入力」画面に、自社がターゲットとする案件を10〜20件入力します。
        **OCR機能**を使えば、仕様書や公告PDFをアップロードするだけで主要項目が自動入力されます。

        ### Step 2：ツールでの検索実測
        各ツールのトライアルアカウントを使用し、Step 1で入力した案件が実際に検索して見つかるか確認し、
        「NJSS掲載」「入札王掲載」のチェックを入れます。

        ### Step 3：キーワード検索ボリュームの確認
        「ワード検索数」画面で、自社の得意領域キーワードで検索した結果のヒット件数を入力します。

        ### Step 4：コストシミュレーションの設定
        「コスト・ROI分析」画面で、見積金額・平均受注率・粗利率を入力し、シミュレーションを実行します。

        ### Step 5：ダッシュボードで最終判断
        「ダッシュボード」でレーダーチャートと推奨テキストを確認し、スクリーンショットを稟議書に添付してください。

        ---

        ### 営業データベースとしての活用
        - **プロポーザル勝率分析**：企画重視 vs 価格競争の強みを分析
        - **先行営業**：履行期間から逆算し次回公示前にアプローチ
        - **競合把握**：落札企業・競合欄から主要プレーヤーを把握
        """)

# ─────────────────────────────────────────────
#  PAGE: DATA MANAGEMENT
# ─────────────────────────────────────────────
elif page == "データ管理":
    page_header("データ一括管理・初期化", "CSV一括インポートとデータリセット")

    with st.container(border=True):
        st.markdown('<div class="section-title">万能サンプルCSVダウンロード</div>', unsafe_allow_html=True)
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
            {"ID":1,"自治体名":"東京都","案件概要":"ダッシュボード構築業務","落札金額(千円)":15000,"NJSS掲載":True,"入札王掲載":False,"自社結果":"受注","落札企業":"株式会社テクノサンプル"},
            {"ID":2,"自治体名":"大阪府","案件概要":"BIツールライセンス更新","落札金額(千円)":8000,"NJSS掲載":True,"入札王掲載":True,"自社結果":"失注"},
        ]
        st.download_button("万能サンプルCSVをダウンロード",
                           data=pd.DataFrame(sample).to_csv(index=False).encode("utf-8-sig"),
                           file_name="database_sample.csv", mime="text/csv")

    with st.container(border=True):
        st.markdown('<div class="section-title">CSV一括インポート</div>', unsafe_allow_html=True)
        up_f = st.file_uploader("CSVをアップロード", type="csv")
        if up_f:
            im_df = pd.read_csv(up_f, encoding="utf-8-sig")
            st.dataframe(im_df.head(), use_container_width=True)
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("このデータをシステムへ書き込む"):
                try:
                    new_projects = []
                    for _, row in im_df.iterrows():
                        tag = str(row.get("ID",""))
                        if tag == "SETTING_COST":
                            item = str(row.get("自治体名",""))
                            val = int(pd.to_numeric(row.get("落札金額(千円)",0), errors="coerce") or 0)
                            if "NJSS初期" in item: st.session_state.costs["n_init"] = val
                            elif "NJSS月額" in item: st.session_state.costs["n_month"] = val
                            elif "入札王初期" in item: st.session_state.costs["k_init"] = val
                            elif "入札王月額" in item: st.session_state.costs["k_month"] = val
                            elif "受注率" in item: st.session_state.costs["win_rate"] = val
                            elif "粗利率" in item: st.session_state.costs["margin"] = val
                            elif "応札数" in item: st.session_state.costs["annual_bids"] = val
                        elif tag == "SETTING_WORD":
                            w = str(row.get("自治体名",""))
                            if w:
                                if w not in st.session_state.search_words: st.session_state.search_words.append(w)
                                nj = int(pd.to_numeric(row.get("案件概要",0), errors="coerce") or 0)
                                ki = int(pd.to_numeric(row.get("落札企業",0), errors="coerce") or 0)
                                st.session_state.search_counts[w] = {"NJSS": nj, "入札王": ki}
                        else:
                            if pd.notna(row.get("自治体名")) and str(row.get("自治体名")).strip():
                                new_projects.append(row)
                    if new_projects:
                        final = pd.concat([load_data(), pd.DataFrame(new_projects)], ignore_index=True).fillna("")
                        conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=final)
                        load_data.clear()
                    st.success("全データを正常に読み込み・保存しました。")
                except Exception as e:
                    st.error(f"保存失敗: {e}")

    with st.container(border=True):
        with st.expander("⚠️ 危険操作：全データの初期化"):
            st.caption("スプレッドシートの全案件・コスト設定・検索ワードを完全消去します。この操作は元に戻せません。")
            confirm = st.checkbox("本当にすべてのデータを消去してよろしいですか？")
            if st.button("全データを初期化する"):
                if confirm:
                    try:
                        conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"],
                                    data=pd.DataFrame(columns=COLS))
                        st.session_state.update({"search_words":[], "search_counts":{},
                                                  "costs":{"n_init":0,"n_month":0,"n_opt":0,"k_init":0,"k_month":0,"k_opt":0,"margin":20,"win_rate":20,"annual_bids":50}})
                        load_data.clear()
                        st.success("初期化が完了しました。")
                    except Exception as e:
                        st.error(f"初期化失敗: {e}")
                else:
                    st.error("確認チェックボックスを先にチェックしてください。")
