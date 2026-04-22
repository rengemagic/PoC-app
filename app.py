import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection
import base64, datetime, re, json

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
        "n_init": 100000, "n_month": 50000, "n_opt": 0,
        "k_init": 0, "k_month": 30000, "k_opt": 0,
        "margin": 20, "win_rate": 20, "annual_bids": 50,
        "labor_search_hour": 1.0,      
        "labor_cost_per_hour": 3000,   
        "marketing_annual": 500000,    
        "tool_boost_rate": 20,         
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
:root {
  --bg:        #F4F7FA; --bg2:       #FFFFFF; --bg3:       #F8FAFC;
  --line:      #E2E8F0; --line2:     #CBD5E1;
  --text:      #1E293B; --muted:     #64748B;
  --sb-bg:     #0D1320; --sb-text:   #8B9EC7; --sb-hover:  #1A2540; --sb-active: #233154;
  --accent:    #0176D3; --green:     #10B981; --red:       #EF4444;
  --radius:    8px; --radius-lg: 12px;
}
html, body, p, label, input, textarea, select, table, th, td { font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", "Hiragino Sans", "Hiragino Kaku Gothic ProN", "Yu Gothic", YuGothic, Arial, sans-serif; color: var(--text); }
h1,h2,h3,h4,h5 { font-weight: 700 !important; color: var(--text); letter-spacing: -0.02em; }
[data-testid="stHeader"] { background-color: transparent !important; }
footer { display: none !important; }
[data-testid="stAppViewContainer"] { background: var(--bg) !important; }
[data-testid="block-container"] { padding: 2rem 2.5rem 4rem !important; max-width: 1400px; }

/* Sidebar */
[data-testid="stSidebar"] { background: var(--sb-bg) !important; border-right: none !important; }
[data-testid="stSidebar"] > div:first-child { padding-top: 0 !important; }
[data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label, [data-testid="stSidebar"] div { color: var(--sb-text) !important; }
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label > div:first-child { display: none !important; }
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label { padding: 12px 16px !important; margin-bottom: 4px !important; border-radius: 8px !important; transition: background 0.15s; cursor: pointer; background: transparent !important; }
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover { background: var(--sb-hover) !important; }
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label[data-checked="true"] { background: var(--sb-active) !important; border-left: 3px solid var(--accent) !important; }
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label p { font-size: 14.5px !important; font-weight: 500 !important; margin: 0 !important; color: var(--sb-text) !important; }
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label[data-checked="true"] p { color: #FFFFFF !important; font-weight: 700 !important; }

/* Buttons & Containers */
.stButton > button, .stFormSubmitButton > button { background: var(--accent) !important; border: none !important; border-radius: var(--radius) !important; font-weight: 600 !important; font-size: 14px !important; color: #FFFFFF !important; transition: all 0.2s !important; box-shadow: 0 4px 6px rgba(1, 118, 211, 0.2) !important; }
.stButton > button p, .stFormSubmitButton > button p { color: #FFFFFF !important; font-weight: 600 !important; margin: 0; }
.stButton > button:hover { background: #015BA7 !important; box-shadow: 0 6px 12px rgba(1, 118, 211, 0.3) !important; transform: translateY(-1px) !important; }
[data-testid="stVerticalBlockBorderWrapper"] { background: var(--bg2) !important; border: 1px solid var(--line) !important; border-radius: var(--radius-lg) !important; padding: 0.5rem !important; box-shadow: 0 4px 12px rgba(0,0,0,0.02) !important; transition: all 0.2s !important; }

/* Custom UI */
.ph { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 0.5rem; padding-bottom: 0.5rem; }
.ph-title { font-size: 1.8rem; font-weight: 800; color: var(--text) !important; letter-spacing: -0.5px; margin: 0; line-height: 1.1; }
.ph-sub { font-size: 14px; color: var(--muted) !important; margin-top: 5px; font-weight: 500; }
.kpi { background: var(--bg2); border: 1px solid var(--line); border-radius: var(--radius-lg); padding: 1.2rem 1rem; text-align: center; margin-bottom: 1rem; }
.kpi-lbl { font-size: 12px; font-weight: 700; color: var(--muted) !important; margin-bottom: 6px; }
.kpi-val { font-size: 2.1rem; font-weight: 700; color: var(--text) !important; line-height: 1; margin-bottom: 6px; }
.kpi-sub { font-size: 11px; color: var(--muted) !important; font-weight: 500; }
.sec { font-size: 1.15rem; font-weight: 700; color: var(--text) !important; margin-bottom: 0.5rem; border-left: 5px solid var(--accent); padding-left: 12px; background: linear-gradient(90deg, rgba(1,118,211,0.06) 0%, rgba(255,255,255,0) 100%); padding-top: 6px; padding-bottom: 6px; border-radius: 0 4px 4px 0; }
.form-div { display: flex; align-items: center; gap: 12px; margin: 1.75rem 0 1.25rem; }
.form-div-line { flex: 1; height: 1px; background: var(--line2); }
.form-div-label { font-size: 12px; font-weight: 700; color: var(--accent) !important; }
.vs-box { background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 8px; padding: 15px; text-align: center; }
.vs-title { font-size: 14px; font-weight: 700; color: #475569; margin-bottom: 10px; }
.vs-item { display: flex; justify-content: space-between; font-size: 13px; color: #334155; margin-bottom: 4px; border-bottom: 1px dashed #E2E8F0; padding-bottom: 2px;}
.vs-total { font-size: 18px; font-weight: 800; color: #0F172A; margin-top: 10px; padding-top: 10px; border-top: 2px solid #CBD5E1; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
#  LOGIN & DATA LAYER (省略せずに維持)
# ─────────────────────────────────────────────────────────────────
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([2, 1.3, 2])
    with col2:
        st.markdown("<br><br><br><h2 style='text-align:center;'>PoC Board</h2>", unsafe_allow_html=True)
        with st.container(border=True):
            uid = st.text_input("ログインID", placeholder="admin")
            pwd = st.text_input("パスワード", type="password")
            if st.button("サインイン", use_container_width=True):
                if uid == "admin" and pwd == "admin": st.session_state.logged_in = True; st.rerun()
    st.stop()

conn = st.connection("gsheets", type=GSheetsConnection)
COLS_BIDS = ["ID","自治体名","担当部署名","案件概要","公示日","入札日","履行期間","入札方式","参加資格","予算(千円)","落札金額(千円)","自社結果","落札企業","競合1","競合2","競合3","仕様書","NJSS掲載","入札王掲載","URL1","URL2","URL3","URL4","URL5", "検索タグ", "備考"]
COLS_SETTINGS = ["種別", "項目名", "値1", "値2", "値3", "値4", "値5"]

def safe_int(val):
    try: return int(float(str(val).replace(',', ''))) if pd.notna(val) and val != "" else 0
    except: return 0

def is_truthy(val): return str(val).upper() in ["TRUE", "1", "1.0", "YES"]

@st.cache_data(ttl="10m")
def load_bids():
    try:
        df = conn.read(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], worksheet="案件データ", ttl="0s")
        return df if "自治体名" in df.columns else pd.DataFrame(columns=COLS_BIDS)
    except: return pd.DataFrame(columns=COLS_BIDS)

def vdf(df): return df[df["自治体名"].notna() & (df["自治体名"].astype(str).str.strip() != "")].copy()

def sync_settings():
    rows = []
    for k, v in st.session_state.costs.items(): rows.append({"種別": "COST", "項目名": k, "値1": v})
    for w in st.session_state.search_words:
        d = st.session_state.search_counts.get(w, {})
        rows.append({"種別": "WORD", "項目名": w, "値1": d.get("NJSS_入札案件",0), "値2": d.get("入札王_入札案件",0), "値3": d.get("NJSS_落札結果",0), "値4": d.get("入札王_落札結果",0)})
    conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], worksheet="設定データ", data=pd.DataFrame(rows, columns=COLS_SETTINGS).fillna(""))

if "settings_loaded" not in st.session_state:
    try: df_set = conn.read(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], worksheet="設定データ", ttl="0s")
    except: df_set = pd.DataFrame()
    if not df_set.empty and "種別" in df_set.columns:
        for _, r in df_set[df_set["種別"] == "COST"].iterrows(): st.session_state.costs[str(r["項目名"])] = safe_int(r["値1"])
    st.session_state.settings_loaded = True

# ─────────────────────────────────────────────────────────────────
#  NEW ROI ENGINE (人力+ﾏｰｹ vs ﾂｰﾙ+ﾏｰｹ)
# ─────────────────────────────────────────────────────────────────
def calc_roi_data():
    df = vdf(load_bids())
    avg_bid = pd.to_numeric(df["落札金額(千円)"], errors="coerce").fillna(0).mean() * 1000 if not df.empty and (pd.to_numeric(df["落札金額(千円)"], errors="coerce").fillna(0) > 0).any() else 0
    c = st.session_state.costs

    # 基本売上（現状）
    base_rev = avg_bid * (c["margin"]/100) * (c["win_rate"]/100) * c["annual_bids"]
    # ツール導入時の売上（捕捉率アップ分）
    boost_rev = base_rev * (1 + c["tool_boost_rate"]/100)
    
    # 共通・変動コスト
    annual_manual_cost = c["labor_cost_per_hour"] * c["labor_search_hour"] * 240
    market_cost = c["marketing_annual"]

    rows = []
    cum_man = 0; cum_nj = 0; cum_ki = 0
    for y in range(1, 6):
        # パターンA: 人力 + マーケティング (ツールなし)
        man_profit = base_rev - (annual_manual_cost + market_cost)
        cum_man += man_profit
        
        # パターンB: NJSS + マーケティング (人力検索はゼロ)
        nj_tool_cost = (c["n_init"] if y==1 else c["n_opt"]) + (c["n_month"] * 12)
        nj_profit = boost_rev - (nj_tool_cost + market_cost)
        cum_nj += nj_profit
        
        # パターンC: 入札王 + マーケティング
        ki_tool_cost = (c["k_init"] if y==1 else c["k_opt"]) + (c["k_month"] * 12)
        ki_profit = boost_rev - (ki_tool_cost + market_cost)
        cum_ki += ki_profit

        rows.append({
            "年度": f"{y}年目",
            "人力+ﾏｰｹ (累積)": int(cum_man),
            "NJSS+ﾏｰｹ (累積)": int(cum_nj),
            "入札王+ﾏｰｹ (累積)": int(cum_ki),
            "NJSS 単年利益": int(nj_profit),
            "人力 単年利益": int(man_profit)
        })

    # 損益分岐月数の計算（月間追加利益による回収）
    man_profit_m = (base_rev - annual_manual_cost - market_cost) / 12
    nj_profit_m  = (boost_rev - (c["n_month"]*12 + market_cost)) / 12
    
    nj_diff_m = nj_profit_m - man_profit_m
    nj_be_months = (c["n_init"] / nj_diff_m) if nj_diff_m > 0 else 9999

    return pd.DataFrame(rows), avg_bid, annual_manual_cost, nj_be_months, nj_diff_m

# ─────────────────────────────────────────────────────────────────
#  UI HELPERS
# ─────────────────────────────────────────────────────────────────
PLY = dict(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=16, r=16, t=28, b=16), legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5))
C1, C2, C3 = "#0176D3", "#14B8A6", "#8B5CF6"

def page_header(title, sub=""):
    st.markdown(f'<div class="ph"><div><div class="ph-title">{title}</div><div class="ph-sub">{sub}</div></div></div><div style="border-bottom: 1px solid var(--line2); margin-bottom: 2rem;"></div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
#  MAIN APP ROUTING (SIDEBAR)
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""<div style="padding:24px 20px 16px;border-bottom:1px solid rgba(255,255,255,0.05);margin-bottom:8px;"><div><div style="font-size:18px;font-weight:800;color:#FFFFFF;letter-spacing:-0.3px;">PoC Board</div><div style="font-size:10px;color:#8B9EC7;letter-spacing:1px;text-transform:uppercase;margin-top:2px;">Evaluation Tool</div></div></div>""", unsafe_allow_html=True)
    menu_options = ["ダッシュボード", "案件データ入力", "ワード検索数", "ROI分析"]
    current_index = menu_options.index(st.session_state.current_page) if st.session_state.current_page in menu_options else 3
    st.session_state.current_page = st.radio("ナビゲーション", menu_options, index=current_index, label_visibility="collapsed")
    current_page = st.session_state.current_page

# ─────────────────────────────────────────────────────────────────
#  PAGE: ROI (完全改修版)
# ─────────────────────────────────────────────────────────────────
if current_page == "ROI分析":
    page_header("事業性・ROI分析", "人力（As-Is）とツール導入時（To-Be）の収益構造の比較")

    df_roi, avg_bid, ann_manual_cost, nj_be_months, nj_diff_m = calc_roi_data()
    c = st.session_state.costs

    col_set1, col_set2 = st.columns([1, 2])
    
    with col_set1:
        st.markdown('<div class="sec">1. 営業・コスト前提条件</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.session_state.costs["annual_bids"] = st.number_input("年間想定応札数（件）", value=int(c["annual_bids"]))
            st.session_state.costs["win_rate"] = st.slider("平均受注率（%）", 0, 100, int(c["win_rate"]))
            st.session_state.costs["margin"] = st.slider("平均粗利率（%）", 0, 100, int(c["margin"]))
            st.session_state.costs["marketing_annual"] = st.number_input("年間マーケティング費用（円）", value=int(c["marketing_annual"]), step=10000, help="DMやテレアポなど、ツールとは別にかかる販促費")
            
            st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
            st.caption("【人力運用時の隠れたコスト】")
            st.session_state.costs["labor_search_hour"] = st.number_input("1日の手動検索時間（h）", value=float(c["labor_search_hour"]), step=0.5)
            st.session_state.costs["labor_cost_per_hour"] = st.number_input("担当者時給（円）", value=int(c["labor_cost_per_hour"]), step=100)
            
            st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
            st.caption("【ツール導入効果と費用】")
            st.session_state.costs["tool_boost_rate"] = st.slider("ツールによる案件捕捉増加率（%）", 0, 100, int(c["tool_boost_rate"]))
            cx1, cx2 = st.columns(2)
            with cx1:
                st.caption("NJSS 費用")
                ni = st.number_input("初期", value=c["n_init"], key="ni", label_visibility="collapsed")
                nm = st.number_input("月額", value=c["n_month"], key="nm", label_visibility="collapsed")
            with cx2:
                st.caption("入札王 費用")
                ki = st.number_input("初期", value=c["k_init"], key="ki", label_visibility="collapsed")
                km = st.number_input("月額", value=c["k_month"], key="km", label_visibility="collapsed")

        if st.button("設定を保存してシミュレーション更新", use_container_width=True, type="primary"):
            st.session_state.costs.update({"n_init":ni,"n_month":nm,"k_init":ki,"k_month":km})
            sync_settings(); st.rerun()

    with col_set2:
        # コスト比較構造（As-Is vs To-Be）のUI
        st.markdown('<div class="sec">2. 収益構造の比較 (1年あたり)</div>', unsafe_allow_html=True)
        v1, v2 = st.columns(2)
        
        base_sales = avg_bid * (c["margin"]/100) * (c["win_rate"]/100) * c["annual_bids"]
        nj_sales = base_sales * (1 + c["tool_boost_rate"]/100)
        market_c = c["marketing_annual"]
        
        with v1:
            st.markdown(f"""
            <div class="vs-box">
                <div class="vs-title">😟 現状（人力 ＋ マーケティング）</div>
                <div class="vs-item"><span>期待売上</span><span>¥{int(base_sales/10000):,}万</span></div>
                <div class="vs-item"><span style="color:#EF4444;">人力検索コスト</span><span style="color:#EF4444;">- ¥{int(ann_manual_cost/10000):,}万</span></div>
                <div class="vs-item"><span style="color:#EF4444;">マーケティング費</span><span style="color:#EF4444;">- ¥{int(market_c/10000):,}万</span></div>
                <div class="vs-total">単年純利益: ¥{int((base_sales - ann_manual_cost - market_c)/10000):,}万</div>
            </div>
            """, unsafe_allow_html=True)
            
        with v2:
            st.markdown(f"""
            <div class="vs-box" style="border-color: {C1}; background: #F0F9FF;">
                <div class="vs-title" style="color: {C1};">🚀 NJSS導入（ツール ＋ マーケティング）</div>
                <div class="vs-item"><span style="color:{C1}; font-weight:bold;">期待売上 (捕捉↑)</span><span style="color:{C1}; font-weight:bold;">¥{int(nj_sales/10000):,}万</span></div>
                <div class="vs-item"><span style="color:#10B981;">人力検索コスト</span><span style="color:#10B981;">¥0 (不要)</span></div>
                <div class="vs-item"><span style="color:#EF4444;">NJSS利用費(月額)</span><span style="color:#EF4444;">- ¥{int((c["n_month"]*12)/10000):,}万</span></div>
                <div class="vs-item"><span style="color:#EF4444;">マーケティング費</span><span style="color:#EF4444;">- ¥{int(market_c/10000):,}万</span></div>
                <div class="vs-total" style="color:{C1};">単年純利益: ¥{int((nj_sales - (c["n_month"]*12) - market_c)/10000):,}万</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # 損益分岐点ハイライト
        st.markdown('<div class="sec">3. 損益分岐点（ペイバック・ピリオド）</div>', unsafe_allow_html=True)
        if nj_diff_m > 0:
            st.success(f"💡 **NJSS導入により、毎月「¥{int(nj_diff_m):,}」の利益が人力運用時より上乗せされます。**\n初期費用(¥{c['n_init']:,})は、導入後 **約 {max(1, int(nj_be_months))}ヶ月** で回収し、それ以降は人力運用を上回る黒字化（投資回収完了）となります。")
        else:
            st.error("⚠️ 現在の設定では、ツールの月額費用が人力運用による削減効果と売上増加を上回っています。受注率や捕捉増加率を見直してください。")

        st.markdown("<br>", unsafe_allow_html=True)

        # 5年ROI グラフ＆テーブル
        st.markdown('<div class="sec">4. 累積純利益シミュレーション（5カ年）</div>', unsafe_allow_html=True)
        
        tab_graph, tab_table = st.tabs(["📈 グラフ表示", "📊 テーブル表示（詳細）"])
        
        with tab_graph:
            fig = px.line(df_roi, x="年度", y=["人力+ﾏｰｹ (累積)", "NJSS+ﾏｰｹ (累積)", "入札王+ﾏｰｹ (累積)"], 
                          color_discrete_map={"人力+ﾏｰｹ (累積)": "#94A3B8", "NJSS+ﾏｰｹ (累積)": C1, "入札王+ﾏｰｹ (累積)": C2})
            fig.update_traces(line_width=3, marker=dict(size=8))
            fig.update_layout(**PLY, hovermode="x unified", yaxis_title="累積純利益 (円)", height=350)
            st.plotly_chart(fig, use_container_width=True)
            
        with tab_table:
            st.caption("単位：円（全コスト差し引き後の手元に残る純利益）")
            # Pandasのスタイル機能を使ってカンマ区切りで見やすく表示
            styled_df = df_roi[["年度", "人力+ﾏｰｹ (累積)", "NJSS+ﾏｰｹ (累積)", "入札王+ﾏｰｹ (累積)"]].style.format({
                "人力+ﾏｰｹ (累積)": "{:,.0f}",
                "NJSS+ﾏｰｹ (累積)": "{:,.0f}",
                "入札王+ﾏｰｹ (累積)": "{:,.0f}"
            })
            st.dataframe(styled_df, hide_index=True, use_container_width=True)

# 他のページ処理は省略（ダッシュボード等のコードはそのまま維持してください）
else:
    st.info("他のページ（ダッシュボード、案件入力など）は既存のコードと結合してご利用ください。")
