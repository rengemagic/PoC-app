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
        "margin": 30, "win_rate": 20, "annual_bids": 30,
        "labor_search_hour": 1.5,      
        "tool_labor_search_hour": 0.5, 
        "labor_cost_per_hour": 3000,   
        "labor_days_per_year": 240,    
        "marketing_annual": 500000,    
        "tool_bid_increase_rate": 40,  
        "tool_win_rate_boost": 5,      
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
[data-testid="stSidebar"] { background: var(--sb-bg) !important; border-right: none !important; }
[data-testid="stSidebar"] > div:first-child { padding-top: 0 !important; }
[data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label, [data-testid="stSidebar"] div { color: var(--sb-text) !important; }
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label > div:first-child { display: none !important; }
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label { padding: 12px 16px !important; margin-bottom: 4px !important; border-radius: 8px !important; transition: background 0.15s; cursor: pointer; background: transparent !important; }
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover { background: var(--sb-hover) !important; }
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label[data-checked="true"] { background: var(--sb-active) !important; border-left: 3px solid var(--accent) !important; }
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label p { font-size: 14.5px !important; font-weight: 500 !important; margin: 0 !important; color: var(--sb-text) !important; }
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label[data-checked="true"] p { color: #FFFFFF !important; font-weight: 700 !important; }
.stButton > button, .stFormSubmitButton > button { background: var(--accent) !important; border: none !important; border-radius: var(--radius) !important; font-weight: 600 !important; font-size: 14px !important; color: #FFFFFF !important; transition: all 0.2s !important; box-shadow: 0 4px 6px rgba(1, 118, 211, 0.2) !important; }
.stButton > button p, .stFormSubmitButton > button p { color: #FFFFFF !important; font-weight: 600 !important; margin: 0; }
.stButton > button:hover { background: #015BA7 !important; box-shadow: 0 6px 12px rgba(1, 118, 211, 0.3) !important; transform: translateY(-1px) !important; }
[data-testid="stVerticalBlockBorderWrapper"] { background: var(--bg2) !important; border: 1px solid var(--line) !important; border-radius: var(--radius-lg) !important; padding: 0.5rem !important; box-shadow: 0 4px 12px rgba(0,0,0,0.02) !important; transition: all 0.2s !important; }
.ph { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 0.5rem; padding-bottom: 0.5rem; }
.ph-title { font-size: 1.8rem; font-weight: 800; color: var(--text) !important; letter-spacing: -0.5px; margin: 0; line-height: 1.1; }
.ph-sub { font-size: 14px; color: var(--muted) !important; margin-top: 5px; font-weight: 500; }
.sec { font-size: 1.15rem; font-weight: 700; color: var(--text) !important; margin-bottom: 0.5rem; border-left: 5px solid var(--accent); padding-left: 12px; background: linear-gradient(90deg, rgba(1,118,211,0.06) 0%, rgba(255,255,255,0) 100%); padding-top: 6px; padding-bottom: 6px; border-radius: 0 4px 4px 0; }
.form-div { display: flex; align-items: center; gap: 12px; margin: 1.75rem 0 1.25rem; }
.form-div-line { flex: 1; height: 1px; background: var(--line2); }
.form-div-label { font-size: 12px; font-weight: 700; color: var(--accent) !important; }
.rl { font-size: 13px; font-weight: 600; color: var(--text) !important; margin-bottom: 4px; }
.rl .req { color: #EF4444 !important; font-size: 11px; margin-left: 5px; }

/* ダッシュボード用 KPIカード */
.kpi { background: var(--bg2); border: 1px solid var(--line); border-radius: var(--radius-lg); padding: 1.2rem 1rem; text-align: center; margin-bottom: 1rem; }
.kpi-lbl { font-size: 12px; font-weight: 700; color: var(--muted) !important; margin-bottom: 6px; }
.kpi-val { font-size: 2.1rem; font-weight: 700; color: var(--text) !important; line-height: 1; margin-bottom: 6px; }
.kpi-sub { font-size: 11px; color: var(--muted) !important; font-weight: 500; }
.kpi-tag { display: inline-block; margin-top: 8px; padding: 3px 10px; border-radius: 4px; font-size: 11px; font-weight: 700; }
.tag-up { background: rgba(16,185,129,0.15); color: var(--green) !important; }
.tag-dn { background: rgba(239,68,68,0.12); color: var(--red) !important; }
.tag-neu { background: var(--bg3); color: var(--muted) !important; }

/* Fancy Card UI（ROI分析ページ用） */
.fancy-card { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 22px 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03); text-align: center; transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.2s cubic-bezier(0.4, 0, 0.2, 1); height: 100%; display: flex; flex-direction: column; justify-content: center; margin-bottom: 1rem;}
.fancy-card:hover { transform: translateY(-4px); box-shadow: 0 12px 20px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05); }
.fc-title { font-size: 13.5px; font-weight: 700; color: #64748B; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.05em;}
.fc-val { font-size: 2.3rem; font-weight: 800; color: #0F172A; line-height: 1.1; margin-bottom: 12px; font-family: "Helvetica Neue", Arial, sans-serif;}
.fc-sub { font-size: 12.5px; font-weight: 700; padding: 6px 14px; border-radius: 20px; display: inline-block; letter-spacing: 0.02em;}
.fc-sub.green { background: #DCFCE7; color: #16A34A; }
.fc-sub.blue { background: #DBEAFE; color: #2563EB; }
.fc-sub.purple { background: #F3E8FF; color: #9333EA; }

/* 比較パネル用CSS */
.vs-box { background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.02); height: 100%; display: flex; flex-direction: column; justify-content: space-between;}
.vs-title { font-size: 16px; font-weight: 800; color: #334155; margin-bottom: 15px; text-align: center; padding-bottom: 10px; border-bottom: 2px solid #E2E8F0;}
.vs-item { display: flex; justify-content: space-between; font-size: 13.5px; color: #475569; margin-bottom: 8px; padding-bottom: 4px; border-bottom: 1px dashed #E2E8F0; transition: background 0.2s;}
.vs-item:hover { background: rgba(0,0,0,0.02); border-radius: 4px;}
.vs-item.highlight { font-weight: 700; color: #0176D3; background: rgba(1,118,211,0.05); padding: 4px; border-radius: 4px; border:none;}
.vs-item.highlight:hover { background: rgba(1,118,211,0.08); }
.vs-total { font-size: 15px; font-weight: 700; color: #0F172A; margin-top: 15px; padding: 10px; background: #E2E8F0; border-radius: 8px; text-align: center; cursor: help; transition: background 0.2s;}
.vs-total:hover { background: #CBD5E1;}
.vs-total-large { font-size: 22px; font-weight: 800; color: #0F172A; margin-top: 10px; padding: 15px; background: #DBEAFE; border-radius: 8px; text-align: center; border: 2px solid #93C5FD; cursor: help; transition: transform 0.2s;}
.vs-total-large:hover { transform: translateY(-2px); box-shadow: 0 4px 6px rgba(0,0,0,0.05);}

/* ロジック表示ボックスCSS */
.logic-box { background: #F8FAFC; border: 1px dashed #CBD5E1; border-radius: 8px; padding: 1.2rem; margin-top: 0.5rem; font-size: 0.9rem; color: #334155; }
.logic-box strong { color: #0F172A; font-size: 1rem; display: block; margin-top: 10px; }
.logic-eq { color: var(--accent); font-family: monospace; font-size: 1.05rem; margin: 6px 0 16px 0; display: block; background: #FFFFFF; padding: 8px; border: 1px solid #E2E8F0; border-radius: 4px; font-weight: bold;}

/* サマリーレポート用CSS */
.report-wrap { background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 0px; padding: 30px; margin-top: 10px;}
.rep-title { font-size: 22px; font-weight: 800; color: #0F172A; border-bottom: 3px solid #0176D3; padding-bottom: 12px; margin-bottom: 25px; text-align: center; background: #FFFFFF;}
.rep-h2 { font-size: 16px; font-weight: 800; color: #0176D3; margin-top: 25px; margin-bottom: 12px; background: #FFFFFF; padding: 4px 12px; border-left: 5px solid #0176D3;}
.rep-text { font-size: 14.5px; color: #334155; line-height: 1.7; margin-bottom: 10px; background: #FFFFFF;}
.rep-ul { margin-top: 5px; padding-left: 20px; font-size: 14.5px; color: #334155; line-height: 1.8; background: #FFFFFF;}
.rep-hi { font-weight: 800; color: #E11D48; font-size: 16px;}
.rep-box { background: #FFFFFF; border: 2px solid #E2E8F0; padding: 15px; text-align: center; margin-top: 15px;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
#  LOGIN
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
                else: st.error("IDまたはパスワードが間違っています。")
    st.stop()

# ─────────────────────────────────────────────────────────────────
#  DATA LAYER
# ─────────────────────────────────────────────────────────────────
conn = st.connection("gsheets", type=GSheetsConnection)
COLS_BIDS = ["ID","自治体名","担当部署名","案件概要","公示日","入札日","履行期間","入札方式","参加資格","予算(千円)","落札金額(千円)","自社結果","落札企業","競合1","競合2","競合3","仕様書","NJSS掲載","入札王掲載","URL1","URL2","URL3","URL4","URL5", "検索タグ", "備考"]
COLS_SETTINGS = ["種別", "項目名", "値1", "値2", "値3", "値4", "値5"]

def safe_num(val):
    try: return float(str(val).replace(',', '')) if pd.notna(val) and val != "" else 0.0
    except: return 0.0

def safe_int(val): return int(safe_num(val))

def is_truthy(val): return str(val).upper() in ["TRUE", "1", "1.0", "YES"]

@st.cache_data(ttl="10m")
def load_bids():
    try:
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        df = conn.read(spreadsheet=url, worksheet="案件データ", ttl="0s")
        if "自治体名" in df.columns:
            for col in COLS_BIDS:
                if col not in df.columns: df[col] = ""
            return df
        return pd.DataFrame(columns=COLS_BIDS)
    except: return pd.DataFrame(columns=COLS_BIDS)

def vdf(df): return df[df["自治体名"].notna() & (df["自治体名"].astype(str).str.strip() != "")].copy()

def save_bids(df_new):
    conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], worksheet="案件データ", data=df_new.fillna(""))
    load_bids.clear()

def sync_settings():
    rows = []
    for k, v in st.session_state.costs.items(): rows.append({"種別": "COST", "項目名": k, "値1": v})
    for w in st.session_state.search_words:
        d = st.session_state.search_counts.get(w, {})
        rows.append({"種別": "WORD", "項目名": w, "値1": d.get("NJSS_入札案件",0), "値2": d.get("入札王_入札案件",0), "値3": d.get("NJSS_落札結果",0), "値4": d.get("入札王_落札結果",0), "値5": d.get("登録日","")})
    conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], worksheet="設定データ", data=pd.DataFrame(rows, columns=COLS_SETTINGS).fillna(""))

if "settings_loaded" not in st.session_state:
    try: df_set = conn.read(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], worksheet="設定データ", ttl="0s")
    except: df_set = pd.DataFrame()
    if not df_set.empty and "種別" in df_set.columns:
        for _, r in df_set[df_set["種別"] == "COST"].iterrows(): 
            k = str(r["項目名"])
            if k in st.session_state.costs:
                val = safe_num(r["値1"])
                st.session_state.costs[k] = float(val) if "hour" in k else int(val)
        for _, r in df_set[df_set["種別"] == "WORD"].iterrows():
            w = str(r["項目名"])
            if w and w not in st.session_state.search_words:
                st.session_state.search_words.append(w)
                v1, v2 = safe_int(r.get("値1")), safe_int(r.get("値2"))
                if "値4" not in r or pd.isna(r["値4"]) or str(r.get("値4")).strip() == "":
                    st.session_state.search_counts[w] = {"NJSS_入札案件": 0, "入札王_入札案件": 0, "NJSS_落札結果": v1, "入札王_落札結果": v2, "登録日": str(r.get("値3", ""))}
                else:
                    st.session_state.search_counts[w] = {"NJSS_入札案件": v1, "入札王_入札案件": v2, "NJSS_落札結果": safe_int(r.get("値3")), "入札王_落札結果": safe_int(r.get("値4")), "登録日": str(r.get("値5", ""))}
    st.session_state.settings_loaded = True

# ─────────────────────────────────────────────────────────────────
#  NEW ROI ENGINE (WITH DYNAMIC LABOR DAYS)
# ─────────────────────────────────────────────────────────────────
def calc_roi_data():
    df = vdf(load_bids())
    avg_bid = pd.to_numeric(df["落札金額(千円)"], errors="coerce").fillna(0).mean() * 1000 if not df.empty and (pd.to_numeric(df["落札金額(千円)"], errors="coerce").fillna(0) > 0).any() else 0
    c = st.session_state.costs

    gross_profit_per_bid = avg_bid * (c["margin"]/100)
    base_sales = c["annual_bids"] * (c["win_rate"]/100) * gross_profit_per_bid
    
    tool_bids = c["annual_bids"] * (1 + c.get("tool_bid_increase_rate", 40)/100)
    tool_win_rate = (c["win_rate"] + c.get("tool_win_rate_boost", 5)) / 100
    tool_sales = (tool_bids * tool_win_rate) * gross_profit_per_bid

    # 稼働日数を反映
    annual_manual_cost = c["labor_cost_per_hour"] * c["labor_search_hour"] * c.get("labor_days_per_year", 240)
    annual_tool_labor_cost = c["labor_cost_per_hour"] * c.get("tool_labor_search_hour", 0.5) * c.get("labor_days_per_year", 240)
    market_cost = c["marketing_annual"]

    rows = []
    cum_man = 0; cum_nj = 0; cum_ki = 0
    cum_man_cost = 0; cum_nj_cost = 0; cum_ki_cost = 0

    for y in range(1, 6):
        man_cost_y = annual_manual_cost + market_cost
        man_profit = base_sales - man_cost_y
        cum_man += man_profit
        cum_man_cost += man_cost_y
        
        nj_cost_y = (c["n_init"] if y==1 else c["n_opt"]) + (c["n_month"] * 12) + market_cost + annual_tool_labor_cost
        nj_profit = tool_sales - nj_cost_y
        cum_nj += nj_profit
        cum_nj_cost += nj_cost_y
        
        ki_cost_y = (c["k_init"] if y==1 else c["k_opt"]) + (c["k_month"] * 12) + market_cost + annual_tool_labor_cost
        ki_profit = tool_sales - ki_cost_y
        cum_ki += ki_profit
        cum_ki_cost += ki_cost_y

        rows.append({
            "年度": f"{y}年目",
            "人力+ﾏｰｹ (累積)": int(cum_man), "NJSS+ﾏｰｹ (累積)": int(cum_nj), "入札王+ﾏｰｹ (累積)": int(cum_ki),
            "人力(単年)": int(man_profit), "NJSS(単年)": int(nj_profit), "入札王(単年)": int(ki_profit),
            "人力コスト(累積)": int(cum_man_cost), "NJSSコスト(累積)": int(cum_nj_cost), "入札王コスト(累積)": int(cum_ki_cost),
            "tt_人力+ﾏｰｹ (累積)": f"【計算式】前年までの累積利益 ＋ 今年の単年利益(¥{int(man_profit/10000):,}万)\n[単年利益内訳] ベース売上 - (人力検索コスト + マーケ費)",
            "tt_NJSS+ﾏｰｹ (累積)": f"【計算式】前年までの累積利益 ＋ 今年の単年利益(¥{int(nj_profit/10000):,}万)\n[単年利益内訳] 向上後売上 - (NJSS費用 + ツール運用人件費 + マーケ費)",
            "tt_入札王+ﾏｰｹ (累積)": f"【計算式】前年までの累積利益 ＋ 今年の単年利益(¥{int(ki_profit/10000):,}万)\n[単年利益内訳] 向上後売上 - (入札王費用 + ツール運用人件費 + マーケ費)",
            "tt_人力コスト(累積)": f"【計算式】前年までの累積コスト ＋ 今年のコスト(¥{int(man_cost_y/10000):,}万)\n[今年コスト内訳] 人力検索コスト(¥{int(annual_manual_cost/10000):,}万) + マーケ費(¥{int(market_cost/10000):,}万)",
            "tt_NJSSコスト(累積)": f"【計算式】前年までの累積コスト ＋ 今年のコスト(¥{int(nj_cost_y/10000):,}万)\n[今年コスト内訳] NJSS費用(¥{int((nj_cost_y - market_cost - annual_tool_labor_cost)/10000):,}万) + ツール運用人件費(¥{int(annual_tool_labor_cost/10000):,}万) + マーケ費(¥{int(market_cost/10000):,}万)\n※初年度は初期費用を含みます",
            "tt_入札王コスト(累積)": f"【計算式】前年までの累積コスト ＋ 今年のコスト(¥{int(ki_cost_y/10000):,}万)\n[今年コスト内訳] 入札王費用(¥{int((ki_cost_y - market_cost - annual_tool_labor_cost)/10000):,}万) + ツール運用人件費(¥{int(annual_tool_labor_cost/10000):,}万) + マーケ費(¥{int(market_cost/10000):,}万)\n※初年度は初期費用を含みます"
        })

    man_profit_m = (base_sales - annual_manual_cost - market_cost) / 12
    nj_profit_m  = (tool_sales - (c["n_month"]*12 + market_cost + (annual_tool_labor_cost/12))) / 12
    nj_diff_m = nj_profit_m - man_profit_m
    nj_be_months = (c["n_init"] / nj_diff_m) if nj_diff_m > 0 else 9999

    return pd.DataFrame(rows), avg_bid, annual_manual_cost, annual_tool_labor_cost, base_sales, tool_sales, tool_bids, tool_win_rate, gross_profit_per_bid, nj_be_months, nj_diff_m

# ─────────────────────────────────────────────────────────────────
#  UI HELPERS & API
# ─────────────────────────────────────────────────────────────────
PLY = dict(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=16, r=16, t=28, b=16), legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5))
C1, C2, C3 = "#0176D3", "#14B8A6", "#8B5CF6"

def go_to_dashboard(): st.session_state.current_page = "ダッシュボード"

def page_header(title, sub=""):
    col1, col2 = st.columns([3, 1])
    with col1: st.markdown(f'<div class="ph"><div><div class="ph-title">{title}</div><div class="ph-sub">{sub}</div></div></div>', unsafe_allow_html=True)
    with col2: 
        st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
        if title != "PoC Dashboard": st.button("ダッシュボードに戻る", use_container_width=True, on_click=go_to_dashboard)
    st.markdown('<div style="border-bottom: 1px solid var(--line2); margin-bottom: 2rem;"></div>', unsafe_allow_html=True)

def kpi(label, value, unit="", sub="", tag="", tag_type="neu", color="#0176D3"):
    t = f'<div class="kpi-tag tag-{tag_type}">{tag}</div>' if tag else ""
    st.markdown(f'<div class="kpi" style="border-top: 4px solid {color};"><div class="kpi-lbl">{label}</div><div class="kpi-val" style="color:{color} !important;">{value}<span style="font-size:1rem;margin-left:4px;">{unit}</span></div><div class="kpi-sub">{sub}</div>{t}</div>', unsafe_allow_html=True)

def req_label(text): st.markdown(f'<div class="rl">{text}<span class="req">必須</span></div>', unsafe_allow_html=True)
def form_div(text): st.markdown(f'<div class="form-div"><div class="form-div-line"></div><div class="form-div-label">{text}</div><div class="form-div-line"></div></div>', unsafe_allow_html=True)
def sec(text): st.markdown(f'<div class="sec">{text}</div>', unsafe_allow_html=True)

def gemini_extract(text_data: str) -> dict:
    if not text_data.strip(): return {}
    try:
        api_key = st.secrets["gemini"]["api_key"]
        import requests
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        prompt = '以下の案件テキストを解析しJSONで出力して。{"自治体名":"","担当部署名":"","案件概要":"","公示日":"","入札日":"","履行期間":"","入札方式":"","参加資格":"","予算(千円)":""}\n\n' + text_data
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.1, "response_mime_type": "application/json"}}
        resp = requests.post(url, json=payload, timeout=20)
        if resp.status_code == 200:
            raw_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(raw_text.replace("```json", "").replace("```", "").strip())
        return {}
    except: return {}

def gemini_extract_counts(text_data: str) -> dict:
    if not text_data.strip(): return {}
    try:
        api_key = st.secrets["gemini"]["api_key"]
        import requests
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        prompt = '検索結果テキストから抽出してJSONで。{"ツール名":"","キーワード":"","入札案件数":0,"落札結果数":0}\n\n' + text_data
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.1, "response_mime_type": "application/json"}}
        resp = requests.post(url, json=payload, timeout=20)
        if resp.status_code == 200:
            raw_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(raw_text.replace("```json", "").replace("```", "").strip())
        return {}
    except: return {}

# ─────────────────────────────────────────────────────────────────
#  MAIN APP ROUTING (SIDEBAR)
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""<div style="padding:24px 20px 16px;border-bottom:1px solid rgba(255,255,255,0.05);margin-bottom:8px;"><div><div style="font-size:18px;font-weight:800;color:#FFFFFF;letter-spacing:-0.3px;">PoC Board</div><div style="font-size:10px;color:#8B9EC7;letter-spacing:1px;text-transform:uppercase;margin-top:2px;">Evaluation Tool</div></div></div>""", unsafe_allow_html=True)
    menu_options = ["ダッシュボード", "案件データ入力", "ワード検索数", "ROI分析", "データ管理", "マニュアル"]
    current_index = menu_options.index(st.session_state.current_page) if st.session_state.current_page in menu_options else 0
    st.session_state.current_page = st.radio("ナビゲーション", menu_options, index=current_index, label_visibility="collapsed")
    current_page = st.session_state.current_page
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    if st.button("ログアウト", use_container_width=True): st.session_state.logged_in = False; st.rerun()

# ─────────────────────────────────────────────────────────────────
#  PAGE: DASHBOARD
# ─────────────────────────────────────────────────────────────────
if current_page == "ダッシュボード":
    page_header("PoC Dashboard", "入札ツール導入前検証 — データ統合ビュー")

    df  = load_bids()
    vd  = vdf(df)
    df_roi, _, _, _, _, _, _, _, _, _, _ = calc_roi_data()

    if vd.empty:
        st.info("データがありません。「案件データ入力」から登録してください。")
        st.stop()

    total = len(vd)
    nj_c  = vd["NJSS掲載"].apply(is_truthy).sum()
    ki_c  = vd["入札王掲載"].apply(is_truthy).sum()
    n_p5  = df_roi.iloc[-1]["NJSS+ﾏｰｹ (累積)"] if not df_roi.empty else 0
    k_p5  = df_roi.iloc[-1]["入札王+ﾏｰｹ (累積)"] if not df_roi.empty else 0

    kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
    with kpi_col1: kpi("対象案件数", total, "件", sub="登録済み総案件", color="#3B82F6")
    with kpi_col2: kpi("NJSS 網羅率", f"{nj_c/total*100:.1f}" if total else "0.0", "%", sub=f"{nj_c}件捕捉", tag="NJSS", tag_type="up" if nj_c >= ki_c else "dn", color="#14B8A6")
    with kpi_col3: kpi("入札王 網羅率", f"{ki_c/total*100:.1f}" if total else "0.0", "%", sub=f"{ki_c}件捕捉", tag="入札王", tag_type="up" if ki_c >= nj_c else "dn", color="#6366F1")

    kpi_col4, kpi_col5 = st.columns(2)
    with kpi_col4: kpi("NJSS 5年純利益", f"{int(n_p5/10000):,}", "万円", sub="人件費等全コスト差引後", tag_type="neu", color="#8B5CF6")
    with kpi_col5: kpi("入札王 5年純利益", f"{int(k_p5/10000):,}", "万円", sub="人件費等全コスト差引後", tag_type="neu", color="#EC4899")

    st.markdown("<br>", unsafe_allow_html=True)

    r1l, r1r = st.columns(2)
    with r1l:
        with st.container(border=True):
            sec("案件捕捉数の比較")
            fig = px.bar(x=["NJSS","入札王"], y=[nj_c, ki_c], color=["NJSS","入札王"], color_discrete_map={"NJSS": C1, "入札王": C2}, text=[nj_c, ki_c])
            fig.update_traces(marker_line_width=0, textposition="outside", textfont_size=14)
            fig.update_layout(**PLY, showlegend=False, height=280)
            fig.update_yaxes(title="", zeroline=False); fig.update_xaxes(title="")
            st.plotly_chart(fig, use_container_width=True)

    with r1r:
        with st.container(border=True):
            sec("総合評価レーダー")
            nj_sw = sum(1 for v in st.session_state.search_counts.values() if (v.get("NJSS_入札案件",0)+v.get("NJSS_落札結果",0)) > (v.get("入札王_入札案件",0)+v.get("入札王_落札結果",0)))
            ki_sw = sum(1 for v in st.session_state.search_counts.values() if (v.get("入札王_入札案件",0)+v.get("入札王_落札結果",0)) > (v.get("NJSS_入札案件",0)+v.get("NJSS_落札結果",0)))
            nj_cov = nj_c/total*100 if total else 0
            ki_cov = ki_c/total*100 if total else 0
            tot_sw = nj_sw + ki_sw
            nj_s   = nj_sw/tot_sw*100 if tot_sw else 50
            ki_s   = ki_sw/tot_sw*100 if tot_sw else 50
            mx     = max(n_p5, k_p5, 1)
            nj_ps, ki_ps = max(0, n_p5/mx*100), max(0, k_p5/mx*100)
            
            fig_r = go.Figure()
            fig_r.add_trace(go.Scatterpolar(r=[nj_cov,nj_s,nj_ps,nj_cov], theta=["網羅率","検索精度","5年ROI","網羅率"], fill="toself", name="NJSS", line=dict(color=C1, width=2), fillcolor="rgba(1,118,211,0.15)"))
            fig_r.add_trace(go.Scatterpolar(r=[ki_cov,ki_s,ki_ps,ki_cov], theta=["網羅率","検索精度","5年ROI","網羅率"], fill="toself", name="入札王", line=dict(color=C2, width=2, dash="dash"), fillcolor="rgba(20,184,166,0.1)"))
            fig_r.update_layout(polar=dict(bgcolor="rgba(0,0,0,0)", radialaxis=dict(visible=True, range=[0,100])), paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"), height=280, margin=dict(t=16,b=36,l=16,r=16))
            st.plotly_chart(fig_r, use_container_width=True)

    with st.container(border=True):
        sec("キーワード検索精度比較 (総計)")
        if st.session_state.search_words and st.session_state.search_counts:
            sw_df = pd.DataFrame([{
                "ワード": w, 
                "NJSS": st.session_state.search_counts.get(w,{}).get("NJSS_入札案件",0) + st.session_state.search_counts.get(w,{}).get("NJSS_落札結果",0), 
                "入札王": st.session_state.search_counts.get(w,{}).get("入札王_入札案件",0) + st.session_state.search_counts.get(w,{}).get("入札王_落札結果",0)
            } for w in st.session_state.search_words])
            
            tab_kw_graph, tab_kw_table = st.tabs(["📈 グラフ表示", "📊 テーブル表示"])
            
            with tab_kw_graph:
                fig3 = px.bar(sw_df, x="ワード", y=["NJSS","入札王"], barmode="group", color_discrete_map={"NJSS": C1, "入札王": C2})
                fig3.update_traces(marker_line_width=0); fig3.update_layout(**PLY, height=350, legend_title_text=""); fig3.update_xaxes(tickangle=-45); fig3.update_yaxes(title="総ヒット件数")
                st.plotly_chart(fig3, use_container_width=True)
                
            with tab_kw_table:
                disp_df = sw_df.rename(columns={"NJSS": "NJSS (件)", "入札王": "入札王 (件)"})
                st.dataframe(disp_df, hide_index=True, use_container_width=True)
        else:
            st.info("キーワードデータがありません。「ワード検索数」画面から追加してください。")

    with st.container(border=True):
        sec("累積純利益の推移（5カ年・全コスト差引後）")
        fig4 = px.line(df_roi, x="年度", y=["人力+ﾏｰｹ (累積)", "NJSS+ﾏｰｹ (累積)", "入札王+ﾏｰｹ (累積)"], color_discrete_map={"人力+ﾏｰｹ (累積)": "#94A3B8", "NJSS+ﾏｰｹ (累積)": C1, "入札王+ﾏｰｹ (累積)": C2})
        fig4.update_traces(line_width=3); fig4.update_layout(**PLY, height=300); fig4.update_yaxes(title="純利益 (円)"); fig4.update_xaxes(title="")
        st.plotly_chart(fig4, use_container_width=True)

# ─────────────────────────────────────────────────────────────────
#  PAGE: DATA INPUT
# ─────────────────────────────────────────────────────────────────
elif current_page == "案件データ入力":
    page_header("案件データ入力", "AIによる自動入力 + 手動入力")
    
    st.markdown('<div style="font-size:13px; color:var(--muted); margin-bottom:1rem;">案件のWebテキストをコピーして貼り付けると、Gemini AIが自動で項目を振り分けます。</div>', unsafe_allow_html=True)
    pasted_text = st.text_area("案件テキスト", height=150, placeholder="ここにテキストをペースト...", label_visibility="collapsed")
    if st.button("テキストをAIで解析する ✨", type="primary", use_container_width=True):
        if pasted_text.strip():
            with st.spinner("Gemini AI がテキストを解析中..."):
                result = gemini_extract(pasted_text)
                if result: 
                    st.session_state.ocr_result = result
                    st.success("テキストの解析に成功しました！フォームに反映しています。")
        else: st.warning("テキストを入力してください。")

    ocr = st.session_state.ocr_result or {}
    df_cur = load_bids()
    vd     = vdf(df_cur)

    with st.container(border=True):
        with st.form("entry_form", clear_on_submit=True):
            form_div("基本情報")
            st.caption("💡 【自動マージ機能】すでに同じ「自治体名」と「案件名」のデータが登録されている場合、情報を自動で統合（マージ）します。")
            
            c1, c2 = st.columns(2)
            with c1: req_label("自治体名・発注機関"); mun = st.text_input("mun", label_visibility="collapsed", placeholder="例: 横浜市", value=ocr.get("自治体名",""))
            with c2: st.markdown('<div class="rl">担当部署名</div>', unsafe_allow_html=True); dep = st.text_input("dep", label_visibility="collapsed", placeholder="例: デジタル統括本部", value=ocr.get("担当部署名",""))
            req_label("案件名・案件概要"); smm = st.text_input("smm", label_visibility="collapsed", placeholder="例: データ連携基盤構築業務", value=ocr.get("案件概要",""))

            form_div("スケジュール・要件")
            c3,c4,c5 = st.columns(3)
            def parse_date(d_str):
                try: return datetime.datetime.strptime(d_str, "%Y-%m-%d").date() if d_str and isinstance(d_str, str) else None
                except: return None
            pub_d  = c3.date_input("公示日", value=parse_date(ocr.get("公示日")))
            bid_d  = c4.date_input("入札日", value=parse_date(ocr.get("入札日")))
            per_d  = c5.text_input("履行期間", placeholder="2025-06-01 〜 2026-03-31", value=ocr.get("履行期間",""))
            c6,c7  = st.columns(2)
            methods = ["","公募型プロポーザル","一般競争入札","指名競争入札","随意契約","その他"]
            m_idx  = methods.index(ocr.get("入札方式","")) if ocr.get("入札方式","") in methods else 0
            method = c6.selectbox("入札方式", methods, index=m_idx)
            qual   = c7.text_input("参加資格", placeholder="情報処理 Aランク", value=ocr.get("参加資格",""))

            form_div("結果・金額")
            c8,c9,c10 = st.columns(3)
            try: bv = int(ocr.get("予算(千円)", 0))
            except: bv = 0
            budget   = c8.number_input("予算額 (千円)", min_value=0, step=100, value=bv)
            with c9:
                st.markdown('<div class="rl">落札金額 (千円)</div>', unsafe_allow_html=True)
                wbid = st.number_input("wbid", label_visibility="collapsed", min_value=0, step=100)
            our_res  = c10.selectbox("自社結果", ["","受注","失注","見送り","辞退"])
            c11,c12  = st.columns(2)
            wnr = c11.text_input("落札企業"); b1  = c12.text_input("競合1"); b2  = c11.text_input("競合2"); b3  = c12.text_input("競合3")

            form_div("ツール掲載確認（PoC）")
            cx1,cx2,cx3 = st.columns(3)
            spc = cx1.checkbox("仕様書あり"); njl = cx2.checkbox("NJSSに掲載"); kil = cx3.checkbox("入札王に掲載")

            form_div("参考URL")
            cu1,cu2 = st.columns(2); url1 = cu1.text_input("URL 1"); url2 = cu2.text_input("URL 2")
            cu3,cu4 = st.columns(2); url3 = cu3.text_input("URL 3"); url4 = cu4.text_input("URL 4")
            url5 = st.text_input("URL 5")

            form_div("タグ・備考")
            tags = st.text_input("検索タグ", placeholder="例: BI, クラウド")
            remarks = st.text_area("備考", height=80)

            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("この案件を保存する", use_container_width=True):
                if mun and smm:
                    mun_clean = mun.strip()
                    smm_clean = smm.strip()
                    
                    mask = (vd["自治体名"].astype(str).str.strip() == mun_clean) & (vd["案件概要"].astype(str).str.strip() == smm_clean)
                    dup_idx = vd[mask].index
                    
                    if len(dup_idx) > 0:
                        idx = dup_idx[0]
                        row = vd.loc[idx]
                        vd.at[idx, "仕様書"] = is_truthy(row.get("仕様書")) or spc
                        vd.at[idx, "NJSS掲載"] = is_truthy(row.get("NJSS掲載")) or njl
                        vd.at[idx, "入札王掲載"] = is_truthy(row.get("入札王掲載")) or kil
                        if dep: vd.at[idx, "担当部署名"] = dep
                        if pub_d: vd.at[idx, "公示日"] = pub_d.strftime("%Y-%m-%d")
                        if bid_d: vd.at[idx, "入札日"] = bid_d.strftime("%Y-%m-%d")
                        if per_d: vd.at[idx, "履行期間"] = per_d
                        if method: vd.at[idx, "入札方式"] = method
                        if qual: vd.at[idx, "参加資格"] = qual
                        if budget > 0: vd.at[idx, "予算(千円)"] = budget
                        if wbid > 0: vd.at[idx, "落札金額(千円)"] = wbid
                        if our_res: vd.at[idx, "自社結果"] = our_res
                        if wnr: vd.at[idx, "落札企業"] = wnr
                        if b1: vd.at[idx, "競合1"] = b1
                        if b2: vd.at[idx, "競合2"] = b2
                        if b3: vd.at[idx, "競合3"] = b3
                        if url1: vd.at[idx, "URL1"] = url1
                        if url2: vd.at[idx, "URL2"] = url2
                        if url3: vd.at[idx, "URL3"] = url3
                        if url4: vd.at[idx, "URL4"] = url4
                        if url5: vd.at[idx, "URL5"] = url5
                        if tags:
                            e_tag = str(row.get("検索タグ", ""))
                            vd.at[idx, "検索タグ"] = tags if e_tag == "nan" or not e_tag.strip() else f"{e_tag}, {tags}"
                        if remarks:
                            e_rem = str(row.get("備考", ""))
                            vd.at[idx, "備考"] = remarks if e_rem == "nan" or not e_rem.strip() else f"{e_rem}\n{remarks}"

                        try:
                            save_bids(vd)
                            st.session_state.ocr_result = None
                            st.success(f"✨ 既存データと重複を検知したため統合（マージ）しました！")
                        except Exception as e: st.error(f"保存失敗: {e}")
                            
                    else:
                        new_rec = pd.DataFrame([{
                            "ID": len(vd)+1, "自治体名": mun, "担当部署名": dep, "案件概要": smm, 
                            "公示日": pub_d.strftime("%Y-%m-%d") if pub_d else "", "入札日": bid_d.strftime("%Y-%m-%d") if bid_d else "", 
                            "履行期間": per_d, "入札方式": method, "参加資格": qual, 
                            "予算(千円)": budget, "落札金額(千円)": wbid, "自社結果": our_res, 
                            "落札企業": wnr, "競合1": b1, "競合2": b2, "競合3": b3, 
                            "仕様書": spc, "NJSS掲載": njl, "入札王掲載": kil, 
                            "URL1": url1, "URL2": url2, "URL3": url3, "URL4": url4, "URL5": url5,
                            "検索タグ": tags, "備考": remarks
                        }])
                        try:
                            save_bids(pd.concat([vd, new_rec], ignore_index=True))
                            st.session_state.ocr_result = None
                            st.success("🎉 新規案件として保存しました。")
                        except Exception as e: st.error(f"保存失敗: {e}")
                else: st.error("「自治体名」「案件概要」は必須です。")

    if not vd.empty:
        with st.container(border=True): 
            sec("登録済みデータ一覧")
            st.dataframe(vd, hide_index=True, use_container_width=True)

# ─────────────────────────────────────────────────────────────────
#  PAGE: KEYWORD
# ─────────────────────────────────────────────────────────────────
elif current_page == "ワード検索数":
    page_header("ワード検索数比較", "AIテキスト解析または手動入力で件数を記録")
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    st.markdown('<div style="font-size:13px; color:var(--muted); margin-bottom:1rem;">検索結果画面の文字をすべてコピーして貼り付けると、AIが自動で数値を抽出します。</div>', unsafe_allow_html=True)
    search_text = st.text_area("検索結果のテキスト", height=150, placeholder="ここに検索結果の画面テキストをペースト...", label_visibility="collapsed")
    
    if st.button("テキストをAIで解析して追加する ✨", type="primary", use_container_width=True):
        if search_text.strip():
            with st.spinner("AIが検索結果を解析中..."):
                res = gemini_extract_counts(search_text)
                if res and "キーワード" in res and res["キーワード"]:
                    w = res["キーワード"]
                    tool = res.get("ツール名", "")
                    b_cnt = res.get("入札案件数", 0)
                    w_cnt = res.get("落札結果数", 0)
                    
                    if w not in st.session_state.search_words:
                        st.session_state.search_words.append(w)
                        st.session_state.search_counts[w] = {"NJSS_入札案件": 0, "入札王_入札案件": 0, "NJSS_落札結果": 0, "入札王_落札結果": 0, "登録日": today_str}
                    
                    if "NJSS" in tool.upper() or "うるる" in tool:
                        st.session_state.search_counts[w]["NJSS_入札案件"] = b_cnt
                        st.session_state.search_counts[w]["NJSS_落札結果"] = w_cnt
                        st.success(f"🎉 NJSSの「{w}」の検索結果を読み取りました！")
                    elif "入札王" in tool:
                        st.session_state.search_counts[w]["入札王_入札案件"] = b_cnt
                        st.session_state.search_counts[w]["入札王_落札結果"] = w_cnt
                        st.success(f"🎉 入札王の「{w}」の検索結果を読み取りました！")
                    else:
                        st.warning(f"⚠️ 件数は読み取れましたがツール名が特定できませんでした。下の表から手動で入力してください。")
                    
                    sync_settings(); st.rerun()
                else: st.error("⚠️ テキストからキーワードや件数を読み取れませんでした。")
        else: st.warning("テキストを入力してください。")

    st.markdown("<hr>", unsafe_allow_html=True)
    
    ca1,ca2,ca3 = st.columns([2,1,1])
    nw = ca1.text_input("手動でキーワード追加", placeholder="例: BIツール", label_visibility="collapsed")
    if ca2.button("追加", use_container_width=True):
        if nw and nw not in st.session_state.search_words:
            st.session_state.search_words.append(nw); 
            st.session_state.search_counts[nw] = {"NJSS_入札案件": 0, "入札王_入札案件": 0, "NJSS_落札結果": 0, "入札王_落札結果": 0, "登録日": today_str}
            sync_settings(); st.rerun()
    if ca3.button("クリア", use_container_width=True):
        st.session_state.search_words = []; st.session_state.search_counts = {}
        sync_settings(); st.rerun()

    with st.container(border=True):
        sec("ヒット件数テーブル（セル直接編集可）")
        if st.session_state.search_words:
            df_sw = pd.DataFrame([{
                "検索ワード": w, 
                "NJSS 入札案件(件)":  st.session_state.search_counts.get(w,{}).get("NJSS_入札案件",0), 
                "入札王 入札案件(件)": st.session_state.search_counts.get(w,{}).get("入札王_入札案件",0),
                "NJSS 落札結果(件)":  st.session_state.search_counts.get(w,{}).get("NJSS_落札結果",0), 
                "入札王 落札結果(件)": st.session_state.search_counts.get(w,{}).get("入札王_落札結果",0),
                "登録日": st.session_state.search_counts.get(w,{}).get("登録日", today_str)
            } for w in st.session_state.search_words])
            
            edited = st.data_editor(df_sw, num_rows="dynamic", use_container_width=True, hide_index=True)
            if st.button("件数を保存してダッシュボードへ反映", use_container_width=True):
                st.session_state.search_words = edited["検索ワード"].dropna().tolist()
                st.session_state.search_counts = {
                    row["検索ワード"]: {
                        "NJSS_入札案件": safe_int(row.get("NJSS 入札案件(件)")), 
                        "入札王_入札案件": safe_int(row.get("入札王 入札案件(件)")), 
                        "NJSS_落札結果": safe_int(row.get("NJSS 落札結果(件)")), 
                        "入札王_落札結果": safe_int(row.get("入札王 落札結果(件)")), 
                        "登録日": str(row.get("登録日", today_str))
                    } for _, row in edited.iterrows() if pd.notna(row["検索ワード"])
                }
                sync_settings(); st.success("保存しました。")
        else: st.info("キーワードを追加してください。")

# ─────────────────────────────────────────────────────────────────
#  PAGE: ROI 
# ─────────────────────────────────────────────────────────────────
elif current_page == "ROI分析":
    page_header("事業性・ROI分析", "人力（As-Is）とツール導入時（To-Be）の収益構造の比較")

    df_roi, avg_bid, ann_manual_cost, ann_tool_labor_cost, base_sales, tool_sales, tool_bids, tool_win_rate, gross_profit_per_bid, nj_be_months, nj_diff_m = calc_roi_data()
    c = st.session_state.costs

    col_set1, col_set2 = st.columns([1, 2])
    with col_set1:
        st.markdown('<div class="sec">1. 基本前提（人力・現状）</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.session_state.costs["annual_bids"] = st.number_input("年間想定応札数（件）", value=int(c["annual_bids"]), help="現在、手動で検索して応札できている年間の想定件数です。")
            st.session_state.costs["win_rate"] = st.slider("平均受注率（%）", 0, 100, int(c["win_rate"]), help="応札した案件のうち、実際に受注できる確率の現状ベースです。")
            st.session_state.costs["margin"] = st.slider("平均粗利率（%）", 0, 100, int(c["margin"]), help="1案件あたりの売上から原価を引いた、自社に残る粗利の割合です。")
            st.session_state.costs["marketing_annual"] = st.number_input("年間マーケティング費用（円）", value=int(c["marketing_annual"]), step=10000, help="入札以外の営業・マーケティングにかかっている年間費用（比較用）です。")
            
            st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
            st.caption("【人力運用時の隠れたコスト】")
            st.session_state.costs["labor_days_per_year"] = st.number_input("年間稼働日数（日）", value=int(c.get("labor_days_per_year", 240)), step=1, help="1年間の営業日数（稼働日）です。人件費の計算に使用します。")
            st.session_state.costs["labor_search_hour"] = st.number_input("1日の手動検索時間（h）", value=float(c["labor_search_hour"]), step=0.5, help="1日あたり、担当者が入札サイトを手動で巡回・検索している時間です。")
            st.session_state.costs["labor_cost_per_hour"] = st.number_input("担当者時給（円）", value=int(c["labor_cost_per_hour"]), step=100, help="手動検索を行っている担当者の時給換算コストです。（見えない人件費の可視化）")
            
        st.markdown('<div class="sec" style="margin-top:15px;">2. 🚀 ツールの付加価値と費用</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.caption("【ツールの導入メリット（売上拡大）】")
            st.session_state.costs["tool_bid_increase_rate"] = st.slider("見逃し防止による 応札数の増加率（%）", 0, 100, int(c.get("tool_bid_increase_rate", 40)), help="ツールで網羅的に検索できるようになることで、今まで見逃していた案件に気付き、応札数がどれくらい増えるかの想定値です。")
            st.session_state.costs["tool_win_rate_boost"] = st.slider("競合データ分析による 勝率の向上（+ポイント）", 0, 20, int(c.get("tool_win_rate_boost", 5)), help="過去の落札金額や競合他社の傾向をツールで分析することで、勝率が現在から何ポイント上がるかの想定値です。")
            
            st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
            st.caption("【ツール利用時の人件費】")
            st.session_state.costs["tool_labor_search_hour"] = st.number_input("ツール利用時の1日の確認時間（h）", value=float(c.get("tool_labor_search_hour", 0.5)), step=0.5, help="ツールが自動収集した案件をチェックし、社内に展開するための1日あたりの作業時間です。")

            st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
            st.caption("【ツール利用コスト】")
            cx1, cx2 = st.columns(2)
            with cx1:
                st.caption("NJSS 費用")
                ni = st.number_input("初期", value=c["n_init"], key="ni", label_visibility="collapsed", help="NJSSの初期費用")
                nm = st.number_input("月額", value=c["n_month"], key="nm", label_visibility="collapsed", help="NJSSの月額費用")
            with cx2:
                st.caption("入札王 費用")
                ki = st.number_input("初期", value=c["k_init"], key="ki", label_visibility="collapsed", help="入札王の初期費用")
                km = st.number_input("月額", value=c["k_month"], key="km", label_visibility="collapsed", help="入札王の月額費用")

        if st.button("設定を保存してシミュレーション更新", use_container_width=True, type="primary"):
            st.session_state.costs.update({"n_init":ni,"n_month":nm,"k_init":ki,"k_month":km})
            sync_settings(); st.rerun()

    with col_set2:
        st.markdown('<div class="sec">3. ツール導入による営業KPIの向上（計算結果）</div>', unsafe_allow_html=True)
        
        k1, k2, k3 = st.columns(3)
        c1_html = f'''<div class="fancy-card" style="border-top: 4px solid #3B82F6;">
            <div class="fc-title">年間応札数</div>
            <div class="fc-val">{int(tool_bids)} <span style="font-size:1.2rem;">件</span></div>
            <div><span class="fc-sub blue">見逃し防止で +{int(tool_bids - c['annual_bids'])}件</span></div>
        </div>'''
        c2_html = f'''<div class="fancy-card" style="border-top: 4px solid #10B981;">
            <div class="fc-title">平均受注率</div>
            <div class="fc-val">{int(tool_win_rate*100)} <span style="font-size:1.2rem;">%</span></div>
            <div><span class="fc-sub green">データ分析で +{c['tool_win_rate_boost']}pt</span></div>
        </div>'''
        c3_html = f'''<div class="fancy-card" style="border-top: 4px solid #8B5CF6;">
            <div class="fc-title">1案件あたりの平均粗利</div>
            <div class="fc-val"><span style="font-size:1.2rem;">¥</span>{int(gross_profit_per_bid/10000):,} <span style="font-size:1.2rem;">万</span></div>
            <div style="height:25px;"></div>
        </div>'''
        with k1: st.markdown(c1_html, unsafe_allow_html=True)
        with k2: st.markdown(c2_html, unsafe_allow_html=True)
        with k3: st.markdown(c3_html, unsafe_allow_html=True)
        
        with st.expander("📊 ツールの付加価値による「期待売上」の算出ロジック", expanded=False):
            st.markdown(f"""
            <div class="logic-box">
                <strong>① 現状の年間期待売上（粗利ベース）</strong>
                <span class="logic-eq">想定応札数({c['annual_bids']}件) × 現状勝率({c['win_rate']}%) × 1案件平均粗利(¥{int(gross_profit_per_bid):,}) ＝ ¥{int(base_sales):,}</span>
                
                <strong>② ツール導入時の年間期待売上（粗利ベース）</strong>
                <span class="logic-eq">向上後応札数({int(tool_bids)}件) × 向上後勝率({int(tool_win_rate*100)}%) × 1案件平均粗利(¥{int(gross_profit_per_bid):,}) ＝ ¥{int(tool_sales):,}</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="sec">4. 業務効率化（時間削減・コスト削減効果）</div>', unsafe_allow_html=True)
        days = c.get("labor_days_per_year", 240)
        man_h = c["labor_search_hour"] * days
        tool_h = c.get("tool_labor_search_hour", 0.5) * days
        diff_h = man_h - tool_h
        diff_c = ann_manual_cost - ann_tool_labor_cost

        kpi_t1, kpi_t2 = st.columns(2)
        t1_html = f'''<div class="fancy-card" style="border-top: 4px solid #F59E0B;">
            <div class="fc-title">年間作業時間の削減</div>
            <div class="fc-val" style="color:#D97706;">▲ {int(diff_h)} <span style="font-size:1.2rem;">時間</span></div>
            <div><span class="fc-sub" style="background:#FEF3C7; color:#D97706;">現状 {int(man_h)}h → 導入後 {int(tool_h)}h</span></div>
        </div>'''
        t2_html = f'''<div class="fancy-card" style="border-top: 4px solid #EF4444;">
            <div class="fc-title">年間見えない人件費の削減</div>
            <div class="fc-val" style="color:#DC2626;">▲ <span style="font-size:1.2rem;">¥</span>{int(diff_c/10000):,} <span style="font-size:1.2rem;">万</span></div>
            <div><span class="fc-sub" style="background:#FEE2E2; color:#DC2626;">現状 ¥{int(ann_manual_cost/10000)}万 → 導入後 ¥{int(ann_tool_labor_cost/10000)}万</span></div>
        </div>'''
        with kpi_t1: st.markdown(t1_html, unsafe_allow_html=True)
        with kpi_t2: st.markdown(t2_html, unsafe_allow_html=True)

        df_time = pd.DataFrame([
            {"方式": "ツール導入後", "年間作業時間 (時間)": tool_h, "年間人件費 (万円)": ann_tool_labor_cost / 10000, "種類": "導入後"},
            {"方式": "人力（現状）", "年間作業時間 (時間)": man_h, "年間人件費 (万円)": ann_manual_cost / 10000, "種類": "現状"}
        ])

        tc1, tc2 = st.columns(2)
        with tc1:
            fig_t1 = px.bar(df_time, x="年間作業時間 (時間)", y="方式", color="種類", orientation='h', text="年間作業時間 (時間)", color_discrete_map={"現状": "#94A3B8", "導入後": "#10B981"})
            fig_t1.update_traces(textposition='outside', texttemplate='%{text:,.0f} h', marker_line_width=0)
            fig_t1.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=40, t=0, b=0), showlegend=False, yaxis_title="", height=120)
            st.plotly_chart(fig_t1, use_container_width=True)
        with tc2:
            fig_t2 = px.bar(df_time, x="年間人件費 (万円)", y="方式", color="種類", orientation='h', text="年間人件費 (万円)", color_discrete_map={"現状": "#94A3B8", "導入後": "#10B981"})
            fig_t2.update_traces(textposition='outside', texttemplate='¥%{text:,.0f} 万', marker_line_width=0)
            fig_t2.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=40, t=0, b=0), showlegend=False, yaxis_title="", height=120)
            st.plotly_chart(fig_t2, use_container_width=True)

        st.markdown('<div class="sec" style="margin-top: 15px;">5. 受注件数別 初年度ROI（投資対効果）シミュレーション</div>', unsafe_allow_html=True)
        st.caption("初年度のツール投資額（初期費用＋12ヶ月分の月額）に対して、実際に何件受注できれば投資回収ライン（0%）を突破し、利益化できるかを可視化します。")
        
        nj_inv = c["n_init"] + (c["n_month"] * 12)
        ki_inv = c["k_init"] + (c["k_month"] * 12)
        
        max_x = max(10, int(c['annual_bids'] * 1.5))
        roi_data_pts = []
        for i in range(0, max_x + 1):
            s = i * gross_profit_per_bid
            nr = ((s - nj_inv) / nj_inv) * 100 if nj_inv > 0 else 0
            kr = ((s - ki_inv) / ki_inv) * 100 if ki_inv > 0 else 0
            roi_data_pts.append({"受注件数": i, "NJSS": nr, "入札王": kr})
        df_roi_curve = pd.DataFrame(roi_data_pts)
        
        col_r1, col_r2 = st.columns([1, 1.8])
        with col_r1:
            st.markdown("##### 🎯 目標受注件数での確認")
            target_orders = st.slider("初年度の想定受注件数 (件)", min_value=1, max_value=max_x, value=int(tool_bids * tool_win_rate) if int(tool_bids * tool_win_rate) > 0 else 5)
            t_sales = target_orders * gross_profit_per_bid
            t_nr = ((t_sales - nj_inv) / nj_inv) * 100 if nj_inv > 0 else 0
            t_kr = ((t_sales - ki_inv) / ki_inv) * 100 if ki_inv > 0 else 0
            
            r1_html = f'''<div class="fancy-card" style="border-top: 4px solid {C1}; padding: 15px; margin-bottom: 10px;">
                <div class="fc-title">NJSS 初年度ROI</div>
                <div class="fc-val" style="color:{C1}; font-size:1.8rem;">{int(t_nr):,} <span style="font-size:1rem;">%</span></div>
                <div><span class="fc-sub" style="background:#E0F2FE; color:{C1}; font-size:11px;">投資: ¥{int(nj_inv/10000)}万 / 粗利: ¥{int(t_sales/10000)}万</span></div>
            </div>'''
            r2_html = f'''<div class="fancy-card" style="border-top: 4px solid {C2}; padding: 15px;">
                <div class="fc-title">入札王 初年度ROI</div>
                <div class="fc-val" style="color:{C2}; font-size:1.8rem;">{int(t_kr):,} <span style="font-size:1rem;">%</span></div>
                <div><span class="fc-sub" style="background:#CCFBF1; color:{C2}; font-size:11px;">投資: ¥{int(ki_inv/10000)}万 / 粗利: ¥{int(t_sales/10000)}万</span></div>
            </div>'''
            st.markdown(r1_html, unsafe_allow_html=True)
            st.markdown(r2_html, unsafe_allow_html=True)
            
        with col_r2:
            fig_roi_curve = px.line(df_roi_curve, x="受注件数", y=["NJSS", "入札王"], color_discrete_map={"NJSS": C1, "入札王": C2})
            fig_roi_curve.add_hline(y=0, line_dash="dash", line_color="#EF4444", annotation_text="損益分岐点 (ROI 0%)", annotation_position="bottom right")
            fig_roi_curve.add_vline(x=target_orders, line_dash="dot", line_color="#64748B", annotation_text=f"想定: {target_orders}件", annotation_position="top left")
            fig_roi_curve.update_traces(line_width=3)
            fig_roi_curve.update_layout(**PLY, hovermode="x unified", yaxis_title="初年度ROI (%)", height=300)
            fig_roi_curve.update_layout(legend_title_text="")
            st.plotly_chart(fig_roi_curve, use_container_width=True)

        # ─────────────────────────────────────────────────────────────────
        #  NEW: 収益構造の比較 にツールチップを追加
        # ─────────────────────────────────────────────────────────────────
        st.markdown('<div class="sec">6. 収益構造の比較（マウスオーバーで計算式を表示）</div>', unsafe_allow_html=True)
        st.info("💡 項目名や金額にマウスカーソルを合わせると、具体的な計算ロジックの内訳が表示されます。")
        
        man_1y = df_roi.iloc[0]["人力(単年)"]
        nj_1y  = df_roi.iloc[0]["NJSS(単年)"]
        man_5y = df_roi.iloc[-1]["人力+ﾏｰｹ (累積)"]
        nj_5y  = df_roi.iloc[-1]["NJSS+ﾏｰｹ (累積)"]
        ki_5y  = df_roi.iloc[-1]["入札王+ﾏｰｹ (累積)"]
        
        market_c = c["marketing_annual"]
        nj_monthly_annual = c["n_month"] * 12
        
        v1, v2 = st.columns(2)
        with v1:
            st.markdown(f"""
            <div class="vs-box">
                <div class="vs-title">😟 現状（人力 ＋ マーケティング）</div>
                <div class="vs-item" title="【計算式】想定応札数({c['annual_bids']}件) × 現状勝率({c['win_rate']}%) × 1案件平均粗利(¥{int(gross_profit_per_bid/10000):,}万)" style="cursor:help;">
                    <span>年間粗利額 (ベース)</span><span>¥{int(base_sales/10000):,}万</span>
                </div>
                <div class="vs-item" title="【計算式】1日の手動検索時間({c['labor_search_hour']}h) × 担当者時給(¥{c['labor_cost_per_hour']:,}) × 年間稼働日数({days}日)" style="cursor:help;">
                    <span style="color:#EF4444;">人力検索コスト</span><span style="color:#EF4444;">- ¥{int(ann_manual_cost/10000):,}万</span>
                </div>
                <div class="vs-item" title="【入力値】年間マーケティング費用" style="cursor:help;">
                    <span style="color:#EF4444;">マーケティング費</span><span style="color:#EF4444;">- ¥{int(market_c/10000):,}万</span>
                </div>
                <div class="vs-total" title="【計算式】年間粗利額(ベース) － 人力検索コスト － マーケティング費" style="cursor:help;">
                    単年 純利益<br><span style="font-size:1.2rem;">¥{int(man_1y/10000):,}万</span>
                </div>
                <div class="vs-total-large" title="【計算式】単年純利益 × 5年間" style="background:#F1F5F9; border-color:#CBD5E1; color:#475569; cursor:help;">
                    <div style="font-size:12px; font-weight:normal;">5年累計 純利益</div>
                    ¥{int(man_5y/10000):,}万
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with v2:
            st.markdown(f"""
            <div class="vs-box" style="border: 2px solid {C1}; background: #F0F9FF;">
                <div class="vs-title" style="color: {C1};">🚀 ツール導入（NJSS ＋ マーケティング）</div>
                <div class="vs-item highlight" title="【計算式】向上後応札数({int(tool_bids)}件) × 向上後勝率({int(tool_win_rate*100)}%) × 1案件平均粗利(¥{int(gross_profit_per_bid/10000):,}万)" style="cursor:help;">
                    <span>年間粗利額 (分析・網羅UP)</span><span>¥{int(tool_sales/10000):,}万</span>
                </div>
                <div class="vs-item" title="【計算式】1日の確認時間({c.get('tool_labor_search_hour', 0.5)}h) × 担当者時給(¥{c['labor_cost_per_hour']:,}) × 年間稼働日数({days}日)" style="cursor:help;">
                    <span style="color:#10B981; font-weight:bold;">ツール運用人件費</span><span style="color:#10B981; font-weight:bold;">- ¥{int(ann_tool_labor_cost/10000):,}万</span>
                </div>
                <div class="vs-item" title="【計算式】NJSS月額費用(¥{c['n_month']:,}) × 12ヶ月" style="cursor:help;">
                    <span style="color:#EF4444;">NJSS利用費(初期含まず)</span><span style="color:#EF4444;">- ¥{int(nj_monthly_annual/10000):,}万</span>
                </div>
                <div class="vs-item" title="【入力値】年間マーケティング費用" style="cursor:help;">
                    <span style="color:#EF4444;">マーケティング費</span><span style="color:#EF4444;">- ¥{int(market_c/10000):,}万</span>
                </div>
                <div class="vs-total" title="【計算式】年間粗利額 － ツール運用人件費 － NJSS利用費(年間) － マーケ費 － NJSS初期費用(初年度のみ¥{c['n_init']:,})" style="color:{C1}; cursor:help;">
                    単年 純利益 (※初年度は初期費用を含む)<br><span style="font-size:1.2rem;">¥{int(nj_1y/10000):,}万</span>
                </div>
                <div class="vs-total-large" title="【計算式】5年間の純利益の累計（初年度の初期費用マイナス分も含む）" style="cursor:help;">
                    <div style="font-size:12px; font-weight:normal; color:#0176D3;">5年累計 純利益</div>
                    ¥{int(nj_5y/10000):,}万
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="sec">7. 累積純利益シミュレーション（5カ年）</div>', unsafe_allow_html=True)
        
        tab_graph, tab_table = st.tabs(["📈 グラフ表示", "📊 テーブル表示（詳細）"])
        with tab_graph:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_roi["年度"], y=df_roi["人力+ﾏｰｹ (累積)"], name="現状 純利益(累積)", mode="lines+markers", line=dict(color="#94A3B8", width=3)))
            fig.add_trace(go.Scatter(x=df_roi["年度"], y=df_roi["NJSS+ﾏｰｹ (累積)"], name="NJSS 純利益(累積)", mode="lines+markers", line=dict(color=C1, width=3)))
            fig.add_trace(go.Scatter(x=df_roi["年度"], y=df_roi["入札王+ﾏｰｹ (累積)"], name="入札王 純利益(累積)", mode="lines+markers", line=dict(color=C2, width=3)))
            fig.add_trace(go.Scatter(x=df_roi["年度"], y=df_roi["人力コスト(累積)"], name="現状 コスト(累積)", mode="lines", line=dict(color="#CBD5E1", width=2, dash="dot")))
            fig.add_trace(go.Scatter(x=df_roi["年度"], y=df_roi["NJSSコスト(累積)"], name="NJSS コスト(累積)", mode="lines", line=dict(color="#93C5FD", width=2, dash="dot")))
            fig.add_trace(go.Scatter(x=df_roi["年度"], y=df_roi["入札王コスト(累積)"], name="入札王 コスト(累積)", mode="lines", line=dict(color="#5EEAD4", width=2, dash="dot")))
            
            fig.update_layout(**PLY, hovermode="x unified", yaxis_title="累積金額 (円)", height=350)
            st.plotly_chart(fig, use_container_width=True)
            
        with tab_table:
            st.caption("単位：円（全コスト差し引き後の手元に残る純利益、および累積コスト）")
            styled_df = df_roi[["年度", "人力+ﾏｰｹ (累積)", "NJSS+ﾏｰｹ (累積)", "入札王+ﾏｰｹ (累積)", "人力コスト(累積)", "NJSSコスト(累積)", "入札王コスト(累積)"]].style.format(
                {"人力+ﾏｰｹ (累積)": "{:,.0f}", "NJSS+ﾏｰｹ (累積)": "{:,.0f}", "入札王+ﾏｰｹ (累積)": "{:,.0f}", "人力コスト(累積)": "{:,.0f}", "NJSSコスト(累積)": "{:,.0f}", "入札王コスト(累積)": "{:,.0f}"}
            )
            st.dataframe(styled_df, hide_index=True, use_container_width=True)

    # ─────────────────────────────────────────────────────────────────
    #  サマリーレポート セクション
    # ─────────────────────────────────────────────────────────────────
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown('<div class="sec" style="font-size:1.3rem;">8. 稟議・報告用 サマリーレポート（PowerPoint転記用）</div>', unsafe_allow_html=True)
    st.info("💡 以下のレポート全体は白背景で統一されています。そのままスクリーンショットを撮ってスライドに貼り付けてご活用いただけます。\n\n🔍 **テーブルの数値にカーソルを合わせると、計算式と内訳が確認できます。**")
    
    diff_5y_n = nj_5y - man_5y
    diff_5y_k = ki_5y - man_5y
    
    nj_first_year_cost = c["n_init"] + nj_monthly_annual
    be_orders_1y_n = (nj_first_year_cost / gross_profit_per_bid) if gross_profit_per_bid > 0 else 0
    
    ki_monthly_annual = c["k_month"] * 12
    ki_first_year_cost = c["k_init"] + ki_monthly_annual
    be_orders_1y_k = (ki_first_year_cost / gross_profit_per_bid) if gross_profit_per_bid > 0 else 0
    
    st.markdown(f"""
    <div class="report-wrap">
        <div class="rep-title">【提案】入札情報収集ツールの導入による売上拡大および業務効率化</div>
    """, unsafe_allow_html=True)
    
    col_rep1, col_rep2 = st.columns([1.2, 1])
    
    with col_rep1:
        st.markdown('<div class="rep-h2">1. 比較シミュレーションの前提</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="rep-text">本レポートでは、今後新たに入札市場へ参入するにあたり、<b>「ツールを使用せず人力のみで運用した場合」</b>と<b>「入札情報収集ツール（NJSS・入札王）を導入した場合」</b>の収益性を比較しています。<br><br><span style="font-size:13px; color:#475569;">※現在、人力での検索業務は行っていませんが、今後ツール未導入のまま入札に参加した場合に発生する「検索人件費（1日 {c["labor_search_hour"]} 時間 × 年間 {days} 日想定）」と「案件の見逃し（機会損失）」を可視化するため、比較対象（ベースライン）として設定しています。ツール導入後も日々の確認・仕分け作業として1日 {c.get("tool_labor_search_hour", 0.5)} 時間の人件費が発生する前提で現実的な算出を行っています。</span></div>', unsafe_allow_html=True)
        
        st.markdown('<div class="rep-h2">2. 試算の前提条件（算出根拠）</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <ul class="rep-ul">
            <li><b>平均落札金額</b>: 約 {int(avg_bid/10000):,} 万円 <span style="font-size:12px;color:#64748b;">（※登録済み過去案件のデータより算出）</span></li>
            <li><b>基本受注率</b>: {c['win_rate']} %</li>
            <li><b>平均粗利率</b>: {c['margin']} %</li>
        </ul>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="rep-h2">3. 定量的な期待効果</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <ul class="rep-ul">
            <li><b>応札機会の拡大</b>: 網羅的な案件収集により見逃しを防ぎ、応札数が年間 {c['annual_bids']}件 から <span class="rep-hi">{int(tool_bids)}件</span> へ増加。</li>
            <li><b>勝率の向上</b>: 過去の落札データ・仕様書分析を通じた戦略的な値付けにより、勝率が {c['win_rate']}% から <span class="rep-hi">{int(tool_win_rate*100)}%</span> に向上。</li>
            <li><b>業務効率化（人件費削減）</b>: 検索にかかる時間を年間 {int(man_h)}時間 から {int(tool_h)}時間に削減し、約 {int(diff_c/10000):,}万円分の見えない人件費を削減。</li>
            <li><b>5年間の純利益創出</b>: 上記売上増・コスト減の相乗効果により、5年間で追加の利益（キャッシュフロー）を創出。<br><b>→ <span class="rep-hi">NJSS 約 {int(diff_5y_n/10000):,} 万円 / 入札王 約 {int(diff_5y_k/10000):,} 万円</span></b></li>
        </ul>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="rep-h2">4. コストと費用回収に必要な受注件数</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <ul class="rep-ul">
            <li><b>初期費用</b>: NJSS ¥{c['n_init']:,} / 入札王 ¥{c['k_init']:,}</li>
            <li><b>月額利用料</b>: NJSS ¥{c['n_month']:,}（年間 ¥{nj_monthly_annual:,}）<br>　　　　　　 入札王 ¥{c['k_month']:,}（年間 ¥{ki_monthly_annual:,}）</li>
            <li><b>コスト回収に必要な受注件数</b>: <br><b>→ <span class="rep-hi">NJSS 年間 約 {be_orders_1y_n:.1f} 件 / 入札王 年間 約 {be_orders_1y_k:.1f} 件</span></b><br><span style="font-size:12px;color:#64748b;">※1案件あたりの平均粗利（¥{int(gross_profit_per_bid/10000):,}万）をもとに算出。年間でこの件数さえ受注できれば初年度のツール費用（初期＋月額12ヶ月）は完全にペイでき、それ以上はすべて自社の純利益となる。</span></li>
        </ul>
        """, unsafe_allow_html=True)
        
    with col_rep2:
        st.markdown('<div class="rep-h2" style="margin-top: 0px;">5. 5年累計 利益・コストシミュレーション</div>', unsafe_allow_html=True)
        
        fig_rep = go.Figure()
        fig_rep.add_trace(go.Bar(x=df_roi["年度"], y=df_roi["人力+ﾏｰｹ (累積)"], name="現状 純利益", marker_color="#94A3B8"))
        fig_rep.add_trace(go.Bar(x=df_roi["年度"], y=df_roi["入札王+ﾏｰｹ (累積)"], name="入札王 純利益", marker_color=C2))
        fig_rep.add_trace(go.Bar(x=df_roi["年度"], y=df_roi["NJSS+ﾏｰｹ (累積)"], name="NJSS 純利益", marker_color=C1))
        
        fig_rep.add_trace(go.Scatter(x=df_roi["年度"], y=df_roi["人力コスト(累積)"], name="現状 コスト", mode="lines+markers", line=dict(color="#64748B", dash="dash", width=2)))
        fig_rep.add_trace(go.Scatter(x=df_roi["年度"], y=df_roi["入札王コスト(累積)"], name="入札王 コスト", mode="lines+markers", line=dict(color="#0F766E", width=2)))
        fig_rep.add_trace(go.Scatter(x=df_roi["年度"], y=df_roi["NJSSコスト(累積)"], name="NJSS コスト", mode="lines+markers", line=dict(color="#0284C7", width=2)))

        fig_rep.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=-0.25, x=0.5, xanchor="center", font=dict(size=10)),
            yaxis_title="累積金額 (円)", xaxis_title="", height=320,
            margin=dict(l=10, r=10, t=10, b=10), barmode="group"
        )
        st.plotly_chart(fig_rep, use_container_width=True)
        
        metrics = [
            ("NJSS 純利益 (累積)", "NJSS+ﾏｰｹ (累積)", C1, "bold"),
            ("入札王 純利益 (累積)", "入札王+ﾏｰｹ (累積)", C2, "bold"),
            ("現状 純利益 (累積)", "人力+ﾏｰｹ (累積)", "#475569", "normal"),
            ("NJSS コスト (累積)", "NJSSコスト(累積)", "#0284C7", "normal"),
            ("入札王 コスト (累積)", "入札王コスト(累積)", "#0D9488", "normal"),
            ("現状 コスト (累積)", "人力コスト(累積)", "#64748B", "normal")
        ]
        
        # ツールチップ付きのHTMLテーブル
        table_html = """
        <table style="width:100%; border-collapse: collapse; font-size: 11.5px; margin-top: 5px; background: #FFFFFF; border: 1px solid #E2E8F0;">
            <tr style="border-bottom: 2px solid #CBD5E1;">
                <th style="text-align:left; padding:5px; color:#475569;">項目 (万円)</th>
        """
        for y in df_roi["年度"]: table_html += f'<th style="text-align:right; padding:5px; color:#475569;">{y}</th>'
        table_html += '</tr>'
        
        for label, col_name, color, weight in metrics:
            tt_col = f"tt_{col_name}" # ツールチップ用のカラム名
            table_html += f'<tr style="border-bottom: 1px solid #E2E8F0; background: #FFFFFF;"><td style="text-align:left; padding:5px; color:{color}; font-weight:{weight};">{label}</td>'
            for idx, val in enumerate(df_roi[col_name]):
                tt_text = df_roi[tt_col].iloc[idx] # dataframeからホバー用のテキストを取得
                table_html += f'<td title="{tt_text}" style="text-align:right; padding:5px; color:{color}; font-weight:{weight}; background: #FFFFFF; cursor: help;">{int(val/10000):,}</td>'
            table_html += '</tr>'
        table_html += '</table>'
        
        st.markdown(table_html, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="rep-box" style="margin-top:15px; display:flex; justify-content:space-around;">
            <div>
                <div style="font-size:12px; color:#475569; font-weight:bold;">NJSS 追加利益（5年間）</div>
                <div style="font-size:20px; color:{C1}; font-weight:900; margin-top:3px;">＋ ¥{int(diff_5y_n/10000):,} 万</div>
            </div>
            <div style="border-left: 1px solid #E2E8F0; margin: 0 10px;"></div>
            <div>
                <div style="font-size:12px; color:#475569; font-weight:bold;">入札王 追加利益（5年間）</div>
                <div style="font-size:20px; color:{C2}; font-weight:900; margin-top:3px;">＋ ¥{int(diff_5y_k/10000):,} 万</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
#  PAGE: MANUAL & DATA MANAGEMENT
# ─────────────────────────────────────────────────────────────────
elif current_page == "マニュアル":
    page_header("自走式 PoC評価マニュアル", "検証フロー・API設定ガイド")
    st.markdown("**1. 過去案件データの準備**\n「案件データ入力」画面にターゲット案件を入力。テキストコピペ（Gemini AI）での自動入力が便利です。\n**2. ツールでの検索実測**\n各ツールで案件を検索し「掲載あり」にチェック。\n**3. キーワード検索ボリューム確認**\n「ワード検索数」画面で得意領域のキーワードを入力し、ヒット件数を保存します。\n**4. コストシミュレーション設定**\n「ROI分析」画面で各ツールの見積金額・自社の受注率・粗利率を入力してシミュレーションを実行。\n**5. ダッシュボードで最終判断**\n「ダッシュボード」で推奨テキストを確認し、稟議書に添付します。")

elif current_page == "データ管理":
    page_header("データ一括管理・初期化", "CSVインポート / データリセット")
    with st.container(border=True):
        sec("CSV一括インポート")
        uf = st.file_uploader("CSVをアップロード", type="csv")
        if uf:
            try:
                try: im = pd.read_csv(uf, encoding="utf-8-sig")
                except UnicodeDecodeError: im = pd.read_csv(uf, encoding="shift-jis")
                st.dataframe(im.head(), use_container_width=True)
                if st.button("このデータを書き込む", use_container_width=True):
                    new_p = []; today_str = datetime.date.today().strftime("%Y-%m-%d")
                    for _, row in im.iterrows():
                        tag = str(row.get("ID",""))
                        if tag == "SETTING_COST":
                            item = str(row.get("自治体名",""))
                            val = safe_num(row.get("落札金額(千円)"))
                            if "NJSS初期" in item: st.session_state.costs["n_init"] = int(val)
                            elif "NJSS月額" in item: st.session_state.costs["n_month"] = int(val)
                            elif "入札王初期" in item: st.session_state.costs["k_init"] = int(val)
                            elif "入札王月額" in item: st.session_state.costs["k_month"] = int(val)
                            elif "受注率" in item: st.session_state.costs["win_rate"] = int(val)
                            elif "粗利率" in item: st.session_state.costs["margin"] = int(val)
                            elif "応札数" in item: st.session_state.costs["annual_bids"] = int(val)
                        elif tag == "SETTING_WORD":
                            w = str(row.get("自治体名",""))
                            if w:
                                if w not in st.session_state.search_words: st.session_state.search_words.append(w)
                                st.session_state.search_counts[w] = {"NJSS_入札案件": 0, "入札王_入札案件": 0, "NJSS_落札結果": safe_int(row.get("案件概要")), "入札王_落札結果": safe_int(row.get("落札企業")), "登録日": today_str}
                        else:
                            if pd.notna(row.get("自治体名")) and str(row.get("自治体名")).strip(): new_p.append(row)
                    if new_p: save_bids(pd.concat([load_bids(), pd.DataFrame(new_p)], ignore_index=True))
                    sync_settings(); st.success("全データを正常に読み込み・保存しました。")
            except Exception as e: st.error(f"エラー: {e}")

    with st.container(border=True):
        with st.expander("危険操作：全データの初期化"):
            ok = st.checkbox("すべてのデータを消去することを確認します")
            if st.button("全データを初期化する", use_container_width=True):
                if ok:
                    try:
                        save_bids(pd.DataFrame(columns=COLS_BIDS)); save_settings(pd.DataFrame(columns=COLS_SETTINGS))
                        st.session_state.update({"search_words": [], "search_counts": {}, "costs": {"n_init":0,"n_month":0,"n_opt":0,"k_init":0,"k_month":0,"k_opt":0,"margin":30,"win_rate":20,"annual_bids":30,"labor_search_hour":1.5,"tool_labor_search_hour":0.5,"labor_days_per_year":240,"labor_cost_per_hour":3000,"marketing_annual":500000,"tool_bid_increase_rate":40,"tool_win_rate_boost":5}})
                        st.success("初期化完了。")
                    except Exception as e: st.error(f"エラー: {e}")
                else: st.error("確認チェックを入れてください。")
