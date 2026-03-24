import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
import io

st.set_page_config(page_title="PoC Evaluation Dashboard", layout="wide")

# (CSS部分は以前と同様のため中略。実際には全てのコードを結合してください)

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        return conn.read(ttl="0s")
    except:
        return pd.DataFrame([{"ID": i+1, "自治体名": "", "案件概要": "", "仕様書": False, "予算(千円)": 0, 
                              "落札金額(千円)": 0, "落札企業": "", "応札1": "", "応札2": "", "応札3": "", 
                              "NJSS掲載": False, "入札王掲載": False} for i in range(50)])

# サイドバー設定
st.sidebar.title("PoC Management")
page = st.sidebar.radio("Menu", ["📊 ダッシュボード", "📝 検証データ入力", "🔍 検索ワード設定", "📤 データインポート"])

# --- ページ4: データインポート（新規追加） ---
if page == "📤 データインポート":
    st.header("Bulk Data Import")
    st.write("作成したサンプルCSVをアップロードして、一括で検証データをセットします。")
    
    uploaded_file = st.file_uploader("CSVファイルをアップロードしてください", type="csv")
    
    if uploaded_file is not None:
        import_df = pd.read_csv(uploaded_file)
        st.write("プレビュー:", import_df.head())
        
        if st.button("このデータを現在の入力シートに反映する"):
            # 50件の枠に収まるように調整してセッションに保持
            st.session_state.temp_df = import_df
            st.success("反映しました。「検証データ入力」ページで内容を確認し、保存してください。")

# --- ページ2: 検証データ入力（インポート対応版） ---
elif page == "📝 検証データ入力":
    st.header("PoC Raw Data Entry")
    
    # インポートされたデータがあればそれを使用、なければスプレッドシートから読み込み
    if 'temp_df' in st.session_state:
        df_display = st.session_state.temp_df
    else:
        df_display = load_data()
    
    edited_df = st.data_editor(
        df_display,
        column_config={
            "仕様書": st.column_config.CheckboxColumn("仕様書有"),
            "NJSS掲載": st.column_config.CheckboxColumn("NJSS"),
            "入札王掲載": st.column_config.CheckboxColumn("入札王"),
        },
        hide_index=True,
        num_rows="dynamic", # インポートに合わせて行数可変
        use_container_width=True
    )

    if st.button("☁️ スプレッドシートへ一括保存"):
        conn.update(data=edited_df)
        if 'temp_df' in st.session_state:
            del st.session_state.temp_df # 保存後は一時データを削除
        st.success("Cloud Synchronization Complete.")
        st.rerun()

# (Page1, Page3 のロジックは前回同様)
