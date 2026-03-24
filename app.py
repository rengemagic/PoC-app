import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
import io
import csv
import traceback

# --- 1. UI & CSS (AdminLTE風ダークサイドバー & ダークモード強制リセット) ---
st.set_page_config(page_title="入札ツール精密評価ボード", layout="wide")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"], .stApp { background-color: #F3F3F2 !important; color: #181818 !important; }
    [data-testid="stSidebar"] { background-color: #2c3b41 !important; border-right: 1px solid #1a2226 !important; }
    [data-testid="stSidebar"] * { color: #b8c7ce !important; }
    .sidebar-section-header { color: #4b646f !important; font-size: 12px !important; font-weight: bold; padding: 10px 15px; background-color: #1a2226; margin: 20px 0px 15px 0px; }
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label { margin-bottom: 1.5rem !important; color: white !important; font-size: 15px !important; cursor: pointer; }
    [data-testid="stSidebar"] div.stRadio p { color: white !important; font-size: 15px !important; }
    
    /* ページヘッダー */
    .slds-page-header { background-color: #FFFFFF !important; padding: 1.5rem 2rem; border-bottom: 2px solid #D8DDE6; margin: -4rem -4rem 2rem -4rem; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .slds-page-header h1 { color: #080707 !important; font-size: 1.6rem; font-weight: 700; margin: 0; }
    
    /* ボタン */
    .stButton > button { background-color: #0176D3 !important; color: #FFFFFF !important; border-radius: 4px !important; font-weight: 700 !important; border: none !important; padding: 0.6rem 2rem !important; }
    .stButton > button:hover { background-color: #014486 !important; }
    
    /* 入力ボックス・ファイルアップローダーの背景白化 */
    div[data-baseweb="input"], div[data-baseweb="input"] > div, div[data-baseweb="base-input"], input { background-color: #FFFFFF !important; color: #181818 !important; border-color: #DDDBDA !important; }
    div[data-baseweb="button-group"] button { background-color: #F3F3F2 !important; color: #181818 !important; }
    [data-testid="stFileUploadDropzone"] { background-color: #FFFFFF !important; color: #181818 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- セッション状態の初期化 ---
if 'search_words' not in st.session_state:
    st.session_state.search_words = ["DX推進", "データ分析基盤"]
if 'search_counts' not in st.session_state:
    st.session_state.search_counts = {}

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

# --- 3. サイドバーの構築 ---
with st.sidebar:
    st.markdown('<p class="sidebar-section-header">メインメニュー</p>', unsafe_allow_html=True)
    
    test_mode = st.toggle("🧪 テストモード (インポート表示)")
    
    menu_options = ["ダッシュボード", "実測データ入力", "ワード検索数", "マニュアル"]
    if test_mode:
        menu_options.append("データ一括インポート")

    page = st.radio(
        "メニュー",
        menu_options,
        format_func=lambda x: {
            "ダッシュボード": "📊  ダッシュボード",
            "実測データ入力": "📝  実測データ入力",
            "ワード検索数": "🔍  ワード検索数",
            "マニュアル": "📖  マニュアル",
            "データ一括インポート": "📥  データ一括インポート"
        }[x],
        label_visibility="collapsed"
    )

# --- カスタムKPIカードを描画する関数 ---
def draw_kpi_card(title, value):
    st.markdown(f"""
        <div style="background-color: #FFFFFF; border: 1px solid #DDDBDA; border-radius: 0.5rem; padding: 1.5rem; text-align: center; box-shadow: 0 2px 2px 0 rgba(0,0,0,0.1); margin-bottom: 2rem;">
            <p style="color: #555555; font-size: 14px; font-weight: bold; margin: 0 0 10px 0;">{title}</p>
            <p style="color: #0176D3; font-size: 36px; font-weight: bold; margin: 0;">{value}</p>
        </div>
    """, unsafe_allow_html=True)

# --- 4. コンテンツ表示 ---

if page == "ダッシュボード":
    st.markdown('<div class="slds-page-header"><h1>📊 PoC分析ダッシュボード</h1></div>', unsafe_allow_html=True)
    st.info("💡 以下のダッシュボードは、入力された実測データに基づきリアルタイムに更新されます。")
    
    df = load_data()
    valid_df = df[df["自治体名"].notna() & (df["自治体名"] != "")]

    if valid_df.empty:
        st.warning("データがありません。左のメニューから「実測データ入力」を開き、検証結果を登録してください。")
    else:
        # KPIカード（大型化・枠線あり）
        kpi1, kpi2, kpi3 = st.columns(3)
        nj_count = valid_df["NJSS掲載"].astype(str).str.upper().isin(["TRUE", "1", "1.0", "YES"]).sum()
        ki_count = valid_df["入札王掲載"].astype(str).str.upper().isin(["TRUE", "1", "1.0", "YES"]).sum()
        
        with kpi1: draw_kpi_card("NJSS 網羅率", f"{(nj_count/len(valid_df)*100):.1f}%")
        with kpi2: draw_kpi_card("入札王 網羅率", f"{(ki_count/len(valid_df)*100):.1f}%")
        with kpi3: draw_kpi_card("検証完了案件", f"{len(valid_df)} 件")

        # グラフ用共通レイアウト設定
        chart_layout = dict(
            template="plotly_white", paper_bgcolor="white", plot_bgcolor="white", 
            font=dict(color="#181818"), margin=dict(l=20, r=20, t=50, b=20)
        )
        
        # 配色設定（NJSS: 青, 入札王: オレンジ）
        color_map = {"NJSS": "#0176D3", "入札王": "#F28E2B", "NJSS件数": "#0176D3", "入札王件数": "#F28E2B"}

        # 上段：案件捕捉数 ＆ 競合シェア
        col_l, col_r = st.columns(2)
        with col_l:
            fig_hits = px.bar(x=["NJSS", "入札王"], y=[nj_count, ki_count], title="案件捕捉数の比較",
                              color=["NJSS", "入札王"], color_discrete_map=color_map)
            fig_hits.update_layout(**chart_layout)
            st.plotly_chart(fig_hits, use_container_width=True)
            
        with col_r:
            comp_df = pd.concat([valid_df["落札企業"], valid_df["応札1"], valid_df["応札2"], valid_df["応札3"]])
            pres_df = comp_df[comp_df != ""].value_counts().reset_index()
            pres_df.columns = ["企業名", "出現回数"]
            fig_p = px.bar(pres_df.head(8), x="出現回数", y="企業名", orientation='h', title="競合出現シェア (TOP 8)")
            fig_p.update_traces(marker_color='#0176D3') # 単一色は青に統一
            fig_p.update_layout(**chart_layout)
            st.plotly_chart(fig_p, use_container_width=True)

        # 下段：ワード検索数のグラフ
        if st.session_state.search_words:
            dash_search_data = []
            for word in st.session_state.search_words:
                counts = st.session_state.search_counts.get(word, {"NJSS": 0, "入札王": 0})
                dash_search_data.append({"検索ワード": word, "NJSS件数": counts["NJSS"], "入札王件数": counts["入札王"]})
            
            df_dash_sw = pd.DataFrame(dash_search_data)
            fig_dash_sw = px.bar(df_dash_sw, x="検索ワード", y=["NJSS件数", "入札王件数"], barmode="group", title="ワード別 ヒット件数比較",
                                 color_discrete_map=color_map)
            fig_dash_sw.update_layout(**chart_layout)
            st.plotly_chart(fig_dash_sw, use_container_width=True)

elif page == "実測データ入力":
    st.markdown('<div class="slds-page-header"><h1>📝 PoC 実測データ入力</h1></div>', unsafe_allow_html=True)
    st.info("💡 表のセルを直接クリックしてデータを入力・修正してください。編集後は必ず左下の「クラウドへ一括保存」ボタンを押してください。")
    
    df_display = st.session_state.get('temp_df', load_data())
    
    if not df_display.empty:
        bool_columns = ["仕様書", "NJSS掲載", "入札王掲載"]
        for col in bool_columns:
            if col in df_display.columns:
                df_display[col] = df_display[col].astype(str).str.strip().str.upper().map({'TRUE': True, '1': True, '1.0': True, 'YES': True}).fillna(False)
        
        num_columns = ["予算(千円)", "落札金額(千円)"]
        for col in num_columns:
            if col in df_display.columns:
                df_display[col] = pd.to_numeric(df_display[col].astype(str).str.replace(r'[¥,]', '', regex=True), errors='coerce').fillna(0).astype(int)

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
            clean_df = edited_df.fillna("")
            clean_df = clean_df.replace({None: ""})
            conn.update(spreadsheet=url, data=clean_df)
            
            if 'temp_df' in st.session_state:
                del st.session_state.temp_df
            st.success("スプレッドシートへの保存が完了しました！")
            st.rerun()
        except Exception as e:
            st.error(f"保存に失敗しました。詳細エラー:\n```\n{traceback.format_exc()}\n```")

elif page == "ワード検索数":
    st.markdown('<div class="slds-page-header"><h1>🔍 ワード検索数 実測入力</h1></div>', unsafe_allow_html=True)
    st.info("💡 比較したい検索ワードを追加し、それぞれのツールでのヒット件数を入力してください。（ダッシュボードに自動反映されます）")
    
    col_add1, col_add2 = st.columns([3, 1])
    new_word = col_add1.text_input("追加したい検索ワード", placeholder="例：BIツール、AI活用", key="input_new_word", label_visibility="collapsed")
    if col_add2.button("ワードを追加", use_container_width=True):
        if new_word and new_word not in st.session_state.search_words:
            st.session_state.search_words.append(new_word)
            st.rerun()
            
    if st.button("ワードリストをリセット"):
        st.session_state.search_words = []
        st.session_state.search_counts = {}
        st.rerun()

    if st.session_state.search_words:
        st.markdown("##### ヒット件数の実測値入力")
        search_data = []
        for word in st.session_state.search_words:
            if word not in st.session_state.search_counts:
                st.session_state.search_counts[word] = {"NJSS": 0, "入札王": 0}
            
            col_w1, col_w2 = st.columns(2)
            n_val = col_w1.number_input(f"NJSS: 【 {word} 】", min_value=0, value=st.session_state.search_counts[word]["NJSS"], key=f"n_{word}")
            k_val = col_w2.number_input(f"入札王: 【 {word} 】", min_value=0, value=st.session_state.search_counts[word]["入札王"], key=f"k_{word}")
            
            st.session_state.search_counts[word]["NJSS"] = n_val
            st.session_state.search_counts[word]["入札王"] = k_val

            n_j = "○" if n_val >= k_val and n_val > 0 else "×"
            k_j = "○" if k_val >= n_val and k_val > 0 else "×"
            search_data.append({"検索ワード": word, "NJSS件数": n_val, "NJSS判定": n_j, "入札王件数": k_val, "入札王判定": k_j})
        
        st.table(pd.DataFrame(search_data))
        
        color_map = {"NJSS件数": "#0176D3", "入札王件数": "#F28E2B"}
        df_sw = pd.DataFrame(search_data)
        fig_sw = px.bar(df_sw, x="検索ワード", y=["NJSS件数", "入札王件数"], barmode="group", title="ワード別 ヒット件数比較", color_discrete_map=color_map)
        fig_sw.update_layout(template="plotly_white", paper_bgcolor="white", plot_bgcolor="white", font=dict(color="#181818"), margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig_sw, use_container_width=True)

elif page == "マニュアル":
    st.markdown('<div class="slds-page-header"><h1>📖 操作マニュアル</h1></div>', unsafe_allow_html=True)
    
    st.markdown("""
    ### 1. 本ツールの目的
    本ツールは、入札情報サービス（NJSS、入札王など）の導入検討に向けたPoC（概念実証）において、**各ツールの網羅率や検索精度を定量的に比較・評価**するための専用ダッシュボードです。

    ### 2. 各メニューの利用方法
    
    #### 📊 ダッシュボード
    * 入力されたデータをもとに、各ツールの「網羅率（カバー率）」「競合他社の出現シェア」「ワード検索数の比較」をリアルタイムにグラフ化します。
    * 会議やプレゼン時の報告用画面としてご活用ください。

    #### 📝 実測データ入力
    * Excelのような表形式で、実際の案件データや検証結果を直接入力・編集できる画面です。
    * **【重要】** データを編集した後は、必ず表の下にある **「☁️ クラウドへ一括保存」** ボタンをクリックしてください。保存しないとダッシュボードに反映されません。
    * 一番下の行をクリックすると新しい行が追加され、案件を増やすことができます。

    #### 🔍 ワード検索数
    * 「DX」「AI」などの特定のキーワードで検索した際、各ツールで何件ヒットするかを比較する画面です。
    * ワードを追加し、実測した数値を入力すると、自動でダッシュボードのグラフに連携されます。

    #### 🧪 テストモードとデータインポート
    * サイドバーの「テストモード」をONにすると、「データ一括インポート」メニューが出現します。
    * Excel等で作成したCSVファイルをアップロードすることで、一括でデータを流し込むことができます（初期データの登録などに便利です）。
    """)

elif page == "データ一括インポート":
    st.markdown('<div class="slds-page-header"><h1>📥 データ一括インポート (テスト環境用)</h1></div>', unsafe_allow_html=True)
    st.warning("💡 このメニューは「テストモード」が有効な場合のみ表示されます。不要になったらサイドバーのスイッチをOFFにしてください。")
    uploaded_file = st.file_uploader("テスト用CSVファイルをアップロードしてください", type="csv")
    if uploaded_file:
        try:
            try:
                import_df = pd.read_csv(uploaded_file, encoding="utf-8")
            except UnicodeDecodeError:
                uploaded_file.seek(0)
                import_df = pd.read_csv(uploaded_file, encoding="shift-jis")

            if len(import_df.columns) == 1 and "," in import_df.columns[0]:
                uploaded_file.seek(0)
                try:
                    import_df = pd.read_csv(uploaded_file, encoding="utf-8", quoting=csv.QUOTE_NONE)
                except UnicodeDecodeError:
                    uploaded_file.seek(0)
                    import_df = pd.read_csv(uploaded_file, encoding="shift-jis", quoting=csv.QUOTE_NONE)
                import_df.columns = import_df.columns.str.replace('"', '', regex=False)
                import_df = import_df.replace('"', '', regex=True)

            st.dataframe(import_df.head())
            
            if st.button("このデータを入力シートに反映する"):
                st.session_state.temp_df = import_df
                st.success("反映しました。「実測データ入力」画面に移動して保存してください。")
        except Exception as e:
            st.error(f"CSVの読み込みに失敗しました: {e}")
