import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
import io
import csv
import traceback

# --- 1. UI & CSS (アイコン&上部白枠排除 & Salesforce風タイトル装飾) ---
st.set_page_config(page_title="入札ツール精密評価ボード", layout="wide")

st.markdown("""
    <style>
    /* 1. アイコンと上部白枠の完全排除 */
    
    /* ブラウザの標準ヘッダーバーを消去 */
    [data-testid="stHeader"] { display: none !important; }
    
    /* アプリ全体のコンテナの上部パディングをなくし、上部の隙間を完全に埋める */
    [data-testid="stAppViewContainer"] {
        padding-top: 0rem !important;
    }
    /* メインコンテンツエリアの上部パディングも調整 */
    [data-testid="block-container"] {
        padding-top: 1rem !important; /* 0にすると詰まりすぎるので1rem程度に */
    }

    /* 全体の背景と文字色 */
    [data-testid="stAppViewContainer"], .stApp { background-color: #F3F3F2 !important; color: #181818 !important; }
    
    /* サイドバー配色 (AdminLTEダーク) */
    [data-testid="stSidebar"] { background-color: #2c3b41 !important; border-right: 1px solid #1a2226 !important; }
    [data-testid="stSidebar"] * { color: #b8c7ce !important; }
    
    /* サイドバーのセクションヘッダー */
    .sidebar-section-header { color: #4b646f !important; font-size: 12px !important; font-weight: bold; padding: 10px 15px; background-color: #1a2226; margin: 20px 0px 15px 0px; }
    
    /* ラジオボタンの丸いボタンを完全に消し去る */
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label > div:first-child {
        display: none !important;
    }
    
    /* メニュー項目をテキストリンク風に (絵文字なし前提) */
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label {
        padding: 10px 15px !important;
        margin-bottom: 2px !important;
        background-color: transparent;
        transition: background-color 0.1s;
        cursor: pointer;
    }
    /* ホバー時（マウスを乗せた時）のエフェクト */
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover {
        background-color: rgba(255, 255, 255, 0.05) !important;
    }
    
    /* メニューの文字スタイル */
    [data-testid="stSidebar"] div.stRadio p { color: white !important; font-size: 15px !important; }

    /* 2. タイトルの装飾 (Salesforce Lightning風) */
    
    /* ページヘッダーのコンテナ全体 */
    .slds-page-header {
        background-color: #f7f9fb !important; /* 薄いグレーの背景 */
        padding: 1rem 1.5rem;
        border-bottom: 1px solid #d8dde6;
        margin: -1rem -4rem 1.5rem -4rem; /* コンテナからはみ出させる設定は維持 */
        display: flex;
        align-items: center;
        border-left: 6px solid #0176D3; /* 左側にブルーのアクセントバー */
    }
    
    /* タイトルテキスト */
    .slds-page-header h1 {
        color: #0176D3 !important; /* ジール社のブルー */
        font-size: 1.5rem;
        font-weight: 700;
        margin: 0;
    }

    /* その他、Salesforce風のデザイン設定は維持 */
    .slds-card { background-color: #FFFFFF !important; border: 1px solid #DDDBDA !important; border-radius: 0.5rem; padding: 2rem; box-shadow: 0 2px 2px 0 rgba(0, 0, 0, 0.1); margin-bottom: 2rem; }
    .stButton > button { background-color: #0176D3 !important; color: #FFFFFF !important; border-radius: 4px !important; font-weight: 700 !important; border: none !important; padding: 0.6rem 2rem !important; }
    .stButton > button:hover { background-color: #014486 !important; }
    [data-testid="stMetricValue"] { color: #0176D3 !important; font-weight: 700; }
    [data-testid="stMetricLabel"] p { color: #555555 !important; }
    div[data-baseweb="input"], div[data-baseweb="input"] > div, div[data-baseweb="base-input"], input { background-color: #FFFFFF !important; color: #181818 !important; border-color: #DDDBDA !important; }
    div[data-baseweb="button-group"] button { background-color: #F3F3F2 !important; color: #181818 !important; }
    [data-testid="stFileUploadDropzone"] { background-color: #FFFFFF !important; color: #181818 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- セッション状態の初期化 ---
if 'search_words' not in st.session_state:
    st.session_state.search_words = ["DX推進", "データ分析基盤"]

# --- 2. スプレッドシート接続 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        return conn.read(spreadsheet=url, ttl="0s")
    except Exception as e:
        return pd.DataFrame([{"ID": i+1, "自治体名": "", "案件概要": "", "仕様書": False, "予算(千円)": 0, 
                              "落札金額(千円)": 0, "落札企業": "", "応札1": "", "応札2": "", "応札3": "", 
                              "NJSS掲載": False, "入札王掲載": False} for i in range(50)])

# --- 3. サイドバーの構築 (アイコン削除) ---
with st.sidebar:
    st.markdown('<p class="sidebar-section-header">メインメニュー</p>', unsafe_allow_html=True)
    page = st.radio(
        "メニュー",
        ["ダッシュボード", "過去案件情報入力", "ワード検索数"],
        format_func=lambda x: {
            "ダッシュボード": "ダッシュボード",  # 絵文字「📊 」を削除
            "過去案件情報入力": "過去案件情報入力",  # 絵文字「📝 」を削除
            "ワード検索数": "ワード検索数"  # 絵文字「🔍 」を削除
        }[x],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.caption("開発: 株式会社ジール アライアンス部門")

# --- 4. コンテンツ表示 ---

if page == "ダッシュボード":
    # タイトル部分にSalesforce風ヘッダーを適用
    st.markdown('<div class="slds-page-header"><h1>PoC分析ダッシュボード</h1></div>', unsafe_allow_html=True)
    df = load_data()
    valid_df = df[df["自治体名"].notna() & (df["自治体名"] != "")]

    if valid_df.empty:
        st.info("データがありません。左のメニューから「過去案件情報入力」を開き、検証結果を登録してください。")
    else:
        st.markdown('<div class="slds-card">', unsafe_allow_html=True)
        kpi1, kpi2, kpi3 = st.columns(3)
        nj_count = valid_df["NJSS掲載"].sum()
        ki_count = valid_df["入札王掲載"].sum()
        kpi1.metric("NJSS 網羅率", f"{(nj_count/len(valid_df)*100):.1f}%")
        kpi2.metric("入札王 網羅率", f"{(ki_count/len(valid_df)*100):.1f}%")
        kpi3.metric("検証完了案件", f"{len(valid_df)} 件")
        st.markdown('</div>', unsafe_allow_html=True)

        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown('<div class="slds-card">', unsafe_allow_html=True)
            fig_hits = px.bar(x=["NJSS", "入札王"], y=[nj_count, ki_count], title="案件捕捉数の比較",
                              color=["NJSS", "入札王"], color_discrete_map={"NJSS": "#0176D3", "入札王": "#1B96FF"})
            fig_hits.update_layout(template="plotly_white", paper_bgcolor="white", plot_bgcolor="white", font=dict(color="#181818"))
            st.plotly_chart(fig_hits, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col_r:
            st.markdown('<div class="slds-card">', unsafe_allow_html=True)
            comp_df = pd.concat([valid_df["落札企業"], valid_df["応札1"], valid_df["応札2"], valid_df["応札3"]])
            pres_df = comp_df[comp_df != ""].value_counts().reset_index()
            pres_df.columns = ["企業名", "出現回数"]
            fig_p = px.bar(pres_df.head(8), x="出現回数", y="企業名", orientation='h', title="競合出現シェア (TOP 8)")
            fig_p.update_layout(template="plotly_white", paper_bgcolor="white", plot_bgcolor="white", font=dict(color="#181818"))
            st.plotly_chart(fig_p, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

elif page == "過去案件情報入力":
    st.markdown('<div class="slds-page-header"><h1>過去案件情報入力</h1></div>', unsafe_allow_html=True)
    st.markdown('<div class="slds-card">', unsafe_allow_html=True)
    df_display = st.session_state.get('temp_df', load_data())
    
    edited_df = st.data_editor(
        df_display,
        column_config={
            "仕様書": st.column_config.CheckboxColumn("仕様書有"),
            "NJSS掲載": st.column_config.CheckboxColumn("NJSS確認"),
            "入札王掲載": st.column_config.CheckboxColumn("入札王確認"),
            "予算(千円)": st.column_config.NumberColumn(format="¥%d"),
            "落札金額(千円)": st.column_config.NumberColumn(format="¥%d"),
        },
        hide_index=True, num_rows="dynamic", use_container_width=True
    )
    
    if st.button("☁️ クラウドへ一括保存 (スプレッドシート連携)"):
        try:
            url = st.secrets["connections"]["gsheets"]["spreadsheet"]
            conn.update(spreadsheet=url, data=edited_df)
            if 'temp_df' in st.session_state:
                del st.session_state.temp_df
            st.success("スプレッドシートへの保存が完了しました。")
            st.rerun()
        except Exception as e:
            st.error(f"保存に失敗しました。詳細エラー: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

elif page == "ワード検索数":
    st.markdown('<div class="slds-page-header"><h1>ワード検索数設定</h1></div>', unsafe_allow_html=True)
    st.markdown('<div class="slds-card">', unsafe_allow_html=True)
    col_add1, col_add2 = st.columns([3, 1])
    new_word = col_add1.text_input("追加したい検索ワード", placeholder="BIツール、AI活用", label_visibility="collapsed")
    if col_add2.button("ワードを追加"):
        if new_word and new_word not in st.session_state.search_words:
            st.session_state.search_words.append(new_word)
            st.rerun()
            
    if st.button("ワードリストをリセット"):
        st.session_state.search_words = []
        st.rerun()

    search_data = []
    if st.session_state.search_words:
        st.markdown("##### ヒット件数の実測値入力")
        for word in st.session_state.search_words:
            col_w1, col_w2 = st.columns(2)
            n_val = col_w1.number_input(f"NJSS: 【 {word} 】", min_value=0, key=f"n_{word}")
            k_val = col_w2.number_input(f"入札王: 【 {word} 】", min_value=0, key=f"k_{word}")
            n_j = "○" if n_val >= k_val and n_val > 0 else "×"
            k_j = "○" if k_val >= n_val and k_val > 0 else "×"
            search_data.append({"検索ワード": word, "NJSS件数": n_val, "NJSS判定": n_j, "入札王件数": k_val, "入札王判定": k_j})
        
        st.table(pd.DataFrame(search_data))
        
        df_sw = pd.DataFrame(search_data)
        fig_sw = px.bar(df_sw, x="検索ワード", y=["NJSS件数", "入札王件数"], barmode="group", title="ワード別 ヒット件数比較")
        fig_sw.update_layout(template="plotly_white", paper_bgcolor="white", plot_bgcolor="white", font=dict(color="#181818"))
        st.plotly_chart(fig_sw, use_container_width=True)
    else:
        st.info("検索ワードを追加してください。")
    st.markdown('</div>', unsafe_allow_html=True)
