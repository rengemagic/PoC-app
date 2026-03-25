import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection
import io
import csv
import traceback

# --- 1. UI & CSS (アイコン完全排除・白枠消去・カードデザイン・ボタン青白統一) ---
st.set_page_config(page_title="入札ツール精密評価ボード", layout="wide")

st.markdown("""
    <style>
    /* ヘッダーと上部白枠の完全排除 */
    [data-testid="stHeader"] { display: none !important; }
    [data-testid="stAppViewContainer"] { padding-top: 0rem !important; background-color: #F3F4F6 !important; }
    [data-testid="block-container"] { padding-top: 2rem !important; padding-bottom: 2rem !important; }

    /* 全体の文字色 */
    .stApp { color: #181818 !important; }
    
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

    /* ページヘッダー装飾 (Salesforce Lightning風) */
    .slds-page-header { 
        background-color: #FFFFFF !important; 
        padding: 1.5rem 2rem; 
        border-bottom: 1px solid #E2E8F0; 
        margin: -2rem -4rem 2.5rem -4rem; 
        border-left: 8px solid #0176D3; 
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .slds-page-header h1 { color: #0F172A !important; font-size: 1.5rem; font-weight: 700; margin: 0; }
    
    /* カードデザイン */
    .slds-card { 
        background-color: #FFFFFF !important; 
        border: 1px solid #E2E8F0 !important; 
        border-radius: 8px; 
        padding: 1.5rem; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.02); 
        margin-bottom: 1.5rem; 
    }
    
    /* ボタンデザイン (すべて青背景・白文字に統一) */
    .stButton > button { 
        background-color: #0176D3 !important; 
        color: #FFFFFF !important; 
        border-radius: 6px !important; 
        font-weight: 600 !important; 
        border: none !important; 
        padding: 0.5rem 1.5rem !important; 
        transition: all 0.2s ease;
        width: 100%;
    }
    .stButton > button:hover { background-color: #014486 !important; transform: translateY(-1px); box-shadow: 0 4px 6px rgba(1, 118, 211, 0.2); }
    
    /* 入力フォームのデザイン */
    div[data-baseweb="input"], input, textarea { background-color: #F8FAFC !important; color: #0F172A !important; border-radius: 6px !important; border-color: #CBD5E1 !important; }
    div[data-baseweb="input"]:focus-within { border-color: #0176D3 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- セッション状態の初期化 ---
if 'search_words' not in st.session_state: st.session_state.search_words = ["DX推進", "データ分析基盤"]
if 'search_counts' not in st.session_state: st.session_state.search_counts = {}
if 'temp_df' not in st.session_state: st.session_state.temp_df = None
if 'costs' not in st.session_state: 
    st.session_state.costs = {
        "n_init": 0, "n_month": 0, "n_opt": 0,
        "k_init": 0, "k_month": 0, "k_opt": 0,
        "margin": 20, "win_rate": 20, "annual_bids": 50
    }

# --- 2. データ接続と計算ロジック ---
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
    st.markdown('<p class="sidebar-section-header">Menu</p>', unsafe_allow_html=True)
    test_mode = st.toggle("データ管理モード")
    menu_options = ["ダッシュボード", "過去案件情報入力", "ワード検索数", "コスト・ROI分析", "詳細マニュアル"]
    if test_mode: menu_options.append("データ管理 (一括処理)")
    page = st.radio("メニュー選択", menu_options, label_visibility="collapsed")

# --- 4. コンテンツ表示 ---

if page == "ダッシュボード":
    st.markdown('<div class="slds-page-header"><h1>PoC分析ダッシュボード</h1></div>', unsafe_allow_html=True)
    df = load_data()
    valid_df = df[df["自治体名"].notna() & (df["自治体名"] != "")]
    
    if valid_df.empty:
        st.info("データがありません。「過去案件情報入力」からデータを登録してください。")
    else:
        # KPIカードセクション
        st.markdown('<div class="slds-card">', unsafe_allow_html=True)
        st.markdown("### 全体カバレッジ（網羅率）")
        k1, k2, k3 = st.columns(3)
        nj_c = valid_df["NJSS掲載"].astype(str).str.upper().isin(["TRUE", "1", "1.0", "YES"]).sum()
        ki_c = valid_df["入札王掲載"].astype(str).str.upper().isin(["TRUE", "1", "1.0", "YES"]).sum()
        with k1: st.metric("NJSS 網羅率", f"{(nj_c/len(valid_df)*100):.1f}%")
        with k2: st.metric("入札王 網羅率", f"{(ki_c/len(valid_df)*100):.1f}%")
        with k3: st.metric("分析対象案件数", f"{len(valid_df)} 件")
        st.markdown('</div>', unsafe_allow_html=True)

        # グラフセクション上段
        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown('<div class="slds-card">', unsafe_allow_html=True)
            fig_hits = px.bar(x=["NJSS", "入札王"], y=[nj_c, ki_c], title="案件捕捉数の比較", color=["NJSS", "入札王"], color_discrete_map={"NJSS": "#0176D3", "入札王": "#1B96FF"})
            fig_hits.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_hits, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with col_r:
            st.markdown('<div class="slds-card">', unsafe_allow_html=True)
            comp_df = pd.concat([valid_df["落札企業"], valid_df["応札1"], valid_df["応札2"], valid_df["応札3"]])
            pres_df = comp_df[comp_df != ""].value_counts().reset_index().head(6)
            pres_df.columns = ["企業名", "出現回数"]
            fig_p = px.bar(pres_df, x="出現回数", y="企業名", orientation='h', title="競合出現シェア")
            fig_p.update_traces(marker_color='#0176D3')
            fig_p.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_p, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # グラフセクション中段 (ワード検索数)
        st.markdown('<div class="slds-card">', unsafe_allow_html=True)
        st.markdown("### キーワード検索精度比較")
        if st.session_state.search_words and st.session_state.search_counts:
            s_data = []
            for w in st.session_state.search_words:
                n_val = st.session_state.search_counts.get(w, {}).get("NJSS", 0)
                k_val = st.session_state.search_counts.get(w, {}).get("入札王", 0)
                s_data.append({"ワード": w, "NJSS": n_val, "入札王": k_val})
            df_sw = pd.DataFrame(s_data)
            fig_sw = px.bar(df_sw, x="ワード", y=["NJSS", "入札王"], barmode="group", color_discrete_map={"NJSS": "#0176D3", "入札王": "#1B96FF"})
            fig_sw.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig_sw, use_container_width=True)
        else:
            st.write("検索ワードのデータがありません。「ワード検索数」画面からデータを追加してください。")
        st.markdown('</div>', unsafe_allow_html=True)

        # グラフセクション下段 (5年ROI)
        st.markdown('<div class="slds-card">', unsafe_allow_html=True)
        p_df, _ = calculate_projections()
        fig_proj = px.line(p_df, x="年", y=["NJSS利益", "入札王利益"], title="累積期待利益の予測推移（5カ年）", color_discrete_map={"NJSS利益": "#0176D3", "入札王利益": "#1B96FF"})
        fig_proj.update_layout(template="plotly_white")
        st.plotly_chart(fig_proj, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # 総合判定セクション
        st.markdown('<div class="slds-card">', unsafe_allow_html=True)
        st.markdown("### 総合判定・分析レポート")
        if st.button("総合判定を実行する"):
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
            fig_r.add_trace(go.Scatterpolar(r=[nj_cov, nj_s, nj_ps, nj_cov], theta=cat, fill='toself', name='NJSS', line_color='#0176D3'))
            fig_r.add_trace(go.Scatterpolar(r=[ki_cov, ki_s, ki_ps, ki_cov], theta=cat, fill='toself', name='入札王', line_color='#1B96FF'))
            fig_r.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), margin=dict(t=30, b=30))
            
            cr1, cr2 = st.columns([1, 1])
            with cr1: st.plotly_chart(fig_r, use_container_width=True)
            with cr2:
                st.markdown("#### 判定結果")
                if (nj_cov+nj_s+nj_ps) > (ki_cov+ki_s+ki_ps):
                    st.success("分析の結果、【 NJSS 】の導入を推奨します。網羅率と精度のバランスに優れています。")
                else:
                    st.success("分析の結果、【 入札王 】の導入を推奨します。コストパフォーマンスに優れ、高いROIが期待できます。")
        st.markdown('</div>', unsafe_allow_html=True)

elif page == "過去案件情報入力":
    st.markdown('<div class="slds-page-header"><h1>過去案件情報入力</h1></div>', unsafe_allow_html=True)
    df_cur = load_data()
    valid_df = df_cur[df_cur["自治体名"].notna() & (df_cur["自治体名"] != "")].copy()
    
    st.markdown('<div class="slds-card">', unsafe_allow_html=True)
    with st.form("entry_form", clear_on_submit=True):
        st.markdown("#### 基本情報")
        c1, c2 = st.columns(2)
        mun = c1.text_input("自治体名 (必須)", placeholder="例: 東京都、横浜市", help="発注元の自治体名を入力してください。")
        smm = c2.text_area("案件概要", placeholder="例: 令和6年度 データ分析基盤構築業務", help="どのような案件だったか、後で見て分かる概要を記載します。")
        
        st.markdown("#### 落札・応札情報")
        c3, c4 = st.columns(2)
        wnr = c3.text_input("落札企業", placeholder="例: 株式会社ジール", help="最終的に落札した企業名を入力します。自社の場合は自社名を入力。")
        wbid = c3.number_input("落札金額 (単位: 千円)", min_value=0, help="実際の落札金額を入力します。この平均値がROI計算のベースになります。")
        b1 = c4.text_input("競合企業1", placeholder="例: A社", help="入札に参加していた競合他社を入力します。")
        b2 = c4.text_input("競合企業2", placeholder="例: B社")
        
        st.markdown("#### ツール掲載確認 (実測結果)")
        st.write("※ 各ツールの無料トライアル等で、この案件が実際に検索ヒットするか確認し、チェックを入れます。")
        c5, c6, c7 = st.columns(3)
        spc = c5.checkbox("仕様書あり")
        njl = c6.checkbox("NJSSに掲載あり")
        kil = c7.checkbox("入札王に掲載あり")
        
        if st.form_submit_button("この案件を保存する"):
            if mun:
                new_rec = pd.DataFrame([{"ID": len(valid_df)+1, "自治体名": mun, "案件概要": smm, "仕様書": spc, "予算(千円)": 0, "落札金額(千円)": wbid, "落札企業": wnr, "応札1": b1, "応札2": b2, "応札3": "", "NJSS掲載": njl, "入札王掲載": kil}])
                try:
                    conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=pd.concat([valid_df, new_rec], ignore_index=True).fillna(""))
                    st.success("保存に成功しました。")
                except: 
                    st.error("保存に失敗しました。")
            else: 
                st.error("自治体名は必須項目です。")
    st.markdown('</div>', unsafe_allow_html=True)

    if not valid_df.empty:
        st.markdown('<div class="slds-card">', unsafe_allow_html=True)
        st.markdown("### 登録済みデータ一覧")
        st.dataframe(valid_df, hide_index=True, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

elif page == "ワード検索数":
    st.markdown('<div class="slds-page-header"><h1>ワード検索数比較</h1></div>', unsafe_allow_html=True)
    
    st.markdown('<div class="slds-card">', unsafe_allow_html=True)
    st.markdown("#### 比較キーワードの追加")
    c_add1, c_add2, c_add3 = st.columns([2, 1, 1])
    new_w = c_add1.text_input("キーワード", placeholder="例: BIツール、DX推進", key="in_new_w", label_visibility="collapsed")
    if c_add2.button("追加"):
        if new_w and new_w not in st.session_state.search_words:
            st.session_state.search_words.append(new_w); st.rerun()
    if c_add3.button("クリア"): 
        st.session_state.search_words = []; st.session_state.search_counts = {}; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.search_words:
        st.markdown('<div class="slds-card">', unsafe_allow_html=True)
        st.markdown("#### ヒット件数の実測値入力")
        s_data = []
        for w in st.session_state.search_words:
            if w not in st.session_state.search_counts: st.session_state.search_counts[w] = {"NJSS": 0, "入札王": 0}
            cw1, cw2 = st.columns(2)
            st.session_state.search_counts[w]["NJSS"] = cw1.number_input(f"NJSS: {w}", min_value=0, value=st.session_state.search_counts[w]["NJSS"], key=f"nj_{w}")
            st.session_state.search_counts[w]["入札王"] = cw2.number_input(f"入札王: {w}", min_value=0, value=st.session_state.search_counts[w]["入札王"], key=f"ki_{w}")
            s_data.append({"ワード": w, "NJSS": st.session_state.search_counts[w]["NJSS"], "入札王": st.session_state.search_counts[w]["入札王"]})
        st.markdown('</div>', unsafe_allow_html=True)

elif page == "コスト・ROI分析":
    st.markdown('<div class="slds-page-header"><h1>コスト・ROI分析設定</h1></div>', unsafe_allow_html=True)
    
    st.markdown('<div class="slds-card">', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**NJSS 費用見積**")
        n_i = st.number_input("初期費用 (円)", value=st.session_state.costs["n_init"], key="n_i_v")
        n_m = st.number_input("月額費用 (円)", value=st.session_state.costs["n_month"], key="n_m_v")
        n_o = st.number_input("年間オプション (円)", value=st.session_state.costs["n_opt"], key="n_o_v")
    with c2:
        st.markdown("**入札王 費用見積**")
        k_i = st.number_input("初期費用 (円)", value=st.session_state.costs["k_init"], key="k_i_v")
        k_m = st.number_input("月額費用 (円)", value=st.session_state.costs["k_month"], key="k_m_v")
        k_o = st.number_input("年間オプション (円)", value=st.session_state.costs["k_opt"], key="k_o_v")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="slds-card">', unsafe_allow_html=True)
    st.markdown("**自社営業シミュレーション設定**")
    cs1, cs2, cs3 = st.columns(3)
    wr = cs1.number_input("平均受注率 (%)", value=st.session_state.costs["win_rate"], help="応札に参加した場合、落札できる確率。")
    mg = cs2.number_input("平均粗利率 (%)", value=st.session_state.costs["margin"], help="落札金額に対する、自社の粗利の割合。")
    ab = cs3.number_input("年間想定応札数 (件)", value=st.session_state.costs["annual_bids"], help="1年間に何件の入札に参加するか。")
    
    if st.button("設定を保存して反映"):
        st.session_state.costs.update({"n_init": n_i, "n_month": n_m, "n_opt": n_o, "k_init": k_i, "k_month": k_m, "k_opt": k_o, "margin": mg, "win_rate": wr, "annual_bids": ab})
        st.success("保存に成功しました。")
    st.markdown('</div>', unsafe_allow_html=True)

elif page == "詳細マニュアル":
    st.markdown('<div class="slds-page-header"><h1>自走式 PoC評価マニュアル</h1></div>', unsafe_allow_html=True)
    st.markdown('<div class="slds-card">', unsafe_allow_html=True)
    st.markdown("""
    本システムは、入札情報サービス（NJSS、入札王等）の導入前検証（PoC）において、データに基づいた合理的な決裁を行うための分析ツールです。担当者が単独で検証を進められるよう設計されています。

    ### 1. 検証の全体フロー
    1. **過去データの準備 (データ管理 or 過去案件入力)**
       * 過去1〜2年で自社が関連する、または落札したかった案件を10〜20件リストアップします。
    2. **ツールでの検索実測 (各ツールのトライアル画面)**
       * NJSSおよび入札王のトライアルアカウントを使用し、1でリストアップした案件が「実際に検索して見つかるか」を確認します。
    3. **実測結果の登録 (過去案件情報入力・ワード検索数)**
       * 本システムの入力フォームに、確認した結果（掲載あり/なし等）を記録します。
    4. **コストシミュレーションの設定 (コスト・ROI分析)**
       * 営業担当から提示された見積もり金額と、自社の受注率・利益率を設定します。
    5. **最終判断 (ダッシュボード)**
       * 全データが統合され、レーダーチャートと推奨テキストが出力されます。この画面をキャプチャし、稟議書に添付してください。

    ### 2. 重要指標（KPI）の読み方
    * **網羅率 (Coverage Rate)**: 最も重要な指標です。過去の有望案件が掲載されていなければ、導入しても見逃すことになります。
    * **累積利益予測 (5年ROI)**: 単なる利用料の安さではなく、「落札額 × 粗利率 × 受注率」から導かれる期待利益とコストを差し引き、中長期でどちらが黒字になるかを示します。
    """)
    st.markdown('</div>', unsafe_allow_html=True)

elif page == "データ管理 (一括処理)":
    st.markdown('<div class="slds-page-header"><h1>データ一括管理</h1></div>', unsafe_allow_html=True)
    
    st.markdown('<div class="slds-card">', unsafe_allow_html=True)
    st.markdown("### サンプルCSVダウンロード")
    st.write("Excel等で案件データを一括作成するためのフォーマットです。")
    sample_data = [{"ID": 1, "自治体名": "東京都", "案件概要": "案件サンプル", "仕様書": True, "落札金額(千円)": 10000, "NJSS掲載": True, "入札王掲載": False}]
    st.download_button("フォーマットをダウンロード", data=pd.DataFrame(sample_data).to_csv(index=False).encode('utf-8-sig'), file_name="import_format.csv", mime="text/csv")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="slds-card">', unsafe_allow_html=True)
    st.markdown("### CSVインポート")
    up_f = st.file_uploader("作成したCSVをアップロード", type="csv")
    if up_f:
        im_df = pd.read_csv(up_f, encoding="utf-8-sig")
        st.write("プレビュー:")
        st.dataframe(im_df.head())
        if st.button("このデータをスプレッドシートへ書き込む"):
            try:
                final_df = pd.concat([load_data(), im_df], ignore_index=True).fillna("")
                conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=final_df)
                st.success("保存に成功しました。")
            except: 
                st.error("保存に失敗しました。")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="slds-card">', unsafe_allow_html=True)
    st.markdown("### データの初期化")
    st.write("※ スプレッドシートの全データを消去し、初期状態に戻します。")
    if st.button("全データを初期化する"):
        try:
            conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=pd.DataFrame(columns=CORRECT_COLUMNS))
            st.success("初期化に成功しました。")
        except: 
            st.error("初期化に失敗しました。")
    st.markdown('</div>', unsafe_allow_html=True)
