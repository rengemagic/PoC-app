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
    .sidebar-user-panel { padding: 10px; display: flex; align-items: center; border-bottom: 1px solid #374850; margin-bottom: 10px; }
    .sidebar-user-name { font-weight: 600; color: white !important; margin-bottom: 0px !important; }
    .sidebar-user-status { color: #3c763d !important; font-size: 12px; margin-top: 0px !important; }
    .sidebar-search-box { padding: 0px 10px 10px 10px; }
    .sidebar-section-header { color: #4b646f !important; font-size: 12px !important; font-weight: bold; padding: 10px 15px; background-color: #1a2226; margin: 20px 0px 15px 0px; }
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label { margin-bottom: 1.5rem !important; color: white !important; font-size: 15px !important; cursor: pointer; }
    [data-testid="stSidebar"] div.stRadio p { color: white !important; font-size: 15px !important; }
    .slds-page-header { background-color: #FFFFFF !important; padding: 1.5rem 2rem; border-bottom: 2px solid #D8DDE6; margin: -4rem -4rem 2rem -4rem; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .slds-page-header h1 { color: #080707 !important; font-size: 1.6rem; font-weight: 700; margin: 0; }
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

# --- 3. サイドバーの構築 (日本語化) ---
with st.sidebar:
    st.markdown('<p class="sidebar-section-header">メインメニュー</p>', unsafe_allow_html=True)
    page = st.radio(
        "メニュー",
        ["ダッシュボード", "実測データ入力", "機能・評価設定", "データ一括インポート"],
        format_func=lambda x: {
            "ダッシュボード": "📊  ダッシュボード",
            "実測データ入力": "📝  実測データ入力",
            "機能・評価設定": "⚙️  機能・評価設定",
            "データ一括インポート": "📥  データ一括インポート"
        }[x],
        label_visibility="collapsed"
    )

    st.markdown('<p class="sidebar-section-header">ステータスラベル</p>', unsafe_allow_html=True)
    st.markdown('⭕ <span style="color: #dd4b39; font-weight: bold; font-size: 14px;">重要案件</span>', unsafe_allow_html=True)
    st.markdown('⭕ <span style="color: #f39c12; font-size: 14px;">確認待ち</span>', unsafe_allow_html=True)
    st.markdown('⭕ <span style="color: #00a65a; font-size: 14px;">検証完了</span>', unsafe_allow_html=True)

    st.markdown("---")
    st.caption("開発: 株式会社ジール アライアンス部門")

# --- 4. コンテンツ表示 ---

if page == "ダッシュボード":
    st.markdown('<div class="slds-page-header"><h1>📊 PoC分析ダッシュボード</h1></div>', unsafe_allow_html=True)
    df = load_data()
    valid_df = df[df["自治体名"].notna() & (df["自治体名"] != "")]

    if valid_df.empty:
        st.info("データがありません。左のメニューから「実測データ入力」を開き、検証結果を登録してください。")
    else:
        st.markdown('<div class="slds-card">', unsafe_allow_html=True)
        kpi1, kpi2, kpi3 = st.columns(3)
        
        # 文字列として認識されている可能性があるため、ここで安全にTrueのみカウントする
        nj_count = valid_df["NJSS掲載"].astype(str).str.upper().isin(["TRUE", "1", "1.0", "YES"]).sum()
        ki_count = valid_df["入札王掲載"].astype(str).str.upper().isin(["TRUE", "1", "1.0", "YES"]).sum()
        
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

elif page == "実測データ入力":
    st.markdown('<div class="slds-page-header"><h1>📝 PoC 実測データ入力</h1></div>', unsafe_allow_html=True)
    st.markdown('<div class="slds-card">', unsafe_allow_html=True)
    
    # データを取得
    df_display = st.session_state.get('temp_df', load_data())
    
    # 💡 【超重要】インポートされたデータとStreamlitエディタの型の不一致を解消するロジック
    if not df_display.empty:
        # 1. チェックボックス列を確実なTrue/False型に強制変換
        bool_columns = ["仕様書", "NJSS掲載", "入札王掲載"]
        for col in bool_columns:
            if col in df_display.columns:
                # 文字列の "TRUE" や "1" もすべて本物のTrue/Falseに変換し、空欄はFalseにする
                df_display[col] = df_display[col].astype(str).str.strip().str.upper().map(
                    {'TRUE': True, '1': True, '1.0': True, 'YES': True}
                ).fillna(False)
        
        # 2. 数字列を確実な数値型に強制変換
        num_columns = ["予算(千円)", "落札金額(千円)"]
        for col in num_columns:
            if col in df_display.columns:
                # カンマ(,)などを除去してから数値化し、空欄は0にする
                df_display[col] = pd.to_numeric(
                    df_display[col].astype(str).str.replace(r'[¥,]', '', regex=True), 
                    errors='coerce'
                ).fillna(0).astype(int)

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
            
            # 保存時に邪魔になるNoneやNaNを空文字に一括変換
            clean_df = edited_df.fillna("")
            clean_df = clean_df.replace({None: ""})
            
            conn.update(spreadsheet=url, data=clean_df)
            
            if 'temp_df' in st.session_state:
                del st.session_state.temp_df
            st.success("スプレッドシートへの保存が完了しました！")
            st.rerun()
            
        except Exception as e:
            st.error(f"保存に失敗しました。詳細エラー:\n```\n{traceback.format_exc()}\n```")
    st.markdown('</div>', unsafe_allow_html=True)

elif page == "機能・評価設定":
    st.markdown('<div class="slds-page-header"><h1>⚙️ 機能・評価設定</h1></div>', unsafe_allow_html=True)
    
    st.subheader("🔍 検索ワードの追加とヒット件数比較", divider="blue")
    st.markdown('<div class="slds-card">', unsafe_allow_html=True)
    
    col_add1, col_add2 = st.columns([3, 1])
    new_word = col_add1.text_input("追加したい検索ワード", placeholder="例：BIツール、AI活用", key="input_new_word", label_visibility="collapsed")
    if col_add2.button("ワードを追加", use_container_width=True):
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

    st.subheader("✅ 主要機能チェックリスト", divider="blue")
    st.markdown('<div class="slds-card">', unsafe_allow_html=True)
    features = ["メール通知精度", "カテゴリ検索", "一括CSVダウンロード", "API連携可能", "予算書・予定情報検索", "落札企業分析機能", "同時アクセス数上限", "スマホ閲覧対応"]
    njss_f_scores = 0
    king_f_scores = 0

    f_col1, f_col2 = st.columns(2)
    with f_col1:
        st.markdown("#### NJSS 搭載機能")
        for feat in features:
            if st.checkbox(f"{feat} (NJSS)", key=f"nj_f_{feat}"):
                njss_f_scores += 1
    with f_col2:
        st.markdown("#### 入札王 搭載機能")
        for feat in features:
            if st.checkbox(f"{feat} (入札王)", key=f"ki_f_{feat}"):
                king_f_scores += 1

    st.markdown("---")
    st.markdown("#### 🏆 機能充実度の総合判定")
    if njss_f_scores > king_f_scores:
        st.success(f"機能面では 【 NJSS 】 が優勢です。 ({njss_f_scores} / {len(features)} 項目)")
    elif king_f_scores > njss_f_scores:
        st.success(f"機能面では 【 入札王 】 が優勢です。 ({king_f_scores} / {len(features)} 項目)")
    else:
        st.warning(f"機能面は 【 互角 】 です。 (各 {njss_f_scores} 項目)")
    st.markdown('</div>', unsafe_allow_html=True)

elif page == "データ一括インポート":
    st.markdown('<div class="slds-page-header"><h1>📥 データ一括インポート</h1></div>', unsafe_allow_html=True)
    st.markdown('<div class="slds-card">', unsafe_allow_html=True)
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
    st.markdown('</div>', unsafe_allow_html=True)
