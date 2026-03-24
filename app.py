import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# --- 1. Salesforce Lightning Design System 風 CSS ---
st.set_page_config(page_title="PoC Insights | Salesforce Style", layout="wide")

st.markdown("""
    <style>
    /* 全体の背景色 */
    .stApp {
        background-color: #F3F3F2;
    }
    
    /* ヘッダー部分 */
    .main-header {
        background-color: white;
        padding: 1rem 2rem;
        border-bottom: 2px solid #D8DDE6;
        margin-bottom: 2rem;
        display: flex;
        align-items: center;
    }
    
    /* カード（コンテナ）のデザイン */
    div[data-testid="stVerticalBlock"] > div.element-container {
        background-color: white;
        padding: 0px;
    }
    
    /* 各セクションを白いカードにする */
    .slds-card {
        background-color: white;
        border: 1px solid #DDDBDA;
        border-radius: 0.25rem;
        padding: 1.5rem;
        box-shadow: 0 2px 2px 0 rgba(0, 0, 0, 0.1);
        margin-bottom: 1.5rem;
    }
    
    /* ボタンをSalesforce Blueに */
    .stButton > button {
        background-color: #0176D3 !important;
        color: white !important;
        border-radius: 4px !important;
        border: none !important;
        font-weight: 600 !important;
        padding: 0.5rem 1.5rem !important;
        transition: background-color 0.2s;
    }
    
    .stButton > button:hover {
        background-color: #014486 !important;
    }

    /* サイドバーのカスタマイズ */
    [data-testid="stSidebar"] {
        background-color: #032D60;
        color: white;
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    
    /* メトリック（KPI）の数字の色 */
    [data-testid="stMetricValue"] {
        color: #0176D3;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. スプレッドシート接続 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        return conn.read(spreadsheet=url, ttl="0s")
    except:
        return pd.DataFrame([{"ID": i+1, "自治体名": "", "案件概要": "", "仕様書": False, "予算(千円)": 0, 
                              "落札金額(千円)": 0, "落札企業": "", "応札1": "", "応札2": "", "応札3": "", 
                              "NJSS掲載": False, "入札王掲載": False} for i in range(50)])

# --- 3. サイドバー・ナビゲーション ---
with st.sidebar:
    st.image("https://www.salesforce.com/news/wp-content/uploads/sites/3/2021/05/Salesforce-logo.jpg", width=120)
    st.markdown("### PoC Management Center")
    page = st.radio("Navigation", ["📊 Dashboard", "📝 Data Entry", "🔍 Settings", "📤 Import"])
    st.markdown("---")
    st.caption("v2.0 | Zeeal Inc. Alliances")

# --- 4. メインコンテンツ表示 ---

# --- 📊 Dashboard ページ ---
if page == "📊 Dashboard":
    st.markdown('<div class="main-header"><h1>📊 Executive Insights Dashboard</h1></div>', unsafe_allow_html=True)
    df = load_data()
    valid_df = df[df["自治体名"].notna() & (df["自治体名"] != "")]

    if valid_df.empty:
        st.warning("No data found. Please go to 'Data Entry' to start.")
    else:
        # KPIエリア
        st.markdown("### Key Performance Indicators")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        nj_rate = (valid_df["NJSS掲載"].sum()/len(valid_df)*100)
        ki_rate = (valid_df["入札王掲載"].sum()/len(valid_df)*100)
        
        with kpi1: st.metric("NJSS Coverage", f"{nj_rate:.1f}%")
        with kpi2: st.metric("入札王 Coverage", f"{ki_rate:.1f}%")
        with kpi3: st.metric("Validated Cases", f"{len(valid_df)} units")
        with kpi4: st.metric("Avg. Budget", f"¥{valid_df['予算(千円)'].mean():,.0f}k")

        # グラフエリアをカード化
        st.markdown("---")
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown('<div class="slds-card">', unsafe_allow_html=True)
            fig_hits = px.bar(x=["NJSS", "入札王"], y=[valid_df["NJSS掲載"].sum(), valid_df["入札王掲載"].sum()],
                              title="Search Hit Comparison", color=["NJSS", "入札王"],
                              color_discrete_map={"NJSS": "#0176D3", "入札王": "#1B96FF"})
            st.plotly_chart(fig_hits, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with col_right:
            st.markdown('<div class="slds-card">', unsafe_allow_html=True)
            comp_df = pd.concat([valid_df["落札企業"], valid_df["応札1"], valid_df["応札2"], valid_df["応札3"]])
            pres_df = comp_df[comp_df != ""].value_counts().reset_index()
            pres_df.columns = ["Company", "Presence"]
            fig_p = px.bar(pres_df.head(8), x="Presence", y="Company", orientation='h', title="Market Presence (TOP 8)")
            st.plotly_chart(fig_p, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

# --- 📝 Data Entry ページ ---
elif page == "📝 Data Entry":
    st.markdown('<div class="main-header"><h1>📝 PoC Record Entry</h1></div>', unsafe_allow_html=True)
    df_display = st.session_state.get('temp_df', load_data())
    
    st.markdown('<div class="slds-card">', unsafe_allow_html=True)
    edited_df = st.data_editor(
        df_display,
        column_config={
            "仕様書": st.column_config.CheckboxColumn("Spec"),
            "NJSS掲載": st.column_config.CheckboxColumn("NJSS"),
            "入札王掲載": st.column_config.CheckboxColumn("King"),
            "予算(千円)": st.column_config.NumberColumn(format="¥%d"),
            "落札金額(千円)": st.column_config.NumberColumn(format="¥%d"),
        },
        hide_index=True, num_rows="dynamic", use_container_width=True
    )
    
    if st.button("☁️ Sync to Google Sheets"):
        try:
            url = st.secrets["connections"]["gsheets"]["spreadsheet"]
            # シート名を明示（お使いのシート名に合わせて修正してください）
            conn.update(spreadsheet=url, data=edited_df, worksheet="Sheet1")
            st.success("Successfully synchronized with Cloud Database.")
        except Exception as e:
            st.error(f"Sync failed: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

# --- 📤 Import ページ ---
elif page == "📤 Import":
    st.markdown('<div class="main-header"><h1>📤 Bulk Data Import</h1></div>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="slds-card">', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Upload CSV for evaluation", type="csv")
        if uploaded_file:
            import_df = pd.read_csv(uploaded_file)
            st.dataframe(import_df.head())
            if st.button("Commit to Entry Form"):
                st.session_state.temp_df = import_df
                st.success("Imported to local session. Please check 'Data Entry' page.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- 🔍 Settings ページ ---
elif page == "🔍 Settings":
    st.markdown('<div class="main-header"><h1>🔍 Evaluation Settings</h1></div>', unsafe_allow_html=True)
    # 機能チェックリストなどをカード内に配置
    st.markdown('<div class="slds-card">', unsafe_allow_html=True)
    st.write("Feature Checklist & Weighted Scoring (Under Construction)")
    st.markdown('</div>', unsafe_allow_html=True)
