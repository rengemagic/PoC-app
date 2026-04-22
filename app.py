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
#  SESSION STATE INIT (ROI項目を拡張)
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
        "proposal_labor_cost": 50000,  
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
  --bg: #F4F7FA; --bg2: #FFFFFF; --accent: #0176D3; --muted: #64748B;
}
.kpi { background: var(--bg2); border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.2rem; text-align: center; margin-bottom: 1rem; }
.sec { font-size: 1.15rem; font-weight: 700; border-left: 5px solid var(--accent); padding-left: 12px; margin-bottom: 1rem; margin-top: 1.5rem;}
.logic-box { background: #F8FAFC; border: 1px dashed #CBD5E1; border-radius: 8px; padding: 1rem; margin-top: 1rem; font-size: 0.9rem; color: #334155; }
.logic-box strong { color: #0F172A; }
.logic-eq { color: var(--accent); font-family: monospace; font-size: 1rem; margin: 4px 0 12px 0; display: block; background: #FFFFFF; padding: 6px; border: 1px solid #E2E8F0; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
#  DATA LAYER
# ─────────────────────────────────────────────────────────────────
conn = st.connection("gsheets", type=GSheetsConnection)
COLS_BIDS = ["ID","自治体名","担当部署名","案件概要","公示日","入札日","履行期間","入札方式","参加資格","予算(千円)","落札金額(千円)","自社結果","落札企業","競合1","競合2","競合3","仕様書","NJSS掲載","入札王掲載","URL1","URL2","URL3","URL4","URL5", "検索タグ", "備考"]
COLS_SETTINGS = ["種別", "項目名", "値1", "値2", "値3", "値4", "値5"]

def safe_int(val):
    try: return int(float(str(val).replace(',', ''))) if pd.notna(val) and val != "" else 0
    except: return 0

@st.cache_data(ttl="10m")
def load_bids():
    try:
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        df = conn.read(spreadsheet=url, worksheet="案件データ", ttl="0s")
        return df if not df.empty else pd.DataFrame(columns=COLS_BIDS)
    except: return pd.DataFrame(columns=COLS_BIDS)

def save_bids(df_new):
    conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], worksheet="案件データ", data=df_new.fillna(""))
    load_bids.clear()

def sync_settings():
    rows = []
    for k, v in st.session_state.costs.items(): rows.append({"種別": "COST", "項目名": k, "値1": v})
    conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], worksheet="設定データ", data=pd.DataFrame(rows).fillna(""))

# ─────────────────────────────────────────────────────────────────
#  ROI CALCULATION ENGINE
# ─────────────────────────────────────────────────────────────────
def calc_roi_data():
    c = st.session_state.costs
    df = load_bids()
    avg_bid = 0
    if not df.empty and "落札金額(千円)" in df.columns:
        nums = pd.to_numeric(df["落札金額(千円)"], errors="coerce").fillna(0)
        if (nums > 0).any(): avg_bid = nums[nums > 0].mean() * 1000
    
    rows = []
    # 年間検索稼働費（手動）= 時給 × 時間 × 240日
    annual_manual_search = c["labor_cost_per_hour"] * c["labor_search_hour"] * 240
    
    for y in range(6):
        # 1. ツールなし（As-Is）の利益
        manual_rev = (avg_bid * (c["margin"]/100) * (c["win_rate"]/100) * c["annual_bids"]) * y
        manual_cost = (annual_manual_search + c["marketing_annual"] + (c["proposal_labor_cost"] * c["annual_bids"])) * y
        
        # 2. NJSS導入時の利益
        boost = (1 + c["tool_boost_rate"]/100)
        nj_rev = (avg_bid * (c["margin"]/100) * (c["win_rate"]/100) * (c["annual_bids"] * boost)) * y
        nj_tool_cost = c["n_init"] + (c["n_month"] * 12 + c["n_opt"]) * y
        nj_other_cost = (c["marketing_annual"] + (c["proposal_labor_cost"] * c["annual_bids"] * boost)) * y
        
        # 3. 入札王導入時の利益
        ki_rev = (avg_bid * (c["margin"]/100) * (c["win_rate"]/100) * (c["annual_bids"] * boost)) * y
        ki_tool_cost = c["k_init"] + (c["k_month"] * 12 + c["k_opt"]) * y
        ki_other_cost = (c["marketing_annual"] + (c["proposal_labor_cost"] * c["annual_bids"] * boost)) * y

        rows.append({
            "年": y,
            "現状(ツールなし)": manual_rev - manual_cost,
            "NJSS導入": nj_rev - (nj_tool_cost + nj_other_cost),
            "入札王導入": ki_rev - (ki_tool_cost + ki_other_cost),
            "NJSS累積コスト": nj_tool_cost,
            "入札王累積コスト": ki_tool_cost
        })
    return pd.DataFrame(rows), avg_bid

# ─────────────────────────────────────────────────────────────────
#  PAGE: ROI ANALYSIS
# ─────────────────────────────────────────────────────────────────
def show_roi_page():
    st.title("ROI・事業性分析")
    st.markdown("ツールの直接費用だけでなく、人件費や機会損失を含めた真の投資対効果を算出します。")
    
    p_df, avg_bid = calc_roi_data()
    c = st.session_state.costs

    col_set1, col_set2 = st.columns([1, 2])
    
    with col_set1:
        st.markdown('<div class="sec">1. 隠れたコスト（人件費・販促費）</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.session_state.costs["labor_search_hour"] = st.number_input("手動での検索時間（1日合計/h）", value=float(c["labor_search_hour"]), step=0.5)
            st.session_state.costs["labor_cost_per_hour"] = st.number_input("担当者時給（円）", value=int(c["labor_cost_per_hour"]), step=100)
            st.session_state.costs["proposal_labor_cost"] = st.number_input("1案件あたりの応札工数（円）", value=int(c["proposal_labor_cost"]), step=1000, help="資料作成などにかかる人件費")
            st.session_state.costs["marketing_annual"] = st.number_input("年間マーケティング費用（円）", value=int(c["marketing_annual"]), step=10000, help="DM、テレアポ、ウェビナー費用など")

        st.markdown('<div class="sec">2. 営業指標とツール効果</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.session_state.costs["annual_bids"] = st.number_input("年間想定応札数（件）", value=int(c["annual_bids"]))
            st.session_state.costs["win_rate"] = st.slider("平均受注率（%）", 0, 100, int(c["win_rate"]))
            st.session_state.costs["margin"] = st.slider("平均粗利率（%）", 0, 100, int(c["margin"]))
            st.session_state.costs["tool_boost_rate"] = st.slider("ツール導入による案件捕捉増加率（%）", 0, 100, int(c["tool_boost_rate"]), help="ツールを使うことで見つかる案件がどれだけ増えるか")

        if st.button("シミュレーションを更新", use_container_width=True, type="primary"):
            sync_settings(); st.rerun()

    with col_set2:
        st.markdown('<div class="sec">3. 投資回収シミュレーション（5カ年）</div>', unsafe_allow_html=True)
        
        # グラフ: 累積利益推移
        fig = px.line(p_df, x="年", y=["現状(ツールなし)", "NJSS導入", "入札王導入"], 
                      title="累積純利益の推移（全コスト差し引き後）",
                      color_discrete_map={"現状(ツールなし)": "#94A3B8", "NJSS導入": "#0176D3", "入札王導入": "#10B981"})
        fig.update_layout(hovermode="x unified", yaxis_title="純利益 (円)")
        st.plotly_chart(fig, use_container_width=True)

        # KPIパネル
        k1, k2, k3 = st.columns(3)
        nj_final_profit = p_df.iloc[-1]["NJSS導入"]
        manual_final_profit = p_df.iloc[-1]["現状(ツールなし)"]
        annual_search_saved = c["labor_cost_per_hour"] * c["labor_search_hour"] * 240
        boost_rev = (avg_bid * (c["margin"]/100) * (c["win_rate"]/100) * (c["annual_bids"] * c["tool_boost_rate"]/100))
        
        with k1:
            st.metric("NJSS導入による利益純増(5年)", f"¥{int(nj_final_profit - manual_final_profit):,}")
        with k2:
            st.metric("年間削減される検索工数", f"¥{int(annual_search_saved):,}")
        with k3:
            st.metric("捕捉アップによる年間増益", f"¥{int(boost_rev):,}")

        # 📊 計算ロジック・計算式のエクスパンダー
        with st.expander("📊 算出ロジック・計算式の詳細（プレゼン・稟議用）", expanded=False):
            st.markdown(f"""
            <div class="logic-box">
                <strong>① 基本となる年間期待売上（ベース）</strong>
                <span class="logic-eq">平均落札額(¥{int(avg_bid):,}) × 粗利率({c['margin']}%) × 受注率({c['win_rate']}%) × 想定応札数({c['annual_bids']}件)</span>
                
                <strong>② 現状（ツール未導入）の年間コスト</strong>
                <span class="logic-eq">検索人件費(¥{int(annual_search_saved):,}) ＋ 年間販促費(¥{int(c['marketing_annual']):,}) ＋ 応札人件費(¥{int(c['proposal_labor_cost'] * c['annual_bids']):,})</span>
                <ul style="font-size:0.85rem; color:#64748b; margin-top:0;">
                    <li>※検索人件費 ＝ 1日{c['labor_search_hour']}h × 時給¥{int(c['labor_cost_per_hour']):,} × 240日</li>
                    <li>※応札人件費 ＝ 1案件¥{int(c['proposal_labor_cost']):,} × {c['annual_bids']}件</li>
                </ul>

                <strong>③ ツール導入時（NJSS）の年間コスト（初年度）</strong>
                <span class="logic-eq">ツール費用(¥{int(c['n_init'] + c['n_month']*12):,}) ＋ 販促費(¥{int(c['marketing_annual']):,}) ＋ 応札人件費(¥{int(c['proposal_labor_cost'] * c['annual_bids'] * (1 + c['tool_boost_rate']/100)):,})</span>
                <ul style="font-size:0.85rem; color:#64748b; margin-top:0;">
                    <li>※導入時は検索人件費が「ゼロ」になります。</li>
                    <li>※応札人件費は、捕捉増加分({c['tool_boost_rate']}%)だけ作成コストも増えるとして算出。</li>
                </ul>

                <strong>④ ツール導入時の年間期待売上（機会損失の回収）</strong>
                <span class="logic-eq">年間期待売上（ベース） × 捕捉増加率(1.{c['tool_boost_rate']})</span>
            </div>
            """, unsafe_allow_html=True)

        with st.expander("💡 提案：事業化に向けた「NJSS」有利のポイント"):
            st.markdown(f"""
            - **機会損失の最小化**: 現状よりも案件捕捉が **{c['tool_boost_rate']}%** 向上することで、年間 **¥{int(boost_rev):,}** の利益上乗せが見込めます。
            - **コア業務への集中**: 年間 **¥{int(annual_search_saved):,}** 分の「ただ探すだけ」の時間を、戦略策定や資料作成に充てることが可能になります。
            - **損益分岐点**: ツール費用はかかりますが、捕捉数と受注率の向上により、手動運用よりも早期に高い収益性を実現します。
            """)

# ─────────────────────────────────────────────────────────────────
#  MAIN APP ROUTING
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### PoC Menu")
    menu = st.radio("表示切替", ["ダッシュボード", "案件データ入力", "ワード検索数", "ROI分析"], index=3)
    st.session_state.current_page = menu

if st.session_state.current_page == "ROI分析":
    show_roi_page()
else:
    st.info("他のページは既存のコードをそのまま維持してください。")
