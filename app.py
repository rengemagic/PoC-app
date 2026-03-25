import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection
import io
import csv
import traceback

# --- 1. UI & CSS ---
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
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label { padding: 12px 16px !important; margin-bottom: 4px !important; border-radius: 6px !important; background-color: transparent; transition: all 0.2s; cursor: pointer; width: 100%; display: block; }
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover { background-color: rgba(255, 255, 255, 0.08) !important; color: #FFFFFF !important; }
    [data-testid="stSidebar"] div.stRadio p { color: #F8FAFC !important; font-size: 14px !important; font-weight: 500 !important; margin: 0 !important; }
    .slds-page-header { background-color: #F8FAFC !important; padding: 1.2rem 2rem; border-bottom: 1px solid #E2E8F0; margin: -2rem -4rem 2.5rem -4rem; border-left: 8px solid #0284C7; }
    .slds-page-header h1 { color: #0F172A !important; font-size: 1.5rem; font-weight: 700; margin: 0; }
    </style>
    """, unsafe_allow_html=True)

# --- セッション状態 ---
if 'search_words' not in st.session_state: st.session_state.search_words = ["DX推進", "データ分析基盤"]
if 'search_counts' not in st.session_state: st.session_state.search_counts = {}
if 'temp_df' not in st.session_state: st.session_state.temp_df = None
if 'costs' not in st.session_state: 
    st.session_state.costs = {"n_init": 0, "n_month": 0, "n_opt": 0, "k_init": 0, "k_month": 0, "k_opt": 0, "margin": 20, "win_rate": 20, "annual_bids": 50}

# --- 2. スプレッドシート接続 ---
conn = st.connection("gsheets", type=GSheetsConnection)
CORRECT_COLUMNS = ["ID", "自治体名", "案件概要", "仕様書", "予算(千円)", "落札金額(千円)", "落札企業", "応札1", "応札2", "応札3", "NJSS掲載", "入札王掲載", "URL1", "URL2", "URL3", "URL4", "URL5"]

def load_data():
    try:
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        df = conn.read(spreadsheet=url, ttl="0s")
        if "自治体名" not in df.columns: return pd.DataFrame([{col: "" if col != "ID" else i+1 for col in CORRECT_COLUMNS} for i in range(20)])
        return df
    except: return pd.DataFrame([{col: "" if col != "ID" else i+1 for col in CORRECT_COLUMNS} for i in range(20)])

# --- 3. サイドバー ---
with st.sidebar:
    st.markdown('<p class="sidebar-section-header">Menu</p>', unsafe_allow_html=True)
    test_mode = st.toggle("テストモード表示")
    menu_options = ["ダッシュボード", "過去案件情報入力", "ワード検索数", "コスト・ROI分析", "マニュアル"]
    if test_mode: menu_options.append("データ管理 (テスト)")
    page = st.radio("メニュー", menu_options, label_visibility="collapsed")

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

# --- 4. コンテンツ ---

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
        with k1: st.metric("NJSS 網羅率", f"{(nj_c/len(valid_df)*100):.1f}%")
        with k2: st.metric("入札王 網羅率", f"{(ki_c/len(valid_df)*100):.1f}%")
        with k3: st.metric("検証案件数", f"{len(valid_df)} 件")
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
            with cr2: st.markdown("### 判定レポート")
            if (nj_cov+nj_s+nj_ps) > (ki_cov+ki_s+ki_ps): st.success("【 NJSS 】が推奨されます。")
            else: st.success("【 入札王 】が推奨されます。")

elif page == "過去案件情報入力":
    st.markdown('<div class="slds-page-header"><h1>過去案件情報入力</h1></div>', unsafe_allow_html=True)
    df_cur = load_data()
    valid_df = df_cur[df_cur["自治体名"].notna() & (df_cur["自治体名"] != "")].copy()
    
    # --- 💡 インポート反映処理 ---
    if st.session_state.temp_df is not None:
        st.info(f"📥 インポートされた {len(st.session_state.temp_df)} 件のデータがセッションにあります。")
        if st.button("☁️ クラウドへ一括保存する", use_container_width=True):
            try:
                new_all = pd.concat([valid_df, st.session_state.temp_df], ignore_index=True).fillna("")
                conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=new_all)
                st.session_state.temp_df = None
                st.success("スプレッドシートへの一括保存に成功しました！")
                st.rerun()
            except: st.error("一括保存に失敗しました。")
    
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
        if st.form_submit_button("この案件を単体保存する", use_container_width=True):
            if mun:
                new_rec = pd.DataFrame([{"ID": len(valid_df)+1, "自治体名": mun, "案件概要": smm, "仕様書": spc, "予算(千円)": 0, "落札金額(千円)": wbid, "落札企業": wnr, "応札1": b1, "応札2": b2, "応札3": b3, "NJSS掲載": njl, "入札王掲載": kil}])
                try:
                    conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=pd.concat([valid_df, new_rec], ignore_index=True).fillna(""))
                    st.success("単体保存に成功しました！"); st.rerun()
                except: st.error("保存失敗")
            else: st.error("自治体名は必須です。")
    if not valid_df.empty: st.dataframe(valid_df, hide_index=True, use_container_width=True)

elif page == "ワード検索数":
    st.markdown('<div class="slds-page-header"><h1>ワード検索数</h1></div>', unsafe_allow_html=True)
    c_add1, c_add2 = st.columns([3, 1])
    new_w = c_add1.text_input("追加したい検索ワード", placeholder="例：BIツール", key="in_new_w_pg", label_visibility="collapsed")
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
        n_i = st.number_input("初期費用 (円)", value=st.session_state.costs["n_init"], step=10000, key="n_init_v")
        n_m = st.number_input("月額費用 (円)", value=st.session_state.costs["n_month"], step=10000, key="n_month_v")
        n_o = st.number_input("年間オプション (円)", value=st.session_state.costs["n_opt"], step=10000, key="n_opt_v")
    with c2:
        st.markdown("**入札王設定**")
        k_i = st.number_input("初期費用 (円)", value=st.session_state.costs["k_init"], step=10000, key="k_init_v")
        k_m = st.number_input("月額費用 (円)", value=st.session_state.costs["k_month"], step=10000, key="k_month_v")
        k_o = st.number_input("年間オプション (円)", value=st.session_state.costs["k_opt"], step=10000, key="k_opt_v")
    cs1, cs2, cs3 = st.columns(3)
    wr = cs1.number_input("受注率 (%)", value=st.session_state.costs["win_rate"], min_value=1, max_value=100, key="win_r_v")
    mg = cs2.number_input("粗利率 (%)", value=st.session_state.costs["margin"], min_value=1, max_value=100, key="marg_v")
    ab = cs3.number_input("年間応札数 (件)", value=st.session_state.costs["annual_bids"], min_value=1, key="an_b_v")
    if st.button("設定を保存", use_container_width=True):
        st.session_state.costs.update({"n_init": n_i, "n_month": n_m, "n_opt": n_o, "k_init": k_i, "k_month": k_m, "k_opt": k_o, "margin": mg, "win_rate": wr, "annual_bids": ab})
        st.success("設定を更新しました！"); st.rerun()
    p_df, _ = calculate_projections()
    fig_b = go.Figure()
    fig_b.add_trace(go.Scatter(x=p_df["年"], y=p_df["累積売上"], name="売上期待値", line=dict(color="#10B981", width=4)))
    fig_b.add_trace(go.Scatter(x=p_df["年"], y=p_df["NJSS累積コスト"], name="NJSSコスト", line=dict(color="#0284C7", dash='dash')))
    fig_b.add_trace(go.Scatter(x=p_df["年"], y=p_df["入札王累積コスト"], name="入札王コスト", line=dict(color="#F59E0B", dash='dash')))
    st.plotly_chart(fig_b, use_container_width=True)

elif page == "マニュアル":
    st.markdown('<div class="slds-page-header"><h1>マニュアル</h1></div>', unsafe_allow_html=True)
    st.markdown("### 1. 目的\n入札サービスのPoC評価ツールです。\n### 2. データ管理\n「データ管理」からサンプルCSVをダウンロードし、必要事項を記入してインポートすると一括設定が可能です。")

elif page == "データ管理 (テスト)":
    st.markdown('<div class="slds-page-header"><h1>データ管理</h1></div>', unsafe_allow_html=True)
    
    # --- 💡 強化されたサンプルCSV生成 ---
    st.markdown("### サンプルCSVダウンロード")
    st.write("このCSVは、案件データだけでなく「コスト」や「検索ワード」の設定も一括で行える特別仕様です。")
    # 特殊な行（ヘッダー識別用）を含める
    sample_data = [
        {"ID": "SETTING_COST", "自治体名": "NJSS初期費用", "案件概要": "200000", "仕様書": "", "落札金額(千円)": "", "NJSS掲載": "", "入札王掲載": ""},
        {"ID": "SETTING_COST", "自治体名": "NJSS月額費用", "案件概要": "50000", "仕様書": "", "落札金額(千円)": "", "NJSS掲載": "", "入札王掲載": ""},
        {"ID": "SETTING_WORD", "自治体名": "DX推進", "案件概要": "検索ワード追加", "仕様書": "", "落札金額(千円)": "", "NJSS掲載": "", "入札王掲載": ""},
        {"ID": 1, "自治体名": "東京都", "案件概要": "サンプル案件A", "仕様書": True, "落札金額(千円)": 50000, "NJSS掲載": True, "入札王掲載": False}
    ]
    s_df = pd.DataFrame(sample_data)
    st.download_button(label="万能サンプルCSVをダウンロード", data=s_df.to_csv(index=False).encode('utf-8-sig'), file_name="smart_sample.csv", mime="text/csv")
    
    st.markdown("---")
    up_f = st.file_uploader("CSVインポート", type="csv")
    if up_f:
        try:
            im_df = pd.read_csv(up_f, encoding="utf-8-sig")
            # --- 💡 万能インポート処理 (行ごとに判別) ---
            new_projects = []
            for _, row in im_df.iterrows():
                tag = str(row['ID'])
                if tag == "SETTING_COST":
                    item, val = str(row['自治体名']), int(row['案件概要'])
                    if "NJSS初期" in item: st.session_state.costs["n_init"] = val
                    elif "NJSS月額" in item: st.session_state.costs["n_month"] = val
                    elif "入札王初期" in item: st.session_state.costs["k_init"] = val
                    elif "入札王月額" in item: st.session_state.costs["k_month"] = val
                elif tag == "SETTING_WORD":
                    word = str(row['自治体名'])
                    if word not in st.session_state.search_words: st.session_state.search_words.append(word)
                else:
                    new_projects.append(row)
            
            if new_projects:
                st.session_state.temp_df = pd.DataFrame(new_projects)
                st.success(f"成功！ {len(new_projects)} 件の案件を読み込み、コスト/ワード設定を更新しました。「過去案件情報入力」画面で保存を確定してください。")
            else:
                st.success("コスト・ワード設定の更新に成功しました！")
        except: st.error("読込失敗")
    
    st.markdown("---")
    if st.button("スプレッドシートを初期化", use_container_width=True):
        try:
            conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=pd.DataFrame(columns=CORRECT_COLUMNS))
            st.success("初期化成功！"); st.rerun()
        except: st.error("失敗しました。")
