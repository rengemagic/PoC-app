import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection
import io
import csv
import traceback
import base64

# --- 1. ページ初期設定 (タイトルを英語に統一) ---
st.set_page_config(page_title="Analytics Solution Board", layout="wide")

# --- 2. ユーティリティ関数 ---
# ロゴ画像を中央揃えでHTML表示するためのBase64エンコード関数
def get_image_base64(path):
    try:
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except FileNotFoundError:
        return None

# --- 3. UI & CSS (ダッシュボード用共通デザイン) ---
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

    /* ページメインタイトル装飾 */
    .slds-page-header { 
        background-color: #FFFFFF !important; 
        padding: 1.5rem 2rem; 
        border-bottom: 1px solid #E2E8F0; 
        margin: -2rem -4rem 2rem -4rem; 
        border-left: 8px solid #0176D3; 
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .slds-page-header h1 { color: #0F172A !important; font-size: 1.5rem; font-weight: 700; margin: 0; }
    
    /* サブタイトル(セクション見出し)の装飾 */
    .section-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #0F172A;
        padding-left: 14px;
        border-left: 5px solid #0176D3;
        border-bottom: 1px solid #E2E8F0;
        padding-bottom: 8px;
        margin-top: 2.5rem;
        margin-bottom: 1.5rem;
        letter-spacing: 0.05em;
    }

    /* すべてのボタンを完全な「青」に統一 */
    button[kind="primary"], button[kind="secondary"], button[kind="secondaryFormSubmit"], .stButton > button, .stDownloadButton > button { 
        background-color: #0176D3 !important; 
        color: #FFFFFF !important; 
        border-radius: 6px !important; 
        font-weight: 700 !important; 
        font-size: 1.05rem !important;
        border: none !important; 
        padding: 0.6rem 1.5rem !important; 
        transition: all 0.2s ease;
    }
    button[kind="primary"]:hover, button[kind="secondary"]:hover, button[kind="secondaryFormSubmit"]:hover, .stButton > button:hover, .stDownloadButton > button:hover { 
        background-color: #014486 !important; 
        color: #FFFFFF !important;
        transform: translateY(-2px); 
        box-shadow: 0 4px 6px rgba(1, 118, 211, 0.3); 
    }

    /* フォーム（ログイン画面や入力画面）をクールなカード風に装飾 */
    [data-testid="stForm"] {
        background-color: #FFFFFF;
        padding: 2.5rem 2rem;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
        border: 1px solid #E2E8F0;
        border-top: 5px solid #0176D3;
    }

    /* 入力フォームのデザイン */
    div[data-baseweb="input"], input, textarea { background-color: #F8FAFC !important; color: #0F172A !important; border-radius: 6px !important; border-color: #CBD5E1 !important; }
    div[data-baseweb="input"]:focus-within { border-color: #0176D3 !important; background-color: #FFFFFF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. セキュリティ：クールなログイン画面 ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    # 💡 【重要】ログイン画面専用のスタイル（背景を真っ白にしてロゴを同化させる）
    st.markdown("""
        <style>
        [data-testid="stAppViewContainer"] { background-color: #FFFFFF !important; }
        </style>
    """, unsafe_allow_html=True)

    # 画面中央に配置するためにカラム幅を調整
    col1, col2, col3 = st.columns([1, 1.2, 1])
    
    with col2:
        # 上部の余白
        st.markdown("<div style='margin-top: 8vh;'></div>", unsafe_allow_html=True)
        
        # 💡 ① ロゴ画像を一番上に配置
        logo_base64 = get_image_base64("image_2.png")
        if logo_base64:
            st.markdown(f"""
                <div style="text-align: center; margin-bottom: 10px;">
                    <img src="data:image/png;base64,{logo_base64}" width="300">
                </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("ロゴ画像が見つかりません。")

        # 💡 ② タイトルテキストをロゴの下に配置
        st.markdown("""
            <div style="text-align: center; margin-bottom: 30px;">
                <div style="font-size: 32px; font-weight: 800; color: #0F172A; letter-spacing: 1px; margin-bottom: 5px;">Analytics Solution Board</div>
                <div style="font-size: 13px; color: #64748B; letter-spacing: 2px;">PoC ANALYTICS DASHBOARD</div>
            </div>
        """, unsafe_allow_html=True)
        
        # 💡 ③ ログインフォームを一番下に配置
        with st.form("login_form"):
            st.markdown("<p style='font-size: 13px; color: #64748B; letter-spacing: 2px; font-weight: 600; text-align: center; margin-bottom: 25px;'>SECURE SYSTEM LOGIN</p>", unsafe_allow_html=True)
            user_id = st.text_input("ユーザーID", placeholder="ID")
            password = st.text_input("パスワード", type="password", placeholder="Password")
            st.markdown("<br>", unsafe_allow_html=True)
            submit = st.form_submit_button("ログイン", use_container_width=True)
            
            if submit:
                if user_id == "zeal_admin" and password == "poc2026!":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("IDまたはパスワードが間違っています。")

    st.stop()

# --- 5. カスタム関数・状態初期化 ---
def draw_kpi_card(title, value):
    st.markdown(f"""
        <div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 1.2rem; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.02); margin-bottom: 1rem;">
            <p style="color: #64748B; font-size: 13px; font-weight: 700; margin: 0 0 8px 0; letter-spacing: 0.5px;">{title}</p>
            <p style="color: #0176D3; font-size: 32px; font-weight: 700; margin: 0; line-height: 1.2;">{value}</p>
        </div>
    """, unsafe_allow_html=True)

if 'search_words' not in st.session_state: st.session_state.search_words = []
if 'search_counts' not in st.session_state: st.session_state.search_counts = {}
if 'costs' not in st.session_state: 
    st.session_state.costs = {"n_init": 0, "n_month": 0, "n_opt": 0, "k_init": 0, "k_month": 0, "k_opt": 0, "margin": 0, "win_rate": 0, "annual_bids": 0}

# --- 6. データ接続と上書き保存関数 ---
conn = st.connection("gsheets", type=GSheetsConnection)
CORRECT_COLUMNS = ["ID", "自治体名", "案件概要", "仕様書", "予算(千円)", "落札金額(千円)", "落札企業", "応札1", "応札2", "応札3", "NJSS掲載", "入札王掲載"]

def load_data():
    try:
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        df = conn.read(spreadsheet=url, ttl="0s")
        if "自治体名" not in df.columns: return pd.DataFrame(columns=CORRECT_COLUMNS)
        return df
    except: return pd.DataFrame(columns=CORRECT_COLUMNS)

def save_data_to_gsheets(new_df):
    current_df = load_data()
    if len(new_df) < len(current_df):
        pad_len = len(current_df) - len(new_df)
        empty_pad = pd.DataFrame([[""] * len(CORRECT_COLUMNS) for _ in range(pad_len)], columns=CORRECT_COLUMNS)
        save_df = pd.concat([new_df, empty_pad], ignore_index=True)
    else:
        save_df = new_df
    conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=save_df)

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

# --- 7. サイドバー ---
with st.sidebar:
    # 💡 サイドバーのロゴ配置
    logo_sidebar_base64 = get_image_base64("image_2.png")
    if logo_sidebar_base64:
        st.markdown(f"""
            <div style="text-align: center; margin-bottom: 20px;">
                <img src="data:image/png;base64,{logo_sidebar_base64}" width="150">
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown('<p class="sidebar-section-header">Menu</p>', unsafe_allow_html=True)
    test_mode = st.toggle("データ管理モード")
    menu_options = ["ダッシュボード", "過去案件情報入力", "ワード検索数", "コスト・ROI分析", "詳細マニュアル"]
    if test_mode: menu_options.append("データ管理 (一括・初期化)")
    page = st.radio("メニュー選択", menu_options, label_visibility="collapsed")
    
    st.markdown("---")
    if st.button("ログアウト", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# --- 8. コンテンツ表示 ---

if page == "ダッシュボード":
    st.markdown('<div class="slds-page-header"><h1>Analytics Solution Board</h1></div>', unsafe_allow_html=True)
    df = load_data()
    valid_df = df[df["自治体名"].notna() & (df["自治体名"] != "")]
    
    if valid_df.empty:
        st.info("データがありません。「過去案件情報入力」または「データ管理」からデータを登録してください。")
    else:
        st.markdown('<div class="section-title">Project Coverage Summary</div>', unsafe_allow_html=True)
        
        nj_c = valid_df["NJSS掲載"].astype(str).str.upper().isin(["TRUE", "1", "1.0", "YES"]).sum()
        ki_c = valid_df["入札王掲載"].astype(str).str.upper().isin(["TRUE", "1", "1.0", "YES"]).sum()
        avg_bid_val = valid_df["落札金額(千円)"].mean() * 1000
        exp_profit = avg_bid_val * (st.session_state.costs["margin"]/100) * (st.session_state.costs["win_rate"]/100)
        comp_series = pd.concat([valid_df["応札1"], valid_df["応札2"], valid_df["応札3"]])
        comp_count = comp_series[comp_series != ""].nunique()

        k1, k2, k3 = st.columns(3)
        with k1: draw_kpi_card("分析対象案件数 (Total Projects)", f"{len(valid_df)} 件")
        with k2: draw_kpi_card("NJSS 網羅率 (NJSS Coverage)", f"{(nj_c/len(valid_df)*100):.1f}%")
        with k3: draw_kpi_card("入札王 網羅率 (Hits Coverage)", f"{(ki_c/len(valid_df)*100):.1f}%")
        
        k4, k5, k6 = st.columns(3)
        with k4: draw_kpi_card("平均落札金額", f"¥ {int(avg_bid_val):,}")
        with k5: draw_kpi_card("1応札あたりの期待利益", f"¥ {int(exp_profit):,}")
        with k6: draw_kpi_card("観測された競合企業数", f"{comp_count} 社")

        st.markdown('<div class="section-title">Detailed Analysis Charts</div>', unsafe_allow_html=True)
        col_l, col_r = st.columns(2)
        with col_l:
            fig_hits = px.bar(x=["NJSS", "Hits"], y=[nj_c, ki_c], title="案件捕捉数の比較 (Capture Hits Comparison)", color=["NJSS", "Hits"], color_discrete_map={"NJSS": "#0176D3", "Hits": "#1B96FF"})
            fig_hits.update_layout(template="plotly_white", xaxis_title=None, yaxis_title=None, margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_hits, use_container_width=True)
            
        with col_r:
            pres_df = comp_series[comp_series != ""].value_counts().reset_index().head(6)
            pres_df.columns = ["企業名", "出現回数"]
            fig_p = px.bar(pres_df, x="出現回数", y="企業名", orientation='h', title="競合出現シェア (上位6社) (Competitor Share)")
            fig_p.update_traces(marker_color='#0176D3')
            fig_p.update_layout(template="plotly_white", xaxis_title=None, yaxis_title=None, margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_p, use_container_width=True)

        st.markdown('<div class="section-title">Keyword Search Accuracy</div>', unsafe_allow_html=True)
        if st.session_state.search_words and st.session_state.search_counts:
            s_data = []
            for w in st.session_state.search_words:
                n_val = st.session_state.search_counts.get(w, {}).get("NJSS", 0)
                k_val = st.session_state.search_counts.get(w, {}).get("入札王", 0)
                s_data.append({"ワード": w, "NJSS": n_val, "Hits": k_val})
            df_sw = pd.DataFrame(s_data)
            if not df_sw.empty:
                fig_sw = px.bar(df_sw, x="ワード", y=["NJSS", "Hits"], barmode="group", color_discrete_map={"NJSS": "#0176D3", "Hits": "#1B96FF"})
                fig_sw.update_layout(template="plotly_white", xaxis_title=None, yaxis_title=None, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_sw, use_container_width=True)
        else:
            st.write("検索ワードのデータがありません。「ワード検索数」画面からデータを追加してください。")

        st.markdown('<div class="section-title">5-Year Cumulative Profit Projection</div>', unsafe_allow_html=True)
        st.info("下記は「コスト・ROI分析」で設定された数値を元に描画されています。（設定が0円等の場合は平坦なグラフになります）")
        p_df, _ = calculate_projections()
        fig_proj = px.line(p_df, x="年", y=["NJSS利益", "入札王利益"], color_discrete_map={"NJSS利益": "#0176D3", "入札王利益": "#1B96FF"})
        fig_proj.update_layout(template="plotly_white", xaxis_title=None, yaxis_title=None, paper_bgcolor="rgba(0,0,0,0)")
        fig_proj.data[0].name="NJSS Profit"; fig_proj.data[1].name="Hits Profit"
        st.plotly_chart(fig_proj, use_container_width=True)

        st.markdown('<div class="section-title">Overall Judgment & Analytics Report</div>', unsafe_allow_html=True)
        
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
        cat = ['Coverage', 'Accuracy', 'Profitability (5Y ROI)', 'Coverage']
        fig_r.add_trace(go.Scatterpolar(r=[nj_cov, nj_s, nj_ps, nj_cov], theta=cat, fill='toself', name='NJSS', line_color='#0176D3'))
        fig_r.add_trace(go.Scatterpolar(r=[ki_cov, ki_s, ki_ps, ki_cov], theta=cat, fill='toself', name='Hits', line_color='#1B96FF'))
        fig_r.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), margin=dict(t=30, b=30), paper_bgcolor="rgba(0,0,0,0)")
        
        cr1, cr2 = st.columns([1, 1])
        with cr1: st.plotly_chart(fig_r, use_container_width=True)
        with cr2:
            st.markdown("#### データに基づく推奨事項 (Recommendations)")
            if (nj_cov+nj_s+nj_ps) > (ki_cov+ki_s+ki_ps):
                st.success("【結論】 NJSSの導入を推奨します。\n\n網羅率が高く、過去のターゲット案件を確実に取りこぼさず捕捉できています。中長期的に見て機会損失を防ぐことで、費用対効果を最大化できる可能性が高いです。")
            else:
                st.success("【結論】 Hits (入札王) の導入を推奨します。\n\nコストパフォーマンスが非常に高く、損益分岐点を早く超えることができます。ROI（投資対効果）を重視した運用に最適です。")

elif page == "過去案件情報入力":
    st.markdown('<div class="slds-page-header"><h1>過去案件情報入力</h1></div>', unsafe_allow_html=True)
    st.write("関連する過去の案件情報を入力してください。このデータが「網羅率」と「ROI」の計算ベースになります。")
    df_cur = load_data()
    valid_df = df_cur[df_cur["自治体名"].notna() & (df_cur["自治体名"] != "")].copy()
    
    st.markdown('<div class="section-title">新規案件の登録</div>', unsafe_allow_html=True)
    with st.form("entry_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        mun = c1.text_input("自治体名 (必須)", placeholder="例: 東京都、横浜市", help="発注元の自治体名を入力します。")
        smm = c2.text_area("案件概要", placeholder="例: データ分析基盤構築業務", help="どのような案件だったかを簡潔に記載します。")
        
        st.markdown("#### 落札・応札情報")
        c3, c4 = st.columns(2)
        wnr = c3.text_input("落札企業", placeholder="例: 株式会社ジール", help="最終的に落札した企業名です。自社の場合は自社名を入力。")
        wbid = c3.number_input("落札金額 (単位: 千円)", min_value=0, help="この金額の平均値が、利益予測シミュレーションのベースとなります。")
        b1 = c4.text_input("競合企業1", placeholder="例: A社", help="入札に参加していた競合他社を入力します。")
        b2 = c4.text_input("競合企業2", placeholder="例: B社")
        
        st.markdown("#### ツール掲載確認 (実測結果)")
        st.write("各ツールのトライアル等で、この案件が実際にヒットするか確認してチェックを入れてください。")
        c5, c6, c7 = st.columns(3)
        spc = c5.checkbox("仕様書あり")
        njl = c6.checkbox("NJSSに掲載あり")
        kil = c7.checkbox("Hitsに掲載あり")
        
        if st.form_submit_button("この案件を保存する", use_container_width=True):
            if mun:
                new_rec = pd.DataFrame([{"ID": len(valid_df)+1, "自治体名": mun, "案件概要": smm, "仕様書": spc, "予算(千円)": 0, "落札金額(千円)": wbid, "落札企業": wnr, "応札1": b1, "応札2": b2, "応札3": "", "NJSS掲載": njl, "入札王掲載": kil}])
                try:
                    save_data_to_gsheets(pd.concat([valid_df, new_rec], ignore_index=True).fillna(""))
                    st.success("スプレッドシートへの保存に成功しました。")
                except: 
                    st.error("保存に失敗しました。")
            else: 
                st.error("自治体名は必須項目です。")

    if not valid_df.empty:
        st.markdown('<div class="section-title">登録済みデータ一覧</div>', unsafe_allow_html=True)
        st.dataframe(valid_df, hide_index=True, use_container_width=True)

elif page == "ワード検索数":
    st.markdown('<div class="slds-page-header"><h1>ワード検索数比較</h1></div>', unsafe_allow_html=True)
    st.write("得意分野のキーワードで検索し、各ツールでのヒット件数を入力・保存してください。")
    
    st.markdown('<div class="section-title">比較キーワードの操作</div>', unsafe_allow_html=True)
    c_add1, c_add2, c_add3 = st.columns([2, 1, 1])
    new_w = c_add1.text_input("キーワード", placeholder="例: BIツール、DX推進", key="in_new_w", label_visibility="collapsed")
    if c_add2.button("追加", use_container_width=True):
        if new_w and new_w not in st.session_state.search_words:
            st.session_state.search_words.append(new_w); st.rerun()
    if c_add3.button("リストをクリア", use_container_width=True): 
        st.session_state.search_words = []
        st.session_state.search_counts = {}
        st.rerun()

    st.markdown('<div class="section-title">ヒット件数の実測値テーブル</div>', unsafe_allow_html=True)
    if st.session_state.search_words:
        df_search = pd.DataFrame([
            {"検索ワード": w, "NJSS (件)": st.session_state.search_counts.get(w, {}).get("NJSS", 0), "Hits (件)": st.session_state.search_counts.get(w, {}).get("入札王", 0)}
            for w in st.session_state.search_words
        ])

        edited_df = st.data_editor(df_search, num_rows="dynamic", use_container_width=True, hide_index=True, key="kw_editor")
        
        if st.button("テーブルの検索件数を保存する", use_container_width=True):
            st.session_state.search_words = edited_df["検索ワード"].dropna().tolist()
            new_counts = {}
            for _, row in edited_df.iterrows():
                if pd.notna(row["検索ワード"]):
                    new_counts[row["検索ワード"]] = {"NJSS": int(row.get("NJSS (件)", 0) or 0), "入札王": int(row.get("Hits (件)", 0) or 0)}
            st.session_state.search_counts = new_counts
            st.success("検索件数を保存しました。ダッシュボードに反映されます。")
    else:
        st.info("キーワードを追加すると、ここに件数入力テーブルが表示されます。")

elif page == "コスト・ROI分析":
    st.markdown('<div class="slds-page-header"><h1>コスト・ROI分析設定</h1></div>', unsafe_allow_html=True)
    st.write("ツール見積額と営業パフォーマンスを入力し、採算ラインを可視化します。")
    
    st.markdown('<div class="section-title">ツール費用見積の設定</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**NJSS**")
        n_i = st.number_input("初期費用 (円)", value=st.session_state.costs["n_init"], key="n_i_v")
        n_m = st.number_input("月額費用 (円)", value=st.session_state.costs["n_month"], key="n_m_v")
        n_o = st.number_input("年間オプション (円)", value=st.session_state.costs["n_opt"], key="n_o_v")
        st.info(f"NJSS 初年度合計: {n_i + n_m*12 + n_o:,} 円")
    with c2:
        st.markdown("**Hits**")
        k_i = st.number_input("初期費用 (円)", value=st.session_state.costs["k_init"], key="k_i_v")
        k_m = st.number_input("月額費用 (円)", value=st.session_state.costs["k_month"], key="k_m_v")
        k_o = st.number_input("年間オプション (円)", value=st.session_state.costs["k_opt"], key="k_o_v")
        st.info(f"Hits 初年度合計: {k_i + k_m*12 + k_o:,} 円")
    
    st.markdown('<div class="section-title">自社営業シミュレーション設定</div>', unsafe_allow_html=True)
    cs1, cs2, cs3 = st.columns(3)
    wr = cs1.number_input("平均受注率 (%)", value=st.session_state.costs["win_rate"], help="応札に参加した場合、落札できる確率。")
    mg = cs2.number_input("平均粗利率 (%)", value=st.session_state.costs["margin"], help="落札金額に対する、自社の粗利の割合。")
    ab = cs3.number_input("年間想定応札数 (件)", value=st.session_state.costs["annual_bids"], help="1年間に何件の入札に参加するか。")
    
    if st.button("設定を保存してグラフを更新", use_container_width=True):
        st.session_state.costs.update({"n_init": n_i, "n_month": n_m, "n_opt": n_o, "k_init": k_i, "k_month": k_m, "k_opt": k_o, "margin": mg, "win_rate": wr, "annual_bids": ab})
        st.success("設定を更新しました。")

    p_df, _ = calculate_projections()
    
    st.markdown('<div class="section-title">損益分岐点・5年収益推移シミュレーション</div>', unsafe_allow_html=True)
    st.info("以下のグラフは上記で入力された値を元に計算されています。（すべて0円・データ無しの場合は平坦になります）")
    
    fig_bep = go.Figure()
    fig_bep.add_trace(go.Scatter(x=p_df["年"], y=p_df["累積売上"], name="累積売上期待値 (Cumulative Rev)", line=dict(color="#10B981", width=4)))
    fig_bep.add_trace(go.Scatter(x=p_df["年"], y=p_df["NJSS累積コスト"], name="NJSS累積コスト (NJSS Cost)", line=dict(color="#0176D3", dash='dash')))
    fig_bep.add_trace(go.Scatter(x=p_df["年"], y=p_df["入札王累積コスト"], name="Hits累積コスト (Hits Cost)", line=dict(color="#1B96FF", dash='dash')))
    fig_bep.update_layout(title="累積コストと売上の交差点（損益分岐点）", template="plotly_white", xaxis_title=None, yaxis_title=None, paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_bep, use_container_width=True)

    fig_prof = px.bar(p_df, x="年", y=["NJSS利益", "入札王利益"], barmode="group", title="各年の累積利益比較", color_discrete_map={"NJSS利益": "#0176D3", "入札王利益": "#1B96FF"})
    fig_prof.update_layout(template="plotly_white", xaxis_title=None, yaxis_title=None, paper_bgcolor="rgba(0,0,0,0)")
    fig_prof.data[0].name="NJSS Profit"; fig_prof.data[1].name="Hits Profit"
    st.plotly_chart(fig_prof, use_container_width=True)

    st.markdown('<div class="section-title">ROI分析結果の解説</div>', unsafe_allow_html=True)
    n_p5 = p_df.iloc[-1]["NJSS利益"]
    k_p5 = p_df.iloc[-1]["入札王利益"]
    
    if n_p5 == 0 and k_p5 == 0:
        st.info("上部の設定に数値を入力すると、こちらに5年後の予測と評価コメントが表示されます。")
    elif n_p5 < 0 and k_p5 < 0:
        st.warning("【警告】現在の設定では、5年後も両ツールとも赤字（投資回収不可）の予測です。\n\nツール費用を回収するためには、「想定年間応札数」を増やすか、「平均受注率」「平均粗利率」を改善する必要があります。")
    elif n_p5 > k_p5:
        diff = n_p5 - k_p5
        st.success(f"【判定】ROI（投資対効果）の観点では、NJSSが有利です。\n\n現在の営業シミュレーションでは、5年間でNJSSの方が入札王よりも 約 {diff:,.0f} 円 高い最終利益をもたらす予測となっています。")
    elif k_p5 > n_p5:
        diff = k_p5 - n_p5
        st.success(f"【判定】ROI（投資対効果）の観点では、Hits (入札王) が有利です。\n\n現在の営業シミュレーションでは、コストの低さが利益に直結し、5年間で入札王の方がNJSSよりも 約 {diff:,.0f} 円 高い最終利益をもたらす予測となっています。")
    else:
        st.info("【判定】両ツールの投資対効果はほぼ同等です。\n\nコスト面での差が少ないため、ダッシュボードの「網羅率」や「検索精度」など、機能面での優劣を重視して選定してください。")

elif page == "詳細マニュアル":
    st.markdown('<div class="slds-page-header"><h1>自走式 PoC評価マニュアル</h1></div>', unsafe_allow_html=True)
    st.markdown("""
    本システムは、入札情報サービス（NJSS、入札王等）の導入前検証（PoC）において、感覚ではなく**データに基づいた合理的な決裁**を行うための分析ツールです。

    ### 1. 検証の全体フロー（自走手順）
    
    **STEP 1: 過去データの準備**
    「過去案件情報入力」画面に、関連する過去案件を10〜20件入力します。件数が多いほどシミュレーション精度が上がります。
    
    **STEP 2: ツールでの検索実測**
    各ツールのトライアルアカウントを使用し、STEP 1で入力した案件が「実際に検索して見つかるか」を確認してチェックを入れます。
    
    **STEP 3: キーワード検索ボリュームの確認**
    「ワード検索数」画面を開き、得意領域で検索した結果のヒット件数を入力し、保存します。
    
    **STEP 4: コストシミュレーションの設定**
    「コスト・ROI分析」画面を開き、見積もり金額と、平均受注率・利益率を設定します。これで「何年目で黒字化するか」が算出されます。
    
    **STEP 5: 最終判断と稟議**
    「ダッシュボード」画面を確認してください。入力した全データが統合され、レーダーチャートと推奨テキストが出力されます。この画面をキャプチャし稟議書に添付してください。
    """)

elif page == "データ管理 (一括・初期化)":
    st.markdown('<div class="slds-page-header"><h1>データ一括管理・初期化</h1></div>', unsafe_allow_html=True)
    
    st.markdown('<div class="section-title">テスト用 サンプルCSVダウンロード</div>', unsafe_allow_html=True)
    st.write("このCSVをアップロードするだけで、「コスト」「検索ワード」「過去案件」のすべてが自動セットアップされ、ダッシュボードが一瞬で完成します。テストやデモにご利用ください。")
    
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
        {"ID": 1, "自治体名": "東京都", "案件概要": "ダッシュボード構築", "仕様書": True, "予算(千円)": 0, "落札金額(千円)": 15000, "落札企業": "株式会社ジール", "応札1": "A社", "応札2": "B社", "応札3": "", "NJSS掲載": True, "入札王掲載": False},
        {"ID": 2, "自治体名": "大阪府", "案件概要": "BIツールライセンス更新", "仕様書": True, "予算(千円)": 0, "落札金額(千円)": 8000, "落札企業": "C社", "応札1": "株式会社ジール", "応札2": "", "応札3": "", "NJSS掲載": True, "入札王掲載": True}
    ]
    st.download_button("万能サンプルCSVをダウンロード", data=pd.DataFrame(sample_data).to_csv(index=False).encode('utf-8-sig'), file_name="all_in_one_sample.csv", mime="text/csv")
    
    st.markdown('<div class="section-title">CSV一括インポート</div>', unsafe_allow_html=True)
    up_f = st.file_uploader("作成またはダウンロードしたCSVをアップロード", type="csv")
    if up_f:
        im_df = pd.read_csv(up_f, encoding="utf-8-sig")
        st.write("プレビュー (先頭5件):")
        st.dataframe(im_df.head())
        
        if st.button("このデータをシステムとスプレッドシートへ書き込む", use_container_width=True):
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
                    save_data_to_gsheets(pd.DataFrame(new_projects))
                
                st.success("コスト設定、検索ワード、過去案件データのすべてを正常に読み込み・保存しました。ダッシュボードを確認してください。")
            except Exception as e: 
                st.error(f"保存に失敗しました。詳細: {e}")
                
    st.markdown('<div class="section-title">危険操作：全データの初期化</div>', unsafe_allow_html=True)
    with st.expander("テスト完了後のリセット用"):
        st.warning("スプレッドシートの全案件データ、コスト設定、検索ワードを完全に消去し、空っぽの初期状態に戻します。")
        confirm = st.checkbox("本当にすべてのデータを消去してよろしいですか？（この操作は元に戻せません）")
        
        if st.button("全データを初期化して空っぽにする", use_container_width=True):
            if confirm:
                try:
                    save_data_to_gsheets(pd.DataFrame(columns=CORRECT_COLUMNS))
                    st.session_state.search_words = []
                    st.session_state.search_counts = {}
                    st.session_state.costs = {"n_init": 0, "n_month": 0, "n_opt": 0, "k_init": 0, "k_month": 0, "k_opt": 0, "margin": 0, "win_rate": 0, "annual_bids": 0}
                    st.success("すべてのデータを完全に消去し、初期状態に戻しました。")
                    st.rerun()
                except Exception as e: 
                    st.error(f"初期化に失敗しました。詳細: {e}")
            else:
                st.error("※消去を実行するには、上の確認チェックボックスにチェックを入れてください。")
