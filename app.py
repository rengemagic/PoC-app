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
    .slds-page-header { background-color: #F8FAFC !important; padding: 1.2rem 2rem; border-bottom: 1px solid #E2E8F0; margin: -2rem -4rem 2.5rem -4rem; border-left: 8px solid #0284C7; }
    .slds-page-header h1 { color: #0F172A !important; font-size: 1.5rem; font-weight: 700; margin: 0; }
    .stButton > button { background-color: #0284C7 !important; color: #FFFFFF !important; border-radius: 6px !important; font-weight: 600 !important; border: none !important; padding: 0.5rem 1.5rem !important; }
    .stButton > button:hover { background-color: #0369A1 !important; transform: translateY(-1px); }
    </style>
    """, unsafe_allow_html=True)

# --- セッション状態の初期化 ---
if 'search_words' not in st.session_state: st.session_state.search_words = ["DX推進", "データ分析基盤"]
if 'search_counts' not in st.session_state: st.session_state.search_counts = {}
if 'costs' not in st.session_state: 
    st.session_state.costs = {"n_init": 0, "n_month": 0, "n_opt": 0, "k_init": 0, "k_month": 0, "k_opt": 0, "margin": 20, "win_rate": 20, "annual_bids": 50}

# --- 2. データ接続 ---
conn = st.connection("gsheets", type=GSheetsConnection)
CORRECT_COLUMNS = ["ID", "自治体名", "案件概要", "仕様書", "予算(千円)", "落札金額(千円)", "落札企業", "応札1", "応札2", "応札3", "NJSS掲載", "入札王掲載", "URL1", "URL2", "URL3", "URL4", "URL5"]

def load_data():
    try:
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        df = conn.read(spreadsheet=url, ttl="0s")
        if "自治体名" not in df.columns: return pd.DataFrame(columns=CORRECT_COLUMNS)
        return df
    except: return pd.DataFrame(columns=CORRECT_COLUMNS)

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

# --- 3. サイドバー ---
with st.sidebar:
    st.markdown('<p class="sidebar-section-header">PoC Evaluation Menu</p>', unsafe_allow_html=True)
    test_mode = st.toggle("データ管理モード (一括・初期化)")
    menu_options = ["ダッシュボード", "過去案件情報入力", "ワード検索数", "コスト・ROI分析", "詳細マニュアルガイド"]
    if test_mode: menu_options.append("データ管理 (一括処理)")
    page = st.radio("メニュー", menu_options, label_visibility="collapsed")

# --- 4. コンテンツ表示 ---

if page == "ダッシュボード":
    st.markdown('<div class="slds-page-header"><h1>PoC分析ダッシュボード</h1></div>', unsafe_allow_html=True)
    df = load_data()
    valid_df = df[df["自治体名"].notna() & (df["自治体名"] != "")]
    if valid_df.empty:
        st.warning("データがありません。「過去案件情報入力」または「データ管理」からデータを登録してください。")
    else:
        st.info("💡 蓄積されたデータに基づき、ツールの『網羅率』と『投資回収予測』を可視化しています。")
        k1, k2, k3 = st.columns(3)
        nj_c = valid_df["NJSS掲載"].astype(str).str.upper().isin(["TRUE", "1", "1.0", "YES"]).sum()
        ki_c = valid_df["入札王掲載"].astype(str).str.upper().isin(["TRUE", "1", "1.0", "YES"]).sum()
        with k1: st.metric("NJSS 網羅率", f"{(nj_c/len(valid_df)*100):.1f}%", help="全案件のうちNJSSに掲載されていた割合")
        with k2: st.metric("入札王 網羅率", f"{(ki_c/len(valid_df)*100):.1f}%", help="全案件のうち入札王に掲載されていた割合")
        with k3: st.metric("分析対象案件数", f"{len(valid_df)} 件")
        p_df, _ = calculate_projections()
        st.plotly_chart(px.line(p_df, x="年", y=["NJSS利益", "入札王利益"], title="累積利益予測推移", color_discrete_map={"NJSS利益": "#0284C7", "入札王利益": "#F59E0B"}), use_container_width=True)

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
            n_p5, k_p5 = p_df.iloc[-1]["NJSS利益"], p_df.iloc[-1]["入札王利益"]
            mx = max(n_p5, k_p5, 1)
            nj_ps, ki_ps = max(0, (n_p5 / mx * 100)), max(0, (k_p5 / mx * 100))
            fig_r = go.Figure()
            cat = ['網羅率', '検索精度', '収益性', '網羅率']
            fig_r.add_trace(go.Scatterpolar(r=[nj_cov, nj_s, nj_ps, nj_cov], theta=cat, fill='toself', name='NJSS', line_color='#0284C7'))
            fig_r.add_trace(go.Scatterpolar(r=[ki_cov, ki_s, ki_ps, ki_cov], theta=cat, fill='toself', name='入札王', line_color='#F59E0B'))
            cr1, cr2 = st.columns([1, 1])
            with cr1: st.plotly_chart(fig_r, use_container_width=True)
            with cr2:
                st.markdown("### 🏆 推奨ツールの判定")
                if (nj_cov+nj_s+nj_ps) > (ki_cov+ki_s+ki_ps): st.success("総合評価に基づき、【 NJSS 】を推奨します。")
                else: st.success("総合評価に基づき、【 入札王 】を推奨します。")

elif page == "過去案件情報入力":
    st.markdown('<div class="slds-page-header"><h1>過去案件情報入力</h1></div>', unsafe_allow_html=True)
    st.write("💡 使い方: 過去1年程度の自社関連案件を入力してください。網羅率とROIの計算根拠となります。")
    df_cur = load_data()
    valid_df = df_cur[df_cur["自治体名"].notna() & (df_cur["自治体名"] != "")].copy()
    with st.form("entry_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        mun = c1.text_input("自治体名 (必須)")
        smm = c2.text_area("案件概要")
        st.markdown("---")
        c3, c4 = st.columns(2)
        wnr = c3.text_input("落札企業")
        wbid = c3.number_input("落札金額 (単位: 千円)")
        b1 = c4.text_input("応札1"); b2 = c4.text_input("応札2"); b3 = c4.text_input("応札3")
        st.markdown("---")
        c5, c6, c7 = st.columns(3)
        spc = c5.checkbox("仕様書あり")
        njl = c6.checkbox("NJSSに掲載あり")
        kil = c7.checkbox("入札王に掲載あり")
        if st.form_submit_button("この案件を保存する", use_container_width=True):
            if mun:
                new = pd.DataFrame([{"ID": len(valid_df)+1, "自治体名": mun, "案件概要": smm, "仕様書": spc, "予算(千円)": 0, "落札金額(千円)": wbid, "落札企業": wnr, "応札1": b1, "応札2": b2, "応札3": b3, "NJSS掲載": njl, "入札王掲載": kil}])
                conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=pd.concat([valid_df, new], ignore_index=True).fillna(""))
                st.success("スプレッドシートへの保存に成功しました！"); st.rerun()
            else: st.error("自治体名は必須です。")
    if not valid_df.empty: st.dataframe(valid_df, hide_index=True, use_container_width=True)

elif page == "ワード検索数":
    st.markdown('<div class="slds-page-header"><h1>ワード検索数比較</h1></div>', unsafe_allow_html=True)
    st.write("💡 使い方: 自社の得意分野のキーワードで検索し、各ツールで何件ヒットするかを入力してください。")
    c_add1, c_add2 = st.columns([3, 1])
    new_w = c_add1.text_input("キーワード追加", key="in_new_w")
    if c_add2.button("追加"):
        if new_w: st.session_state.search_words.append(new_w); st.rerun()
    if st.session_state.search_words:
        s_data = []
        for w in st.session_state.search_words:
            if w not in st.session_state.search_counts: st.session_state.search_counts[w] = {"NJSS": 0, "入札王": 0}
            cw1, cw2 = st.columns(2)
            st.session_state.search_counts[w]["NJSS"] = cw1.number_input(f"NJSS: {w}", value=st.session_state.search_counts[w]["NJSS"], key=f"nj_{w}")
            st.session_state.search_counts[w]["入札王"] = cw2.number_input(f"入札王: {w}", value=st.session_state.search_counts[w]["入札王"], key=f"ki_{w}")
            s_data.append({"ワード": w, "NJSS": st.session_state.search_counts[w]["NJSS"], "入札王": st.session_state.search_counts[w]["入札王"]})
        st.plotly_chart(px.bar(pd.DataFrame(s_data), x="ワード", y=["NJSS", "入札王"], barmode="group", color_discrete_map={"NJSS": "#0284C7", "入札王": "#F59E0B"}), use_container_width=True)

elif page == "コスト・ROI分析":
    st.markdown('<div class="slds-page-header"><h1>コスト・ROI分析設定</h1></div>', unsafe_allow_html=True)
    st.write("💡 使い方: 見積額と自社の受注実態を入力して、採算が合うラインを確認してください。")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**NJSS 費用**")
        n_i = st.number_input("初期費用 (円)", value=st.session_state.costs["n_init"], key="n_i_v")
        n_m = st.number_input("月額費用 (円)", value=st.session_state.costs["n_month"], key="n_m_v")
        n_o = st.number_input("年間オプション (円)", value=st.session_state.costs["n_opt"], key="n_o_v")
    with c2:
        st.markdown("**入札王 費用**")
        k_i = st.number_input("初期費用 (円)", value=st.session_state.costs["k_init"], key="k_i_v")
        k_m = st.number_input("月額費用 (円)", value=st.session_state.costs["k_month"], key="k_m_v")
        k_o = st.number_input("年間オプション (円)", value=st.session_state.costs["k_opt"], key="k_o_v")
    cs1, cs2, cs3 = st.columns(3)
    wr = cs1.number_input("平均受注率 (%)", value=st.session_state.costs["win_rate"])
    mg = cs2.number_input("平均粗利率 (%)", value=st.session_state.costs["margin"])
    ab = cs3.number_input("想定年間応札数 (件)", value=st.session_state.costs["annual_bids"])
    if st.button("設定を保存", use_container_width=True):
        st.session_state.costs.update({"n_init": n_i, "n_month": n_m, "n_opt": n_o, "k_init": k_i, "k_month": k_m, "k_opt": k_o, "margin": mg, "win_rate": wr, "annual_bids": ab})
        st.success("設定を更新しました。ダッシュボードに反映されます。")

elif page == "詳細マニュアルガイド":
    st.markdown('<div class="slds-page-header"><h1>PoC評価詳細マニュアル</h1></div>', unsafe_allow_html=True)
    st.markdown("""
    ### 1. 評価指標の定義
    * **網羅率**: 「過去に狙っていた案件を、そのツールで発見できたか」を測ります。これが低いツールは機会損失を招きます。
    * **期待ROI**: 平均落札額 × 粗利率 × 受注率 から「1応札あたりの期待利益」を出し、ツール費用を何件で回収できるか算出します。
    * **検索精度**: キーワード検索結果の数です。件数が多すぎると運用負荷が上がり、少なすぎると漏れのリスクがあります。

    ### 2. 評価の進め方
    1. **過去案件のリストアップ**: 直近1年の重要案件（落札・失注問わず）を20件程度準備します。
    2. **各ツールでの検索**: 試用アカウントでその案件がヒットするか確認します。
    3. **結果入力**: 本システムの「過去案件情報入力」に登録します。
    4. **判定実行**: ダッシュボードの「総合判定」を行い、最終推奨ツールを確認します。
    """)

elif page == "データ管理 (一括処理)":
    st.markdown('<div class="slds-page-header"><h1>データ管理 (一括処理)</h1></div>', unsafe_allow_html=True)
    st.write("💡 使い方: 大量のデータを登録する場合、サンプルCSVを加工してアップロードしてください。")
    # サンプルCSV
    s_data = [{"ID": "SETTING_COST", "自治体名": "NJSS初期費用", "案件概要": "200000"}, {"ID": 1, "自治体名": "東京都", "案件概要": "サンプル案件", "仕様書": True, "落札金額(千円)": 10000, "NJSS掲載": True, "入札王掲載": False}]
    st.download_button("サンプルCSVをダウンロード", data=pd.DataFrame(s_data).to_csv(index=False).encode('utf-8-sig'), file_name="sample.csv", mime="text/csv")
    up_f = st.file_uploader("CSVアップロード", type="csv")
    if up_f:
        im_df = pd.read_csv(up_f, encoding="utf-8-sig")
        st.dataframe(im_df.head())
        if st.button("🔥 このデータを即座にスプレッドシートへ書き込む", use_container_width=True):
            try:
                new_all = []
                for _, row in im_df.iterrows():
                    tag = str(row['ID'])
                    if tag == "SETTING_COST":
                        item, val = str(row['自治体名']), int(row['案件概要'])
                        if "NJSS初期" in item: st.session_state.costs["n_init"] = val
                        elif "NJSS月額" in item: st.session_state.costs["n_month"] = val
                    elif tag == "SETTING_WORD":
                        st.session_state.search_words.append(str(row['自治体名']))
                    else:
                        new_all.append(row)
                if new_all:
                    final_df = pd.concat([load_data(), pd.DataFrame(new_all)], ignore_index=True).fillna("")
                    conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=final_df)
                    st.success("保存に成功しました！ダッシュボードを確認してください。")
                    st.rerun()
            except: st.error("保存に失敗しました。")
