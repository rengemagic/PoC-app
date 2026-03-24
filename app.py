import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# 1. ページ設定とSalesforce風カスタムCSS
st.set_page_config(page_title="PoC Evaluation Dashboard", layout="wide")

st.markdown("""
    <style>
    /* Salesforce風ブランドカラーと背景 */
    .main {
        background-color: #f3f3f2;
    }
    .stButton>button {
        background-color: #0176D3;
        color: white;
        border-radius: 4px;
        border: none;
        padding: 0.5rem 1rem;
    }
    .stButton>button:hover {
        background-color: #014486;
        color: white;
    }
    /* カード風のデザイン */
    div[data-testid="stExpander"] {
        background-color: white;
        border: 1px solid #dddbda;
        border-radius: .25rem;
        box-shadow: 0 2px 2px 0 rgba(0,0,0,0.1);
    }
    /* ヘッダーのデザイン */
    h1 {
        color: #1b1b1b;
        font-family: 'Salesforce Sans', Arial, sans-serif;
        border-bottom: 2px solid #0176D3;
        padding-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. Googleスプレッドシート連携
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # スプレッドシートから最新データを読み込み
        return conn.read(ttl="0s")
    except:
        # データがない場合の初期構造
        return pd.DataFrame([{"ID": i+1, "自治体名": "", "案件概要": "", "仕様書": False, "予算(千円)": 0, 
                              "落札金額(千円)": 0, "落札企業": "", "応札1": "", "応札2": "", "応札3": "", 
                              "NJSS掲載": False, "入札王掲載": False} for i in range(50)])

# サイドバーによるページ切り替え（ダッシュボード分離）
st.sidebar.image("https://www.salesforce.com/news/wp-content/uploads/sites/3/2021/05/Salesforce-logo.jpg", width=100)
page = st.sidebar.radio("メニュー", ["📊 ダッシュボード", "📝 検証データ入力", "🔍 検索ワード設定"])

# --- ページ3: 検索ワード設定 ---
if page == "🔍 検索ワード設定":
    st.header("Search Word Configuration")
    if 'search_words' not in st.session_state:
        st.session_state.search_words = ["DX推進", "データ分析"]
    
    with st.container():
        new_word = st.text_input("追加したい検索ワード")
        if st.button("Add Word") and new_word:
            if new_word not in st.session_state.search_words:
                st.session_state.search_words.append(new_word)
                st.rerun()
        
        st.subheader("現在のワード別ヒット件数入力")
        search_data = []
        for word in st.session_state.search_words:
            col1, col2 = st.columns(2)
            n_v = col1.number_input(f"NJSS: {word}", min_value=0, key=f"n_{word}")
            k_v = col2.number_input(f"入札王: {word}", min_value=0, key=f"k_{word}")
            search_data.append({"ワード": word, "NJSS": n_v, "入札王": k_v})
        st.session_state.search_results = pd.DataFrame(search_data)

# --- ページ2: 検証データ入力 ---
elif page == "📝 検証データ入力":
    st.header("PoC Raw Data Entry")
    df_current = load_data()
    
    st.info("💡 50件の過去案件情報を入力してください。完了後、一番下の保存ボタンを押してください。")
    
    edited_df = st.data_editor(
        df_current,
        column_config={
            "仕様書": st.column_config.CheckboxColumn("仕様書有"),
            "NJSS掲載": st.column_config.CheckboxColumn("NJSS"),
            "入札王掲載": st.column_config.CheckboxColumn("入札王"),
            "予算(千円)": st.column_config.NumberColumn(format="%d"),
            "落札金額(千円)": st.column_config.NumberColumn(format="%d"),
        },
        hide_index=True,
        num_rows="fixed",
        use_container_width=True
    )

    if st.button("☁️ スプレッドシートへ保存 (Sync to Cloud)"):
        conn.update(data=edited_df)
        st.success("Cloud Synchronization Complete.")
        st.rerun()

# --- ページ1: ダッシュボード ---
elif page == "📊 ダッシュボード":
    st.header("Executive Summary Dashboard")
    df = load_data()
    valid_df = df[df["自治体名"] != ""]
    
    if valid_df.empty:
        st.warning("データがありません。「検証データ入力」ページから入力を開始してください。")
    else:
        # KPIカード
        c1, c2, c3 = st.columns(3)
        nj_rate = (valid_df["NJSS掲載"].sum() / len(valid_df)) * 100
        ki_rate = (valid_df["入札王掲載"].sum() / len(valid_df)) * 100
        c1.metric("NJSS 網羅率", f"{nj_rate:.1f}%")
        c2.metric("入札王 網羅率", f"{ki_rate:.1f}%")
        c3.metric("検証案件数", f"{len(valid_df)}件")

        st.markdown("---")
        
        # グラフセクション
        g1, g2 = st.columns(2)
        with g1:
            # 1. 捕捉数グラフ
            fig_hits = px.bar(x=["NJSS", "入札王"], y=[valid_df["NJSS掲載"].sum(), valid_df["入札王掲載"].sum()],
                              title="案件捕捉数比較", color=["NJSS", "入札王"],
                              color_discrete_map={"NJSS": "#0176D3", "入札王": "#FFB75D"})
            st.plotly_chart(fig_hits, use_container_width=True)

        with g2:
            # 2. 金額分布
            price_df = valid_df[valid_df["落札金額(千円)"] > 0]
            if not price_df.empty:
                fig_dist = px.histogram(price_df, x="落札金額(千円)", title="落札価格帯の分布", color_discrete_sequence=['#00A1E0'])
                st.plotly_chart(fig_dist, use_container_width=True)

        # 3. 競合分析
        st.subheader("Competitor Analysis")
        all_comp = pd.concat([valid_df["落札企業"], valid_df["応札1"], valid_df["応札2"], valid_df["応札3"]])
        pres_df = all_comp[all_comp != ""].value_counts().reset_index()
        pres_df.columns = ["企業名", "出現数"]
        fig_pres = px.bar(pres_df.head(10), x="出現数", y="企業名", orientation='h', title="市場出現頻度 (落札+応札)")
        st.plotly_chart(fig_pres, use_container_width=True)
