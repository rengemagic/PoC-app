import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# 1. ページ設定とSalesforce風デザイン
st.set_page_config(page_title="PoC Evaluation Dashboard", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f3f3f2; }
    .stButton>button { background-color: #0176D3; color: white; border-radius: 4px; border: none; }
    div[data-testid="stExpander"] { background-color: white; border: 1px solid #dddbda; border-radius: .25rem; }
    h1 { color: #1b1b1b; border-bottom: 2px solid #0176D3; padding-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 2. Googleスプレッドシート連携（接続の明示）
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # 💡 SecretsからURLを直接参照して読み込み
        target_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        return conn.read(spreadsheet=target_url, ttl="0s")
    except Exception as e:
        # データがない、または初回接続時の初期構造
        return pd.DataFrame([{"ID": i+1, "自治体名": "", "案件概要": "", "仕様書": False, "予算(千円)": 0, 
                              "落札金額(千円)": 0, "落札企業": "", "応札1": "", "応札2": "", "応札3": "", 
                              "NJSS掲載": False, "入札王掲載": False} for i in range(50)])

# サイドバー設定
st.sidebar.title("PoC Management")
page = st.sidebar.radio("Menu", ["📊 ダッシュボード", "📝 検証データ入力", "🔍 検索ワード設定", "📤 データインポート"])

# --- ページ2: 検証データ入力 ---
if page == "📝 検証データ入力":
    st.header("PoC Raw Data Entry")
    
    # インポートされた一時データがあればそれを使用
    df_display = st.session_state.get('temp_df', load_data())
    
    edited_df = st.data_editor(
        df_display,
        column_config={
            "仕様書": st.column_config.CheckboxColumn("仕様書有"),
            "NJSS掲載": st.column_config.CheckboxColumn("NJSS"),
            "入札王掲載": st.column_config.CheckboxColumn("入札王"),
        },
        hide_index=True,
        num_rows="dynamic",
        use_container_width=True
    )

    if st.button("☁️ スプレッドシートへ一括保存"):
        try:
            target_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
            conn.update(spreadsheet=target_url, data=edited_df)
            if 'temp_df' in st.session_state:
                del st.session_state.temp_df
            st.success("Cloud Synchronization Complete.")
            st.rerun()
        except Exception as e:
            st.error(f"保存に失敗しました。共有設定を確認してください: {e}")

# --- ページ4: データインポート ---
elif page == "📤 データインポート":
    st.header("Bulk Data Import")
    uploaded_file = st.file_uploader("CSVアップロード", type="csv")
    if uploaded_file:
        import_df = pd.read_csv(uploaded_file)
        if st.button("このデータを反映する"):
            st.session_state.temp_df = import_df
            st.success("反映しました。「検証データ入力」ページで保存してください。")

# --- ページ1: ダッシュボード（分析） ---
elif page == "📊 ダッシュボード":
    st.header("Executive Summary Dashboard")
    df = load_data()
    valid_df = df[df["自治体名"].notna() & (df["自治体名"] != "")]
    
    if valid_df.empty:
        st.warning("データがありません。入力を開始してください。")
    else:
        # KPI・グラフ表示（前回のロジック通り）
        c1, c2, c3 = st.columns(3)
        c1.metric("NJSS 網羅率", f"{(valid_df['NJSS掲載'].sum()/len(valid_df)*100):.1f}%")
        c2.metric("入札王 網羅率", f"{(valid_df['入札王掲載'].sum()/len(valid_df)*100):.1f}%")
        c3.metric("検証案件数", f"{len(valid_df)}件")

        g1, g2 = st.columns(2)
        with g1:
            fig = px.bar(x=["NJSS", "入札王"], y=[valid_df["NJSS掲載"].sum(), valid_df["入札王掲載"].sum()],
                         title="案件捕捉数比較", color=["NJSS", "入札王"],
                         color_discrete_map={"NJSS": "#0176D3", "入札王": "#FFB75D"})
            st.plotly_chart(fig, use_container_width=True)
        with g2:
            comp_df = pd.concat([valid_df["落札企業"], valid_df["応札1"], valid_df["応札2"], valid_df["応札3"]])
            pres_df = comp_df[comp_df != ""].value_counts().reset_index()
            pres_df.columns = ["企業名", "出現数"]
            fig_p = px.bar(pres_df.head(10), x="出現数", y="企業名", orientation='h', title="市場出現頻度")
            st.plotly_chart(fig_p, use_container_width=True)

# --- ページ3: 検索ワード設定 ---
elif page == "🔍 検索ワード設定":
    st.header("Search Word Configuration")
    # 検索ワードの管理ロジック（中略）
