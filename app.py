import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# --- 1. Salesforce Lightning UI 徹底再現 CSS ---
st.set_page_config(page_title="PoC Evaluation | Salesforce Edition", layout="wide")

st.markdown("""
    <style>
    /* 全体のフォントと背景 */
    @import url('https://fonts.googleapis.com/css2?family=Salesforce+Sans:wght@300;400;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Salesforce Sans', sans-serif;
        color: #181818;
    }
    .stApp {
        background-color: #F3F3F2;
    }

    /* サイドバーの完全刷新 */
    [data-testid="stSidebar"] {
        background-color: white !important;
        border-right: 1px solid #D8DDE6;
    }
    [data-testid="stSidebar"] .stRadio > label {
        color: #080707 !important;
        font-weight: 600;
    }
    /* サイドバーの文字を黒く */
    [data-testid="stSidebarNav"] li a span {
        color: #080707 !important;
    }
    /* ラジオボタンのラベル色 */
    div[data-testid="stWidgetLabel"] p {
        color: #080707 !important;
        font-size: 1.1rem;
    }

    /* メインヘッダー */
    .slds-page-header {
        background-color: white;
        padding: 1.5rem 2rem;
        border-bottom: 2px solid #D8DDE6;
        margin: -4rem -4rem 2rem -4rem;
        display: flex;
        align-items: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .slds-page-header h1 {
        color: #080707;
        font-size: 1.5rem;
        font-weight: 700;
        margin: 0;
    }

    /* Salesforceカード */
    .slds-card {
        background-color: white;
        border: 1px solid #DDDBDA;
        border-radius: 0.5rem;
        padding: 2rem;
        box-shadow: 0 2px 2px 0 rgba(0, 0, 0, 0.1);
        margin-bottom: 2rem;
    }

    /* ボタン */
    .stButton > button {
        background-color: #0176D3 !important;
        color: white !important;
        border-radius: 4px !important;
        font-weight: 700 !important;
        border: none !important;
        padding: 0.6rem 2rem !important;
    }
    
    /* メトリック（数字） */
    [data-testid="stMetricValue"] {
        color: #0176D3 !important;
        font-weight: 700;
    }
    [data-testid="stMetricLabel"] p {
        color: #444444 !important;
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

# --- 3. サイドバー・ナビゲーション（アイコンと文字色改善） ---
with st.sidebar:
    st.image("https://www.salesforce.com/news/wp-content/uploads/sites/3/2021/05/Salesforce-logo.jpg", width=140)
    st.write("")
    # アイコンをビジネスライクな表現に変更
    page = st.radio(
        "Navigation Menu",
        ["Analytics Dashboard", "Data Entry Sheet", "Evaluation Settings", "Bulk Data Import"],
        format_func=lambda x: {
            "Analytics Dashboard": "📊  Dashboard",
            "Data Entry Sheet": "📝  Records",
            "Evaluation Settings": "⚙️  Settings",
            "Bulk Data Import": "📥  Import"
        }[x]
    )
    st.markdown("---")
    st.caption("Developed for Zeeal Inc. Alliances")

# --- 4. コンテンツ表示 ---

if page == "Analytics Dashboard":
    st.markdown('<div class="slds-page-header"><h1>📊 Executive Insights Dashboard</h1></div>', unsafe_allow_html=True)
    df = load_data()
    valid_df = df[df["自治体名"].notna() & (df["自治体名"] != "")]

    if valid_df.empty:
        st.info("No data entries found. Please record evaluation results in 'Data Entry Sheet'.")
    else:
        st.markdown('<div class="slds-card">', unsafe_allow_html=True)
        kpi1, kpi2, kpi3 = st.columns(3)
        nj_count = valid_df["NJSS掲載"].sum()
        ki_count = valid_df["入札王掲載"].sum()
        kpi1.metric("NJSS Coverage", f"{(nj_count/len(valid_df)*100):.1f}%")
        kpi2.metric("入札王 Coverage", f"{(ki_count/len(valid_df)*100):.1f}%")
        kpi3.metric("Total Cases", f"{len(valid_df)} Units")
        st.markdown('</div>', unsafe_allow_html=True)

        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown('<div class="slds-card">', unsafe_allow_html=True)
            fig_hits = px.bar(x=["NJSS", "入札王"], y=[nj_count, ki_count], title="Hit Comparison",
                              color=["NJSS", "入札王"], color_discrete_map={"NJSS": "#0176D3", "入札王": "#1B96FF"})
            st.plotly_chart(fig_hits, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with col_r:
            st.markdown('<div class="slds-card">', unsafe_allow_html=True)
            comp_df = pd.concat([valid_df["落札企業"], valid_df["応札1"], valid_df["応札2"], valid_df["応札3"]])
            pres_df = comp_df[comp_df != ""].value_counts().reset_index()
            pres_df.columns = ["Company", "Presence"]
            fig_p = px.bar(pres_df.head(8), x="Presence", y="Company", orientation='h', title="Top Competitors")
            st.plotly_chart(fig_p, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

elif page == "Data Entry Sheet":
    st.markdown('<div class="slds-page-header"><h1>📝 PoC Evaluation Records</h1></div>', unsafe_allow_html=True)
    st.markdown('<div class="slds-card">', unsafe_allow_html=True)
    df_display = st.session_state.get('temp_df', load_data())
    
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
    
    if st.button("☁️ Save to Salesforce Cloud (GS)"):
        try:
            url = st.secrets["connections"]["gsheets"]["spreadsheet"]
            conn.update(spreadsheet=url, data=edited_df, worksheet="Sheet1")
            st.success("Data successfully synchronized.")
        except Exception as e:
            st.error(f"Synchronization failed: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

# (Importページ等も同様のカードデザインを適用)
