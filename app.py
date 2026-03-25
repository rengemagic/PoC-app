import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection
import io
import csv
import traceback

# --- 1. UI & CSS (アイコン・白枠完全消去 & Salesforce風タイトル装飾) ---
st.set_page_config(page_title="入札ツール精密評価ボード", layout="wide")

st.markdown("""
    <style>
    [data-testid="stHeader"] { display: none !important; }
    [data-testid="stAppViewContainer"] { padding-top: 0rem !important; background-color: #FFFFFF !important; }
    [data-testid="block-container"] { padding-top: 2rem !important; padding-bottom: 2rem !important; }
    .stApp { color: #181818 !important; }
    [data-testid="stSidebar"] { background-color: #1E293B !important; border-right: none !important; }
    [data-testid="stSidebar"] * { color: #CBD5E1 !important; }
    .sidebar-section-header { color: #64748B !important; font-size: 11px !important; font-weight: 700; letter-spacing: 1px; padding: 10px 15px; margin: 20px 0px 5px 0px; text-transform: uppercase; }
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label > div:first-child { display: none !important; }
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label { padding: 12px 16px !important; margin-bottom: 4px !important; border-radius: 6px !important; background-color: transparent; transition: all 0.2s ease-in-out !important; cursor: pointer; width: 100%; display: block; }
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover { background-color: rgba(255, 255, 255, 0.08) !important; color: #FFFFFF !important; }
    [data-testid="stSidebar"] div.stRadio p { color: #F8FAFC !important; font-size: 14px !important; font-weight: 500 !important; margin: 0 !important; }
    .slds-page-header { background-color: #F8FAFC !important; padding: 1.2rem 2rem; border-bottom: 1px solid #E2E8F0; margin: -2rem -4rem 2rem -4rem; border-left: 8px solid #0284C7; }
    .slds-page-header h1 { color: #0F172A !important; font-size: 1.5rem; font-weight: 700; margin: 0; }
    .stButton > button { background-color: #0284C7 !important; color: #FFFFFF !important; border-radius: 6px !important; font-weight: 600 !important; border: none !important; padding: 0.5rem 1.5rem !important; transition: all 0.2s ease; }
    .stButton > button:hover { background-color: #0369A1 !important; transform: translateY(-1px); box-shadow: 0 4px 6px rgba(2, 132, 199, 0.2); }
    div[data-baseweb="input"], div[data-baseweb="input"] > div, div[data-baseweb="base-input"], input, textarea { background-color: #F8FAFC !important; color: #0F172A !important; border-color: #CBD5E1 !important; border-radius: 6px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- セッション状態の初期化 ---
if 'search_words' not in st.session_state: st.session_state.search_words = ["DX推進", "データ分析基盤"]
if 'search_counts' not in st.session_state: st.session_state.search_counts = {}
if 'costs' not in st.session_state: 
    st.session_state.costs = {
        "n_init": 0, "n_month": 0, "n_opt": 0,
        "k_init": 0, "k_month": 0, "k_opt": 0,
        "margin": 20, "win_rate": 20, "annual_bids": 50
    }

# --- 2. スプレッドシート接続 ---
conn = st.connection("gsheets", type=GSheetsConnection)
CORRECT_COLUMNS = ["ID", "自治体名", "案件概要", "仕様書", "予算(千円)", "落札金額(千円)", "落札企業", "応札1", "応札2", "応札3", "NJSS掲載", "入札王掲載", "URL1", "URL2", "URL3", "URL4", "URL5"]

def load_data():
    try:
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        df = conn.read(spreadsheet=url, ttl="0s")
        if "自治体名" not in df.columns: 
            return pd.DataFrame([{col: "" if col != "ID" else i+1 for col in CORRECT_COLUMNS} for i in range(50)])
        return df
    except:
        return pd.DataFrame([{col: "" if col != "ID" else i+1 for col in CORRECT_COLUMNS} for i in range(50)])

# --- 3. サイドバーの構築 ---
with st.sidebar:
    st.markdown('<p class="sidebar-section-header">Menu</p>', unsafe_allow_html=True)
    test_mode = st.toggle("テストモード表示")
    menu_options = ["ダッシュボード", "過去案件情報入力", "ワード検索数", "コスト・ROI分析", "マニュアル"]
    if test_mode: menu_options.append("データ管理 (テスト)")
    page = st.radio("メニュー", menu_options, label_visibility="collapsed")

def draw_kpi_card(title, value):
    st.markdown(f"""
        <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 1.5rem; text-align: center; margin-bottom: 1.5rem;">
            <p style="color: #64748B; font-size: 13px; font-weight: 600; margin: 0 0 8px 0; text-transform: uppercase;">{title}</p>
            <p style="color: #0284C7; font-size: 36px; font-weight: 700; margin: 0; line-height: 1;">{value}</p>
        </div>
    """, unsafe_allow_html=True)

# 損益分岐点・5年推移の計算ロジック
def calculate_projections():
    df = load_data()
    valid_df = df[df["自治体名"].notna() & (df["自治体名"] != "")]
    avg_bid = valid_df["落札金額(千円)"].mean() * 1000 if not valid_df.empty else 0
    
    # 年間期待利益 = 平均落札額 × 粗利 × 受注率 × 年間応札数
    annual_profit = avg_bid * (st.session_state.costs["margin"]/100) * (st.session_state.costs["win_rate"]/100) * st.session_state.costs["annual_bids"]
    
    data = []
    for year in range(6): # 0年(初期)〜5年
        # NJSS
        n_cost = st.session_state.costs["n_init"] + ((st.session_state.costs["n_month"]*12 + st.session_state.costs["n_opt"]) * year)
        # 入札王
        k_cost = st.session_state.costs["k_init"] + ((st.session_state.costs["k_month"]*12 + st.session_state.costs["k_opt"]) * year)
        
        revenue = annual_profit * year
        data.append({
            "年": year, 
            "NJSS累積コスト": n_cost, "NJSS利益": revenue - n_cost,
            "入札王累積コスト": k_cost, "入札王利益": revenue - k_cost,
            "累積売上": revenue
        })
    return pd.DataFrame(data), annual_profit

# --- 4. コンテンツ表示 ---

if page == "ダッシュボード":
    st.markdown('<div class="slds-page-header"><h1>ダッシュボード</h1></div>', unsafe_allow_html=True)
    df = load_data()
    valid_df = df[df["自治体名"].notna() & (df["自治体名"] != "")]

    if valid_df.empty:
        st.warning("データがありません。左のメニューから「過去案件情報入力」を開き、検証結果を登録してください。")
    else:
        kpi1, kpi2, kpi3 = st.columns(3)
        nj_count = valid_df["NJSS掲載"].astype(str).str.upper().isin(["TRUE", "1", "1.0", "YES"]).sum()
        ki_count = valid_df["入札王掲載"].astype(str).str.upper().isin(["TRUE", "1", "1.0", "YES"]).sum()
        with kpi1: draw_kpi_card("NJSS 網羅率", f"{(nj_count/len(valid_df)*100):.1f}%")
        with kpi2: draw_kpi_card("入札王 網羅率", f"{(ki_count/len(valid_df)*100):.1f}%")
        with kpi3: draw_kpi_card("検証完了案件", f"{len(valid_df)} 件")

        # 5年シミュレーション（ダッシュボード版）
        proj_df, _ = calculate_projections()
        fig_proj = px.line(proj_df, x="年", y=["NJSS利益", "入札王利益"], title="5年間の累積利益予測推移", color_discrete_map={"NJSS利益": "#0284C7", "入札王利益": "#F59E0B"})
        st.plotly_chart(fig_proj, use_container_width=True)

        st.markdown('<div class="slds-page-header" style="margin-top: 3rem; margin-bottom: 2rem;"><h1>総合判定・分析レポート</h1></div>', unsafe_allow_html=True)
        if st.button("総合判定を実行する", use_container_width=True):
            # 判定ロジック
            nj_cov = (nj_count / len(valid_df) * 100)
            ki_cov = (ki_count / len(valid_df) * 100)
            
            nj_sw, ki_sw = 0, 0
            for counts in st.session_state.search_counts.values():
                if counts["NJSS"] > counts["入札王"]: nj_sw += 1
                elif counts["入札王"] > counts["NJSS"]: ki_sw += 1
                else: nj_sw += 0.5; ki_sw += 0.5
            total_sw = nj_sw + ki_sw
            nj_search = (nj_sw / total_sw * 100) if total_sw > 0 else 50
            ki_search = (ki_sw / total_sw * 100) if total_sw > 0 else 50
            
            # 5年利益をスコア化
            n_5y_profit = proj_df.iloc[-1]["NJSS利益"]
            k_5y_profit = proj_df.iloc[-1]["入札王利益"]
            max_p = max(n_5y_profit, k_5y_profit, 1)
            nj_profit_score = max(0, (n_5y_profit / max_p * 100))
            ki_profit_score = max(0, (k_5y_profit / max_p * 100))

            fig_radar = go.Figure()
            cat = ['網羅率', '検索精度', '収益性(5年)', '網羅率']
            fig_radar.add_trace(go.Scatterpolar(r=[nj_cov, nj_search, nj_profit_score, nj_cov], theta=cat, fill='toself', name='NJSS', line_color='#0284C7'))
            fig_radar.add_trace(go.Scatterpolar(r=[ki_cov, ki_search, ki_profit_score, ki_cov], theta=cat, fill='toself', name='入札王', line_color='#F59E0B'))
            fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), margin=dict(t=30, b=30))
            
            c_radar, c_res = st.columns([1, 1])
            with c_radar: st.plotly_chart(fig_radar, use_container_width=True)
            with c_res:
                st.markdown("### 判定レポート")
                nj_total = nj_cov + nj_search + nj_profit_score
                ki_total = ki_cov + ki_search + ki_profit_score
                if nj_total > ki_total: st.success(f"総合判定：【 NJSS 】が優勢です。\n\n網羅率と収益性のバランスが最も優れています。")
                elif ki_total > nj_total: st.success(f"総合判定：【 入札王 】が優勢です。\n\nコストパフォーマンスに基づいた高い利益率が期待できます。")
                else: st.info("総合判定：【 互角 】です。運用のしやすさでご判断ください。")

elif page == "過去案件情報入力":
    st.markdown('<div class="slds-page-header"><h1>過去案件情報入力</h1></div>', unsafe_allow_html=True)
    df_current = load_data()
    valid_df = df_current[df_current["自治体名"].notna() & (df_current["自治体名"] != "")].copy()
    
    with st.form("entry_form", clear_on_submit=True):
        st.markdown("#### 基本情報")
        c1, c2 = st.columns(2)
        with c1: municipality = st.text_input("自治体名 (必須)", placeholder="例：東京都")
        with c2: summary = st.text_area("案件概要", placeholder="例：システム改修")
        st.markdown("---")
        st.markdown("#### 落札・応札情報")
        c3, c4 = st.columns(2)
        with c3: winner = st.text_input("落札企業"); winning_bid = st.number_input("落札金額 (単位: 千円)", min_value=0)
        with c4: b1 = st.text_input("応札1"); b2 = st.text_input("応札2"); b3 = st.text_input("応札3")
        st.markdown("---")
        st.markdown("#### ツール掲載確認")
        c5, c6, c7 = st.columns(3)
        with c5: spec = st.checkbox("仕様書あり")
        with c6: nj_l = st.checkbox("NJSS掲載")
        with c7: ki_l = st.checkbox("入札王掲載")
        if st.form_submit_button("この案件を保存する", use_container_width=True):
            if municipality:
                new_rec = pd.DataFrame([{"ID": len(valid_df)+1, "自治体名": municipality, "案件概要": summary, "仕様書": spec, "予算(千円)": 0, "落札金額(千円)": winning_bid, "落札企業": winner, "応札1": b1, "応札2": b2, "応札3": b3, "NJSS掲載": nj_l, "入札王掲載": ki_l}])
                updated = pd.concat([valid_df, new_rec], ignore_index=True).fillna("")
                try:
                    conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=updated)
                    st.success("スプレッドシートへの保存に成功しました。")
                    st.rerun()
                except: st.error("スプレッドシートへの保存に失敗しました。")
            else: st.error("自治体名は必須です。")
    if not valid_df.empty:
        st.dataframe(valid_df, hide_index=True, use_container_width=True)

elif page == "コスト・ROI分析":
    st.markdown('<div class="slds-page-header"><h1>コスト・ROI分析</h1></div>', unsafe_allow_html=True)
    
    st.markdown("#### 各ツールのコスト設定")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**NJSS**")
        n_i = st.number_input("初期費用 (円)", value=st.session_state.costs["n_init"], step=10000)
        n_m = st.number_input("月額費用 (円)", value=st.session_state.costs["n_month"], step=10000)
        n_o = st.number_input("年間オプション (円)", value=st.session_state.costs["n_opt"], step=10000)
    with c2:
        st.markdown("**入札王**")
        k_i = st.number_input("初期費用 (円)", value=st.session_state.costs["k_init"], step=10000)
        k_m = st.number_input("月額費用 (円)", value=st.session_state.costs["k_month"], step=10000)
        k_o = st.number_input("年間オプション (円)", value=st.session_state.costs["k_opt"], step=10000)
    
    st.markdown("---")
    st.markdown("#### 運用シミュレーション設定")
    cs1, cs2, cs3 = st.columns(3)
    with cs1: win_rate = st.number_input("受注率 (%)", value=st.session_state.costs["win_rate"], min_value=1, max_value=100)
    with cs2: margin = st.number_input("粗利率 (%)", value=st.session_state.costs["margin"], min_value=1, max_value=100)
    with cs3: annual_bids = st.number_input("想定年間応札数 (件)", value=st.session_state.costs["annual_bids"], min_value=1)

    if st.button("設定を保存して分析グラフを生成", use_container_width=True):
        st.session_state.costs.update({"n_init": n_i, "n_month": n_m, "n_opt": n_o, "k_init": k_i, "k_month": k_m, "k_opt": k_o, "margin": margin, "win_rate": win_rate, "annual_bids": annual_bids})
        st.success("分析データを更新しました。")

    proj_df, annual_profit = calculate_projections()
    
    st.markdown("---")
    st.markdown("### 5年間収益・損益分岐点シミュレーション")
    fig_bep = go.Figure()
    fig_bep.add_trace(go.Scatter(x=proj_df["年"], y=proj_df["累積売上"], name="累積売上(期待値)", line=dict(color="#10B981", width=4)))
    fig_bep.add_trace(go.Scatter(x=proj_df["年"], y=proj_df["NJSS累積コスト"], name="NJSS累積コスト", line=dict(color="#0284C7", dash='dash')))
    fig_bep.add_trace(go.Scatter(x=proj_df["年"], y=proj_df["入札王累積コスト"], name="入札王累積コスト", line=dict(color="#F59E0B", dash='dash')))
    fig_bep.update_layout(title="累積コストと売上の交差点（損益分岐点）", template="plotly_white")
    st.plotly_chart(fig_bep, use_container_width=True)

    st.markdown("### 累積利益推移")
    fig_profit = px.bar(proj_df, x="年", y=["NJSS利益", "入札王利益"], barmode="group", color_discrete_map={"NJSS利益": "#0284C7", "入札王利益": "#F59E0B"})
    st.plotly_chart(fig_profit, use_container_width=True)

elif page == "データ管理 (テスト)":
    st.markdown('<div class="slds-page-header"><h1>データ管理</h1></div>', unsafe_allow_html=True)
    
    st.markdown("### サンプルデータの活用")
    st.write("インポート用のテンプレートとしてご利用ください。")
    sample_df = pd.DataFrame([
        {"ID": 1, "自治体名": "東京都", "案件概要": "サンプル案件A", "仕様書": True, "落札金額(千円)": 50000, "NJSS掲載": True, "入札王掲載": False},
        {"ID": 2, "自治体名": "横浜市", "案件概要": "サンプル案件B", "仕様書": False, "落札金額(千円)": 30000, "NJSS掲載": True, "入札王掲載": True}
    ])
    csv_data = sample_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(label="サンプルCSVをダウンロード", data=csv_data, file_name="sample_poc_data.csv", mime="text/csv")

    st.markdown("---")
    uploaded_file = st.file_uploader("CSVインポート", type="csv")
    if uploaded_file:
        try:
            import_df = pd.read_csv(uploaded_file, encoding="utf-8-sig")
            st.dataframe(import_df.head())
            if st.button("このデータを反映する"):
                st.session_state.temp_df = import_df
                st.success("反映しました。過去案件情報入力ページから保存してください。")
        except: st.error("読込失敗")

    st.markdown("---")
    if st.button("すべてのデータを消去する (初期化)", use_container_width=True):
        try:
            conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=pd.DataFrame(columns=CORRECT_COLUMNS))
            st.success("スプレッドシートの初期化に成功しました。")
            st.rerun()
        except: st.error("初期化に失敗しました。")
