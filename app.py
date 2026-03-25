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
    /* 1. ヘッダーと上部白枠の完全排除 */
    [data-testid="stHeader"] { display: none !important; }
    [data-testid="stAppViewContainer"] { padding-top: 0rem !important; background-color: #FFFFFF !important; }
    [data-testid="block-container"] { padding-top: 2rem !important; padding-bottom: 2rem !important; }

    /* サイドバー配色 (モダンダーク) */
    [data-testid="stSidebar"] { background-color: #1E293B !important; border-right: none !important; }
    [data-testid="stSidebar"] * { color: #CBD5E1 !important; }
    .sidebar-section-header { color: #64748B !important; font-size: 11px !important; font-weight: 700; letter-spacing: 1px; padding: 10px 15px; margin: 20px 0px 5px 0px; text-transform: uppercase; }

    /* ラジオボタンの「丸いボタン」を消去 */
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label > div:first-child { display: none !important; }
    
    /* メニュー項目をテキストリンク風に */
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label { padding: 12px 16px !important; margin-bottom: 4px !important; border-radius: 6px !important; background-color: transparent; transition: all 0.2s; cursor: pointer; width: 100%; display: block; }
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover { background-color: rgba(255, 255, 255, 0.08) !important; color: #FFFFFF !important; }
    [data-testid="stSidebar"] div.stRadio p { color: #F8FAFC !important; font-size: 14px !important; font-weight: 500 !important; margin: 0 !important; }

    /* 2. ページヘッダー装飾 (Salesforce Lightning風) */
    .slds-page-header { 
        background-color: #F8FAFC !important; 
        padding: 1.2rem 2rem; 
        border-bottom: 1px solid #E2E8F0; 
        margin: -2rem -4rem 2.5rem -4rem; 
        border-left: 8px solid #0284C7; 
    }
    .slds-page-header h1 { color: #0F172A !important; font-size: 1.5rem; font-weight: 700; margin: 0; }
    
    /* ボタン・入力フォームのデザイン */
    .stButton > button { background-color: #0284C7 !important; color: #FFFFFF !important; border-radius: 6px !important; font-weight: 600 !important; border: none !important; padding: 0.5rem 1.5rem !important; }
    .stButton > button:hover { background-color: #0369A1 !important; transform: translateY(-1px); }
    div[data-baseweb="input"], input, textarea { background-color: #F8FAFC !important; color: #0F172A !important; border-radius: 6px !important; }
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

# --- 3. サイドバー ---
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

def calculate_projections():
    df = load_data()
    valid_df = df[df["自治体名"].notna() & (df["自治体名"] != "")]
    avg_bid = valid_df["落札金額(千円)"].mean() * 1000 if not valid_df.empty else 0
    annual_profit = avg_bid * (st.session_state.costs["margin"]/100) * (st.session_state.costs["win_rate"]/100) * st.session_state.costs["annual_bids"]
    data = []
    for year in range(6):
        n_c = st.session_state.costs["n_init"] + ((st.session_state.costs["n_month"]*12 + st.session_state.costs["n_opt"]) * year)
        k_c = st.session_state.costs["k_init"] + ((st.session_state.costs["k_month"]*12 + st.session_state.costs["k_opt"]) * year)
        rev = annual_profit * year
        data.append({"年": year, "NJSS累積コスト": n_c, "NJSS利益": rev - n_c, "入札王累積コスト": k_c, "入札王利益": rev - k_c, "累積売上": rev})
    return pd.DataFrame(data), annual_profit

# --- 4. コンテンツ表示 ---

if page == "ダッシュボード":
    st.markdown('<div class="slds-page-header"><h1>ダッシュボード</h1></div>', unsafe_allow_html=True)
    df = load_data()
    valid_df = df[df["自治体名"].notna() & (df["自治体名"] != "")]
    if valid_df.empty:
        st.warning("データがありません。左のメニューから「過去案件情報入力」を開き、検証結果を登録してください。")
    else:
        k1, k2, k3 = st.columns(3)
        nj_c = valid_df["NJSS掲載"].astype(str).str.upper().isin(["TRUE", "1", "1.0", "YES"]).sum()
        ki_c = valid_df["入札王掲載"].astype(str).str.upper().isin(["TRUE", "1", "1.0", "YES"]).sum()
        with k1: draw_kpi_card("NJSS 網羅率", f"{(nj_c/len(valid_df)*100):.1f}%")
        with k2: draw_kpi_card("入札王 網羅率", f"{(ki_c/len(valid_df)*100):.1f}%")
        with k3: draw_kpi_card("検証完了案件", f"{len(valid_df)} 件")
        
        proj_df, _ = calculate_projections()
        st.plotly_chart(px.line(proj_df, x="年", y=["NJSS利益", "入札王利益"], title="5年間の累積利益推移シミュレーション", color_discrete_map={"NJSS利益": "#0284C7", "入札王利益": "#F59E0B"}), use_container_width=True)

        st.markdown('<div class="slds-page-header" style="margin-top: 3rem; margin-bottom: 2rem;"><h1>総合判定・分析レポート</h1></div>', unsafe_allow_html=True)
        if st.button("総合判定を実行する", use_container_width=True):
            nj_cov = (nj_c / len(valid_df) * 100)
            ki_cov = (ki_c / len(valid_df) * 100)
            nj_sw, ki_sw = 0, 0
            for cts in st.session_state.search_counts.values():
                if cts["NJSS"] > cts["入札王"]: nj_sw += 1
                elif cts["入札王"] > cts["NJSS"]: ki_sw += 1
                else: nj_sw += 0.5; ki_sw += 0.5
            tot = nj_sw + ki_sw
            nj_s = (nj_sw / tot * 100) if tot > 0 else 50
            ki_s = (ki_sw / tot * 100) if tot > 0 else 50
            n_p5, k_p5 = proj_df.iloc[-1]["NJSS利益"], proj_df.iloc[-1]["入札王利益"]
            mx = max(n_p5, k_p5, 1)
            nj_ps, ki_ps = max(0, (n_p5 / mx * 100)), max(0, (k_p5 / mx * 100))
            fig_r = go.Figure()
            cat = ['網羅率', '検索精度', '収益性(5年)', '網羅率']
            fig_r.add_trace(go.Scatterpolar(r=[nj_cov, nj_s, nj_ps, nj_cov], theta=cat, fill='toself', name='NJSS', line_color='#0284C7'))
            fig_r.add_trace(go.Scatterpolar(r=[ki_cov, ki_s, ki_ps, ki_cov], theta=cat, fill='toself', name='入札王', line_color='#F59E0B'))
            fig_r.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), margin=dict(t=30, b=30))
            cr1, cr2 = st.columns([1, 1])
            with cr1: st.plotly_chart(fig_r, use_container_width=True)
            with cr2:
                st.markdown("### 判定レポート")
                if (nj_cov+nj_s+nj_ps) > (ki_cov+ki_s+ki_ps): st.success("総合判定：【 NJSS 】が優勢です。")
                else: st.success("総合判定：【 入札王 】が優勢です。")

elif page == "過去案件情報入力":
    st.markdown('<div class="slds-page-header"><h1>過去案件情報入力</h1></div>', unsafe_allow_html=True)
    df_cur = load_data()
    valid_df = df_cur[df_cur["自治体名"].notna() & (df_cur["自治体名"] != "")].copy()
    with st.form("entry_form", clear_on_submit=True):
        st.markdown("#### 基本情報")
        c1, c2 = st.columns(2)
        mun = c1.text_input("自治体名 (必須)", placeholder="例：東京都")
        smm = c2.text_area("案件概要")
        st.markdown("---")
        st.markdown("#### 落札・応札情報")
        c3, c4 = st.columns(2)
        wnr = c3.text_input("落札企業")
        wbid = c3.number_input("落札金額 (単位: 千円)", min_value=0)
        b1 = c4.text_input("応札1"); b2 = c4.text_input("応札2"); b3 = c4.text_input("応札3")
        st.markdown("---")
        st.markdown("#### ツール掲載確認")
        c5, c6, c7 = st.columns(3)
        spc = c5.checkbox("仕様書あり")
        njl = c6.checkbox("NJSS掲載")
        kil = c7.checkbox("入札王掲載")
        if st.form_submit_button("この案件を保存する", use_container_width=True):
            if mun:
                new_rec = pd.DataFrame([{"ID": len(valid_df)+1, "自治体名": mun, "案件概要": smm, "仕様書": spc, "予算(千円)": 0, "落札金額(千円)": wbid, "落札企業": wnr, "応札1": b1, "応札2": b2, "応札3": b3, "NJSS掲載": njl, "入札王掲載": kil}])
                try:
                    conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=pd.concat([valid_df, new_rec], ignore_index=True).fillna(""))
                    st.success("スプレッドシートへの保存に成功しました。"); st.rerun()
                except: st.error("保存に失敗しました。")
            else: st.error("自治体名は必須です。")
    if not valid_df.empty: st.dataframe(valid_df, hide_index=True, use_container_width=True)

elif page == "ワード検索数":
    st.markdown('<div class="slds-page-header"><h1>ワード検索数</h1></div>', unsafe_allow_html=True)
    c_add1, c_add2 = st.columns([3, 1])
    new_w = c_add1.text_input("追加したい検索ワード", placeholder="例：BIツール", key="in_new_w_page", label_visibility="collapsed")
    if c_add2.button("ワードを追加", use_container_width=True):
        if new_w and new_w not in st.session_state.search_words:
            st.session_state.search_words.append(new_w); st.rerun()
    if st.button("リストをリセット"): st.session_state.search_words = []; st.session_state.search_counts = {}; st.rerun()
    if st.session_state.search_words:
        s_data = []
        for w in st.session_state.search_words:
            if w not in st.session_state.search_counts: st.session_state.search_counts[w] = {"NJSS": 0, "入札王": 0}
            cw1, cw2 = st.columns(2)
            st.session_state.search_counts[w]["NJSS"] = cw1.number_input(f"NJSS: {w}", min_value=0, value=st.session_state.search_counts[w]["NJSS"], key=f"nj_w_{w}")
            st.session_state.search_counts[w]["入札王"] = cw2.number_input(f"入札王: {w}", min_value=0, value=st.session_state.search_counts[w]["入札王"], key=f"ki_w_{w}")
            s_data.append({"ワード": w, "NJSS": st.session_state.search_counts[w]["NJSS"], "入札王": st.session_state.search_counts[w]["入札王"]})
        st.plotly_chart(px.bar(pd.DataFrame(s_data), x="ワード", y=["NJSS", "入札王"], barmode="group", color_discrete_map={"NJSS": "#0284C7", "入札王": "#F59E0B"}), use_container_width=True)

elif page == "コスト・ROI分析":
    st.markdown('<div class="slds-page-header"><h1>コスト・ROI分析</h1></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**NJSS設定**")
        n_i = st.number_input("初期費用 (円)", value=st.session_state.costs["n_init"], step=10000, key="n_init_val")
        n_m = st.number_input("月額費用 (円)", value=st.session_state.costs["n_month"], step=10000, key="n_month_val")
        n_o = st.number_input("年間オプション (円)", value=st.session_state.costs["n_opt"], step=10000, key="n_opt_val")
    with c2:
        st.markdown("**入札王設定**")
        k_i = st.number_input("初期費用 (円)", value=st.session_state.costs["k_init"], step=10000, key="k_init_val")
        k_m = st.number_input("月額費用 (円)", value=st.session_state.costs["k_month"], step=10000, key="k_month_val")
        k_o = st.number_input("年間オプション (円)", value=st.session_state.costs["k_opt"], step=10000, key="k_opt_val")
    st.markdown("---")
    cs1, cs2, cs3 = st.columns(3)
    wr = cs1.number_input("受注率 (%)", value=st.session_state.costs["win_rate"], min_value=1, max_value=100, key="win_rate_val")
    mg = cs2.number_input("粗利率 (%)", value=st.session_state.costs["margin"], min_value=1, max_value=100, key="margin_val")
    ab = cs3.number_input("年間応札数 (件)", value=st.session_state.costs["annual_bids"], min_value=1, key="annual_bids_val")
    if st.button("設定を保存", use_container_width=True):
        st.session_state.costs.update({"n_init": n_i, "n_month": n_m, "n_opt": n_o, "k_init": k_i, "k_month": k_m, "k_opt": k_o, "margin": mg, "win_rate": wr, "annual_bids": ab})
        st.success("シミュレーション設定を更新しました。"); st.rerun()
    p_df, _ = calculate_projections()
    fig_b = go.Figure()
    fig_b.add_trace(go.Scatter(x=p_df["年"], y=p_df["累積売上"], name="累積売上期待値", line=dict(color="#10B981", width=4)))
    fig_b.add_trace(go.Scatter(x=p_df["年"], y=p_df["NJSS累積コスト"], name="NJSS累積コスト", line=dict(color="#0284C7", dash='dash')))
    fig_b.add_trace(go.Scatter(x=p_df["年"], y=p_df["入札王累積コスト"], name="入札王累積コスト", line=dict(color="#F59E0B", dash='dash')))
    st.plotly_chart(fig_b, use_container_width=True)

elif page == "マニュアル":
    st.markdown('<div class="slds-page-header"><h1>マニュアル</h1></div>', unsafe_allow_html=True)
    st.markdown("""
    ### 1. 本ツールの目的
    本ツールは、入札情報サービス（NJSS、入札王など）の導入検討に向けたPoCにおいて、各ツールの「網羅率」「検索精度」「収益性」を定量的に比較評価するための専用システムです。
    ### 2. 操作方法
    * **ダッシュボード**: 全データの集計結果と、5年間の利益シミュレーション、総合判定レポートを表示します。
    * **過去案件情報入力**: 実際の過去の入札結果を1件ずつ登録し、蓄積します。
    * **ワード検索数**: 特定のキーワードでのヒット件数を比較記録します。
    * **コスト・ROI分析**: 各ツールの見積額と、自社の受注率・利益率を入力して損益分岐点を分析します。
    """)

elif page == "データ管理 (テスト)":
    st.markdown('<div class="slds-page-header"><h1>データ管理</h1></div>', unsafe_allow_html=True)
    sm_df = pd.DataFrame([{"ID": 1, "自治体名": "東京都", "案件概要": "サンプル", "仕様書": True, "落札金額(千円)": 50000, "NJSS掲載": True, "入札王掲載": False}])
    st.download_button(label="サンプルCSVをダウンロード", data=sm_df.to_csv(index=False).encode('utf-8-sig'), file_name="sample_poc.csv", mime="text/csv")
    up_f = st.file_uploader("CSVインポート", type="csv")
    if up_f:
        try:
            im_df = pd.read_csv(up_f, encoding="utf-8-sig")
            if st.button("反映"): st.session_state.temp_df = im_df; st.success("セッションに反映しました。入力ページから保存してください。")
        except: st.error("読込に失敗しました。")
    st.markdown("---")
    if st.button("スプレッドシートを初期化", use_container_width=True):
        try:
            conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=pd.DataFrame(columns=CORRECT_COLUMNS))
            st.success("初期化に成功しました。"); st.rerun()
        except: st.error("初期化に失敗しました。")
