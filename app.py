import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection
import io
import csv
import traceback

# --- 1. UI & CSS (入力フィールドの影・モダンデザイン) ---
st.set_page_config(page_title="入札ツール精密評価ボード", layout="wide")

st.markdown("""
    <style>
    /* ヘッダーの非表示と上部余白の調整 */
    [data-testid="stHeader"] { display: none !important; }
    [data-testid="stAppViewContainer"] { padding-top: 0rem !important; background-color: #F8FAFC !important; }
    [data-testid="block-container"] { padding-top: 2rem !important; padding-bottom: 2rem !important; }

    /* 文字色設定 */
    .stApp { color: #1E293B !important; }
    
    /* サイドバー配色 */
    [data-testid="stSidebar"] { background-color: #1E293B !important; border-right: none !important; }
    [data-testid="stSidebar"] * { color: #CBD5E1 !important; }
    .sidebar-section-header { color: #64748B !important; font-size: 11px !important; font-weight: 700; letter-spacing: 1px; padding: 10px 15px; margin: 20px 0px 5px 0px; text-transform: uppercase; }

    /* ラジオボタンをリンク風に */
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label > div:first-child { display: none !important; }
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label { padding: 12px 16px !important; margin-bottom: 4px !important; border-radius: 6px !important; background-color: transparent; transition: all 0.2s; cursor: pointer; width: 100%; display: block; }
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover { background-color: rgba(255, 255, 255, 0.08) !important; color: #FFFFFF !important; }
    [data-testid="stSidebar"] div.stRadio p { color: #F8FAFC !important; font-size: 14px !important; font-weight: 500 !important; margin: 0 !important; }

    /* ページヘッダー装飾 */
    .slds-page-header { 
        background-color: #FFFFFF !important; 
        padding: 1.5rem 2rem; 
        border-bottom: 1px solid #E2E8F0; 
        margin: -2rem -4rem 2rem -4rem; 
        border-left: 8px solid #0176D3; 
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .slds-page-header h1 { color: #0F172A !important; font-size: 1.5rem; font-weight: 700; margin: 0; }
    
    /* プライマリボタン（保存、追加、クリアなど） */
    button[kind="primary"] { 
        background-color: #0176D3 !important; 
        color: #FFFFFF !important; 
        border-radius: 6px !important; 
        font-weight: 700 !important; 
        font-size: 1.1rem !important;
        border: none !important; 
        padding: 0.75rem 1.5rem !important; 
        transition: all 0.2s ease;
    }
    button[kind="primary"]:hover { background-color: #014486 !important; transform: translateY(-2px); box-shadow: 0 4px 6px rgba(1, 118, 211, 0.3); }
    
    /* 💡 入力フィールド（インプットボックス）に美しい影とフォーカス効果を追加 */
    div[data-baseweb="input"] > div, 
    div[data-baseweb="textarea"] > div, 
    div[data-baseweb="select"] > div {
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05) !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 6px !important;
        background-color: #FFFFFF !important;
        transition: box-shadow 0.2s ease, border-color 0.2s ease !important;
    }
    div[data-baseweb="input"] > div:focus-within, 
    div[data-baseweb="textarea"] > div:focus-within, 
    div[data-baseweb="select"] > div:focus-within {
        box-shadow: 0 4px 10px rgba(1, 118, 211, 0.15) !important;
        border-color: #0176D3 !important;
    }
    
    /* セクション区切りのデザイン */
    .form-section-header {
        color: #0176D3;
        font-size: 1.1rem;
        font-weight: 700;
        border-bottom: 2px solid #E2E8F0;
        padding-bottom: 0.5rem;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- カスタムKPIカード関数 ---
def draw_kpi_card(title, value):
    st.markdown(f"""
        <div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 1.5rem; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.02); margin-bottom: 1.5rem;">
            <p style="color: #64748B; font-size: 14px; font-weight: 700; margin: 0 0 8px 0;">{title}</p>
            <p style="color: #0176D3; font-size: 38px; font-weight: 700; margin: 0; line-height: 1.2;">{value}</p>
        </div>
    """, unsafe_allow_html=True)

# --- セッション状態の初期化 ---
if 'search_words' not in st.session_state: st.session_state.search_words = []
if 'search_counts' not in st.session_state: st.session_state.search_counts = {}
if 'costs' not in st.session_state: 
    st.session_state.costs = {"n_init": 0, "n_month": 0, "n_opt": 0, "k_init": 0, "k_month": 0, "k_opt": 0, "margin": 20, "win_rate": 20, "annual_bids": 50}

# --- 💡 データ接続（詳細項目を追加） ---
conn = st.connection("gsheets", type=GSheetsConnection)
CORRECT_COLUMNS = [
    "ID", "自治体名", "担当部署名", "案件概要", "公示日", "入札日", "履行期間", 
    "入札方式", "参加資格", "予算(千円)", "落札金額(千円)", "自社結果", 
    "落札企業", "競合1", "競合2", "競合3", "仕様書", "NJSS掲載", "入札王掲載"
]

def load_data():
    try:
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        df = conn.read(spreadsheet=url, ttl="0s")
        if "担当部署名" not in df.columns: return pd.DataFrame(columns=CORRECT_COLUMNS)
        return df
    except: return pd.DataFrame(columns=CORRECT_COLUMNS)

def calculate_projections():
    df = load_data()
    valid_df = df[df["自治体名"].notna() & (df["自治体名"] != "")]
    # 落札金額の平均値（千円を円に直す）
    if not valid_df.empty and "落札金額(千円)" in valid_df.columns:
        valid_df["落札金額(千円)"] = pd.to_numeric(valid_df["落札金額(千円)"], errors="coerce").fillna(0)
        avg_bid = valid_df[valid_df["落札金額(千円)"] > 0]["落札金額(千円)"].mean() * 1000
        if pd.isna(avg_bid): avg_bid = 0
    else:
        avg_bid = 0
        
    annual_profit = avg_bid * (st.session_state.costs["margin"]/100) * (st.session_state.costs["win_rate"]/100) * st.session_state.costs["annual_bids"]
    data = []
    for year in range(6):
        n_c = st.session_state.costs["n_init"] + ((st.session_state.costs["n_month"]*12 + st.session_state.costs["n_opt"]) * year)
        k_c = st.session_state.costs["k_init"] + ((st.session_state.costs["k_month"]*12 + st.session_state.costs["k_opt"]) * year)
        rev = annual_profit * year
        data.append({"年": year, "NJSS累積コスト": n_c, "NJSS利益": rev - n_c, "入札王累積コスト": k_c, "入札王利益": rev - k_c, "累積売上": rev})
    return pd.DataFrame(data), annual_profit

# --- サイドバー ---
with st.sidebar:
    st.markdown('<p class="sidebar-section-header">Menu</p>', unsafe_allow_html=True)
    test_mode = st.toggle("データ管理モード")
    menu_options = ["ダッシュボード", "過去案件情報入力", "ワード検索数", "コスト・ROI分析", "詳細マニュアル"]
    if test_mode: menu_options.append("データ管理 (一括・初期化)")
    page = st.radio("メニュー選択", menu_options, label_visibility="collapsed")

# --- コンテンツ表示 ---

if page == "ダッシュボード":
    st.markdown('<div class="slds-page-header"><h1>PoC分析ダッシュボード</h1></div>', unsafe_allow_html=True)
    df = load_data()
    valid_df = df[df["自治体名"].notna() & (df["自治体名"] != "")]
    
    if valid_df.empty:
        st.info("データがありません。「過去案件情報入力」または「データ管理」からデータを登録してください。")
    else:
        st.markdown("### 全体カバレッジ（網羅率）")
        k1, k2, k3 = st.columns(3)
        nj_c = valid_df["NJSS掲載"].astype(str).str.upper().isin(["TRUE", "1", "1.0", "YES"]).sum()
        ki_c = valid_df["入札王掲載"].astype(str).str.upper().isin(["TRUE", "1", "1.0", "YES"]).sum()
        with k1: draw_kpi_card("NJSS 網羅率", f"{(nj_c/len(valid_df)*100):.1f}%")
        with k2: draw_kpi_card("入札王 網羅率", f"{(ki_c/len(valid_df)*100):.1f}%")
        with k3: draw_kpi_card("分析対象案件数", f"{len(valid_df)} 件")

        st.markdown("---")
        st.markdown("### 詳細分析グラフ")
        col_l, col_r = st.columns(2)
        with col_l:
            fig_hits = px.bar(x=["NJSS", "入札王"], y=[nj_c, ki_c], title="案件捕捉数の比較", color=["NJSS", "入札王"], color_discrete_map={"NJSS": "#0176D3", "入札王": "#1B96FF"})
            fig_hits.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_hits, use_container_width=True)
        with col_r:
            comp_df = pd.concat([valid_df["落札企業"], valid_df["競合1"], valid_df["競合2"], valid_df["競合3"]])
            pres_df = comp_df[comp_df != ""].value_counts().reset_index().head(6)
            pres_df.columns = ["企業名", "出現回数"]
            fig_p = px.bar(pres_df, x="出現回数", y="企業名", orientation='h', title="競合出現シェア")
            fig_p.update_traces(marker_color='#0176D3')
            fig_p.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_p, use_container_width=True)

        st.markdown("---")
        st.markdown("### キーワード検索精度比較")
        if st.session_state.search_words and st.session_state.search_counts:
            s_data = []
            for w in st.session_state.search_words:
                n_val = st.session_state.search_counts.get(w, {}).get("NJSS", 0)
                k_val = st.session_state.search_counts.get(w, {}).get("入札王", 0)
                s_data.append({"ワード": w, "NJSS": n_val, "入札王": k_val})
            df_sw = pd.DataFrame(s_data)
            if not df_sw.empty:
                fig_sw = px.bar(df_sw, x="ワード", y=["NJSS", "入札王"], barmode="group", color_discrete_map={"NJSS": "#0176D3", "入札王": "#1B96FF"})
                fig_sw.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_sw, use_container_width=True)
        else:
            st.write("検索ワードのデータがありません。「ワード検索数」画面からデータを追加してください。")

        st.markdown("---")
        st.markdown("### 累積期待利益の予測推移（5カ年）")
        p_df, _ = calculate_projections()
        fig_proj = px.line(p_df, x="年", y=["NJSS利益", "入札王利益"], color_discrete_map={"NJSS利益": "#0176D3", "入札王利益": "#1B96FF"})
        fig_proj.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_proj, use_container_width=True)

        st.markdown("---")
        st.markdown("### 総合判定・分析レポート")
        
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
        cat = ['網羅率(過去案件)', '検索精度(ワード)', '収益性(5年ROI)', '網羅率(過去案件)']
        fig_r.add_trace(go.Scatterpolar(r=[nj_cov, nj_s, nj_ps, nj_cov], theta=cat, fill='toself', name='NJSS', line_color='#0176D3'))
        fig_r.add_trace(go.Scatterpolar(r=[ki_cov, ki_s, ki_ps, ki_cov], theta=cat, fill='toself', name='入札王', line_color='#1B96FF'))
        fig_r.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), margin=dict(t=30, b=30), paper_bgcolor="rgba(0,0,0,0)")
        
        cr1, cr2 = st.columns([1, 1])
        with cr1: st.plotly_chart(fig_r, use_container_width=True)
        with cr2:
            st.markdown("#### データに基づく推奨事項")
            if (nj_cov+nj_s+nj_ps) > (ki_cov+ki_s+ki_ps):
                st.success("**【結論】 NJSSの導入を推奨します。**\n\n網羅率が高く、過去のターゲット案件を確実に取りこぼさず捕捉できています。中長期的に見て機会損失を防ぐことで、費用対効果を最大化できる可能性が高いです。")
            else:
                st.success("**【結論】 入札王の導入を推奨します。**\n\nコストパフォーマンスが非常に高く、損益分岐点を早く超えることができます。ROI（投資対効果）を重視した運用に最適です。")

elif page == "過去案件情報入力":
    st.markdown('<div class="slds-page-header"><h1>過去案件情報入力（営業データベース）</h1></div>', unsafe_allow_html=True)
    st.write("過去の入札結果を詳細に記録し、勝率分析や次期更新に向けた営業戦略に活用します。")
    df_cur = load_data()
    valid_df = df_cur[df_cur["自治体名"].notna() & (df_cur["自治体名"] != "")].copy()
    
    with st.form("entry_form", clear_on_submit=True):
        st.markdown('<div class="form-section-header">🏢 基本情報</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        mun = c1.text_input("自治体名・発注機関 ※必須", placeholder="例: 横浜市")
        dep = c2.text_input("担当部署名", placeholder="例: デジタル統括本部")
        smm = st.text_input("案件名・案件概要 ※必須", placeholder="例: 交通データ連携（ETL）基盤構築業務")

        st.markdown('<div class="form-section-header">📅 スケジュール・要件</div>', unsafe_allow_html=True)
        c3, c4, c5 = st.columns(3)
        pub_d = c3.text_input("公示日", placeholder="例: 2025-04-01")
        bid_d = c4.text_input("入札日（提出日）", placeholder="例: 2025-05-15")
        per_d = c5.text_input("履行期間（委託期間）", placeholder="例: 2025-06-01 〜 2026-03-31")
        
        c6, c7 = st.columns(2)
        method = c6.selectbox("入札方式", ["", "公募型プロポーザル", "一般競争入札", "指名競争入札", "随意契約", "その他"])
        qual = c7.text_input("参加資格", placeholder="例: 情報処理 Aランク")

        st.markdown('<div class="form-section-header">💰 結果・金額</div>', unsafe_allow_html=True)
        c8, c9, c10 = st.columns(3)
        budget = c8.number_input("予算額 (単位: 千円)", min_value=0, step=100)
        wbid = c9.number_input("落札金額 (単位: 千円) ※必須", min_value=0, step=100)
        our_res = c10.selectbox("自社結果", ["", "受注", "失注", "見送り", "辞退"])

        c11, c12 = st.columns(2)
        wnr = c11.text_input("落札企業", placeholder="例: 株式会社ジール")
        b1 = c12.text_input("競合企業1", placeholder="例: A社")
        b2 = c11.text_input("競合企業2", placeholder="例: B社")
        b3 = c12.text_input("競合企業3", placeholder="例: C社")

        st.markdown('<div class="form-section-header">🔍 ツール掲載確認 (PoC用)</div>', unsafe_allow_html=True)
        c13, c14, c15 = st.columns(3)
        spc = c13.checkbox("仕様書あり")
        njl = c14.checkbox("NJSSに掲載あり")
        kil = c15.checkbox("入札王に掲載あり")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("この案件を保存する", type="primary", use_container_width=True):
            if mun and smm and wbid > 0:
                new_rec = pd.DataFrame([{
                    "ID": len(valid_df)+1, "自治体名": mun, "担当部署名": dep, "案件概要": smm, 
                    "公示日": pub_d, "入札日": bid_d, "履行期間": per_d, "入札方式": method, "参加資格": qual, 
                    "予算(千円)": budget, "落札金額(千円)": wbid, "自社結果": our_res, "落札企業": wnr, 
                    "競合1": b1, "競合2": b2, "競合3": b3, "仕様書": spc, "NJSS掲載": njl, "入札王掲載": kil
                }])
                try:
                    conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=pd.concat([valid_df, new_rec], ignore_index=True).fillna(""))
                    st.success("✅ スプレッドシートへの保存に成功しました！")
                except: 
                    st.error("保存に失敗しました。")
            else: 
                st.error("「自治体名」「案件名」「落札金額(1以上)」は必須項目です。")

    if not valid_df.empty:
        st.markdown("---")
        st.markdown("### 登録済みデータ一覧")
        st.dataframe(valid_df, hide_index=True, use_container_width=True)

elif page == "ワード検索数":
    st.markdown('<div class="slds-page-header"><h1>ワード検索数比較</h1></div>', unsafe_allow_html=True)
    st.write("得意分野のキーワードで検索し、各ツールでのヒット件数を入力・保存してください。")
    
    st.markdown("#### 比較キーワードの操作")
    c_add1, c_add2, c_add3 = st.columns([2, 1, 1])
    new_w = c_add1.text_input("キーワード", placeholder="例: BIツール、DX推進", key="in_new_w", label_visibility="collapsed")
    if c_add2.button("追加", type="primary", use_container_width=True):
        if new_w and new_w not in st.session_state.search_words:
            st.session_state.search_words.append(new_w); st.rerun()
    if c_add3.button("リストをクリア", type="primary", use_container_width=True): 
        st.session_state.search_words = []
        st.session_state.search_counts = {}
        st.rerun()

    st.markdown("---")
    st.markdown("#### ヒット件数の実測値テーブル")
    if st.session_state.search_words:
        df_search = pd.DataFrame([
            {"検索ワード": w, "NJSS (件)": st.session_state.search_counts.get(w, {}).get("NJSS", 0), "入札王 (件)": st.session_state.search_counts.get(w, {}).get("入札王", 0)}
            for w in st.session_state.search_words
        ])

        edited_df = st.data_editor(df_search, num_rows="dynamic", use_container_width=True, hide_index=True, key="kw_editor")
        
        if st.button("テーブルの検索件数を保存する", type="primary", use_container_width=True):
            st.session_state.search_words = edited_df["検索ワード"].dropna().tolist()
            new_counts = {}
            for _, row in edited_df.iterrows():
                if pd.notna(row["検索ワード"]):
                    new_counts[row["検索ワード"]] = {"NJSS": int(row.get("NJSS (件)", 0) or 0), "入札王": int(row.get("入札王 (件)", 0) or 0)}
            st.session_state.search_counts = new_counts
            st.success("✅ 検索件数を保存しました。ダッシュボードに反映されます。")
    else:
        st.info("キーワードを追加すると、ここに件数入力テーブルが表示されます。")

elif page == "コスト・ROI分析":
    st.markdown('<div class="slds-page-header"><h1>コスト・ROI分析設定</h1></div>', unsafe_allow_html=True)
    st.write("ツール見積額と営業パフォーマンスを入力し、採算ラインを可視化します。")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**NJSS 費用見積**")
        n_i = st.number_input("初期費用 (円)", value=st.session_state.costs["n_init"], key="n_i_v")
        n_m = st.number_input("月額費用 (円)", value=st.session_state.costs["n_month"], key="n_m_v")
        n_o = st.number_input("年間オプション (円)", value=st.session_state.costs["n_opt"], key="n_o_v")
        st.info(f"💡 NJSS 初年度合計: **{n_i + n_m*12 + n_o:,} 円**")
    with c2:
        st.markdown("**入札王 費用見積**")
        k_i = st.number_input("初期費用 (円)", value=st.session_state.costs["k_init"], key="k_i_v")
        k_m = st.number_input("月額費用 (円)", value=st.session_state.costs["k_month"], key="k_m_v")
        k_o = st.number_input("年間オプション (円)", value=st.session_state.costs["k_opt"], key="k_o_v")
        st.info(f"💡 入札王 初年度合計: **{k_i + k_m*12 + k_o:,} 円**")
    
    st.markdown("---")
    st.markdown("**自社営業シミュレーション設定**")
    cs1, cs2, cs3 = st.columns(3)
    wr = cs1.number_input("平均受注率 (%)", value=st.session_state.costs["win_rate"], help="応札に参加した場合、落札できる確率。")
    mg = cs2.number_input("平均粗利率 (%)", value=st.session_state.costs["margin"], help="落札金額に対する、自社の粗利の割合。")
    ab = cs3.number_input("年間想定応札数 (件)", value=st.session_state.costs["annual_bids"], help="1年間に何件の入札に参加するか。")
    
    if st.button("設定を保存してグラフを更新", type="primary", use_container_width=True):
        st.session_state.costs.update({"n_init": n_i, "n_month": n_m, "n_opt": n_o, "k_init": k_i, "k_month": k_m, "k_opt": k_o, "margin": mg, "win_rate": wr, "annual_bids": ab})
        st.success("✅ 設定を更新しました。")

    p_df, _ = calculate_projections()
    
    st.markdown("---")
    st.markdown("### 損益分岐点・5年収益推移シミュレーション")
    st.info("💡 以下のグラフは上記で入力された値を元に計算されています。（すべて0円・データ無しの場合は平坦になります）")
    
    fig_bep = go.Figure()
    fig_bep.add_trace(go.Scatter(x=p_df["年"], y=p_df["累積売上"], name="累積売上期待値", line=dict(color="#10B981", width=4)))
    fig_bep.add_trace(go.Scatter(x=p_df["年"], y=p_df["NJSS累積コスト"], name="NJSS累積コスト", line=dict(color="#0176D3", dash='dash')))
    fig_bep.add_trace(go.Scatter(x=p_df["年"], y=p_df["入札王累積コスト"], name="入札王累積コスト", line=dict(color="#1B96FF", dash='dash')))
    fig_bep.update_layout(title="累積コストと売上の交差点（損益分岐点）", template="plotly_white", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_bep, use_container_width=True)

    fig_prof = px.bar(p_df, x="年", y=["NJSS利益", "入札王利益"], barmode="group", title="各年の累積利益比較", color_discrete_map={"NJSS利益": "#0176D3", "入札王利益": "#1B96FF"})
    fig_prof.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_prof, use_container_width=True)

    st.markdown("---")
    st.markdown("### 📊 ROI分析結果の解説")
    n_p5 = p_df.iloc[-1]["NJSS利益"]
    k_p5 = p_df.iloc[-1]["入札王利益"]
    
    if n_p5 < 0 and k_p5 < 0:
        st.warning("**【警告】現在の設定では、5年後も両ツールとも赤字（投資回収不可）の予測です。**\n\nツール費用を回収するためには、「想定年間応札数」を増やすか、「平均受注率」「平均粗利率」を改善する必要があります。")
    elif n_p5 > k_p5:
        diff = n_p5 - k_p5
        st.success(f"**【判定】ROI（投資対効果）の観点では、NJSSが有利です。**\n\n現在の営業シミュレーションでは、5年間でNJSSの方が入札王よりも **約 {diff:,.0f} 円** 高い最終利益をもたらす予測となっています。")
    elif k_p5 > n_p5:
        diff = k_p5 - n_p5
        st.success(f"**【判定】ROI（投資対効果）の観点では、入札王が有利です。**\n\n現在の営業シミュレーションでは、コストの低さが利益に直結し、5年間で入札王の方がNJSSよりも **約 {diff:,.0f} 円** 高い最終利益をもたらす予測となっています。")
    else:
        st.info("**【判定】両ツールの投資対効果はほぼ同等です。**\n\nコスト面での差が少ないため、ダッシュボードの「網羅率」や「検索精度」など、機能面での優劣を重視して選定してください。")

elif page == "詳細マニュアル":
    st.markdown('<div class="slds-page-header"><h1>自走式 PoC評価マニュアル</h1></div>', unsafe_allow_html=True)
    st.markdown("""
    本システムは、入札情報サービス（NJSS、入札王等）の導入前検証（PoC）において、感覚ではなく**データに基づいた合理的な決裁**を行うための分析ツール、兼**営業データベース**です。

    ### 1. 営業データベースとしての活用
    今回より、過去案件入力に「担当部署」「入札方式」「スケジュール」などを記録できるようになりました。
    * **プロポーザル方式の勝率分析**: 自社が企画重視の案件に強いのか、価格競争に強いのかが分析できます。
    * **次期更新の事前営業**: 履行期間から逆算し、次回の入札公示前に担当部署へ直接アプローチする（仕様に食い込む）ことが可能になります。

    ### 2. PoC検証の全体フロー
    **STEP 1: 過去データの準備**
    「過去案件情報入力」画面に、関連する過去案件を10〜20件入力します。
    
    **STEP 2: ツールでの検索実測**
    各ツールのトライアルアカウントを使用し、STEP 1で入力した案件が「実際に検索して見つかるか」を確認してチェックを入れます。
    
    **STEP 3: キーワード検索ボリュームの確認**
    「ワード検索数」画面を開き、得意領域（例：DX推進）で検索した結果のヒット件数を入力し、保存します。
    
    **STEP 4: コストシミュレーションの設定**
    「コスト・ROI分析」画面を開き、見積もり金額と、平均受注率・利益率を設定します。これで「何年目で黒字化するか」が算出されます。
    
    **STEP 5: 最終判断と稟議**
    「ダッシュボード」画面を確認してください。入力した全データが統合され、レーダーチャートと推奨テキストが出力されます。この画面をキャプチャし稟議書に添付してください。
    """)

elif page == "データ管理 (一括・初期化)":
    st.markdown('<div class="slds-page-header"><h1>データ一括管理・初期化</h1></div>', unsafe_allow_html=True)
    
    st.markdown("### 🏆 万能テスト用 サンプルCSVダウンロード")
    st.write("このCSVをアップロードするだけで、**「コスト」「検索ワード」「過去案件（詳細項目含む）」のすべてが自動セットアップ**され、ダッシュボードが一瞬で完成します。")
    
    # 💡 項目を増やした最強サンプルCSVデータ
    sample_data = [
        {"ID": "SETTING_COST", "自治体名": "NJSS初期費用", "落札金額(千円)": 100000},
        {"ID": "SETTING_COST", "自治体名": "NJSS月額費用", "落札金額(千円)": 50000},
        {"ID": "SETTING_COST", "自治体名": "入札王初期費用", "落札金額(千円)": 0},
        {"ID": "SETTING_COST", "自治体名": "入札王月額費用", "落札金額(千円)": 30000},
        {"ID": "SETTING_COST", "自治体名": "平均受注率", "落札金額(千円)": 25},
        {"ID": "SETTING_COST", "自治体名": "平均粗利率", "落札金額(千円)": 30},
        {"ID": "SETTING_COST", "自治体名": "年間想定応札数", "落札金額(千円)": 50},
        {"ID": "SETTING_WORD", "自治体名": "データ分析基盤", "案件概要": "150", "落札企業": "120"},
        {"ID": "SETTING_WORD", "自治体名": "BIツール", "案件概要": "80", "落札企業": "90"},
        {"ID": 1, "自治体名": "東京都", "担当部署名": "デジタルサービス局", "案件概要": "ダッシュボード構築業務", "公示日": "2025-04-01", "入札日": "2025-05-10", "履行期間": "2026-03-31まで", "入札方式": "公募型プロポーザル", "参加資格": "Aランク", "予算(千円)": 20000, "落札金額(千円)": 15000, "自社結果": "受注", "落札企業": "株式会社ジール", "競合1": "A社", "競合2": "B社", "競合3": "", "仕様書": True, "NJSS掲載": True, "入札王掲載": False},
        {"ID": 2, "自治体名": "大阪府", "担当部署名": "スマートシティ戦略部", "案件概要": "BIツールライセンス更新", "公示日": "2025-06-01", "入札日": "2025-07-15", "履行期間": "1年間", "入札方式": "一般競争入札", "参加資格": "情報処理", "予算(千円)": 10000, "落札金額(千円)": 8000, "自社結果": "失注", "落札企業": "C社", "競合1": "株式会社ジール", "競合2": "", "競合3": "", "仕様書": True, "NJSS掲載": True, "入札王掲載": True}
    ]
    st.download_button("万能サンプルCSVをダウンロード", data=pd.DataFrame(sample_data).to_csv(index=False).encode('utf-8-sig'), file_name="database_sample.csv", mime="text/csv", type="primary")
    
    st.markdown("---")
    st.markdown("### CSV一括インポート")
    up_f = st.file_uploader("作成またはダウンロードしたCSVをアップロード", type="csv")
    if up_f:
        im_df = pd.read_csv(up_f, encoding="utf-8-sig")
        st.write("プレビュー (先頭5件):")
        st.dataframe(im_df.head())
        
        if st.button("このデータをシステムとスプレッドシートへ書き込む", type="primary", use_container_width=True):
            try:
                new_projects = []
                for _, row in im_df.iterrows():
                    tag = str(row.get('ID', ''))
                    if tag == "SETTING_COST":
                        item = str(row.get('自治体名', ''))
                        val = int(pd.to_numeric(row.get('落札金額(千円)', 0), errors='coerce'))
                        if pd.isna(val): val = 0
                        
                        if "NJSS初期" in item: st.session_state.costs["n_init"] = val
                        elif "NJSS月額" in item: st.session_state.costs["n_month"] = val
                        elif "入札王初期" in item: st.session_state.costs["k_init"] = val
                        elif "入札王月額" in item: st.session_state.costs["k_month"] = val
                        elif "受注率" in item: st.session_state.costs["win_rate"] = val
                        elif "粗利率" in item: st.session_state.costs["margin"] = val
                        elif "応札数" in item: st.session_state.costs["annual_bids"] = val
                    
                    elif tag == "SETTING_WORD":
                        word = str(row.get('自治体名', ''))
                        if word:
                            if word not in st.session_state.search_words: st.session_state.search_words.append(word)
                            nj_val = int(pd.to_numeric(row.get('案件概要', 0), errors='coerce'))
                            ki_val = int(pd.to_numeric(row.get('落札企業', 0), errors='coerce'))
                            st.session_state.search_counts[word] = {"NJSS": nj_val if pd.notna(nj_val) else 0, "入札王": ki_val if pd.notna(ki_val) else 0}
                    else:
                        if pd.notna(row.get('自治体名')) and str(row.get('自治体名')).strip() != "":
                            new_projects.append(row)
                
                if new_projects:
                    final_df = pd.concat([load_data(), pd.DataFrame(new_projects)], ignore_index=True).fillna("")
                    conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=final_df)
                
                st.success("✅ コスト設定、検索ワード、過去案件データのすべてを正常に読み込み・保存しました！ダッシュボードを確認してください。")
            except Exception as e: 
                st.error(f"保存に失敗しました。詳細: {e}")
                
    st.markdown("---")
    # 💡 隠し機能：データの完全初期化 (安全確認付き)
    with st.expander("🚨 危険操作：全データの初期化（テスト完了後のリセット用）"):
        st.warning("スプレッドシートの全案件データ、コスト設定、検索ワードを完全に消去し、空っぽの初期状態に戻します。")
        confirm = st.checkbox("本当にすべてのデータを消去してよろしいですか？（この操作は元に戻せません）")
        
        if st.button("全データを初期化して空っぽにする", type="primary", use_container_width=True):
            if confirm:
                try:
                    conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=pd.DataFrame(columns=CORRECT_COLUMNS))
                    st.session_state.search_words = []
                    st.session_state.search_counts = {}
                    st.session_state.costs = {"n_init": 0, "n_month": 0, "n_opt": 0, "k_init": 0, "k_month": 0, "k_opt": 0, "margin": 20, "win_rate": 20, "annual_bids": 50}
                    st.success("✅ すべてのデータを消去し、初期状態に戻しました。")
                    st.rerun()
                except: 
                    st.error("初期化に失敗しました。")
            else:
                st.error("※消去を実行するには、上の確認チェックボックスにチェックを入れてください。")
