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
    div[data-baseweb="input"], div[data-baseweb="input"] > div, div[data-baseweb="base-input"], input, textarea { background-color: #FFFFFF !important; color: #181818 !important; border-color: #DDDBDA !important; }
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
        kpi1, kpi2, kpi3 = st.columns(3)
        nj_count = valid_df["NJSS掲載"].astype(str).str.upper().isin(["TRUE", "1", "1.0", "YES"]).sum()
        ki_count = valid_df["入札王掲載"].astype(str).str.upper().isin(["TRUE", "1", "1.0", "YES"]).sum()
        
        with kpi1: draw_kpi_card("NJSS 網羅率", f"{(nj_count/len(valid_df)*100):.1f}%")
        with kpi2: draw_kpi_card("入札王 網羅率", f"{(ki_count/len(valid_df)*100):.1f}%")
        with kpi3: draw_kpi_card("検証完了案件", f"{len(valid_df)} 件")

        chart_layout = dict(template="plotly_white", paper_bgcolor="white", plot_bgcolor="white", font=dict(color="#181818"), margin=dict(l=20, r=20, t=50, b=20))
        color_map = {"NJSS": "#0176D3", "入札王": "#F28E2B", "NJSS件数": "#0176D3", "入札王件数": "#F28E2B"}

        col_l, col_r = st.columns(2)
        with col_l:
            fig_hits = px.bar(x=["NJSS", "入札王"], y=[nj_count, ki_count], title="案件捕捉数の比較", color=["NJSS", "入札王"], color_discrete_map=color_map)
            fig_hits.update_layout(**chart_layout)
            st.plotly_chart(fig_hits, use_container_width=True)
            
        with col_r:
            comp_df = pd.concat([valid_df["落札企業"], valid_df["応札1"], valid_df["応札2"], valid_df["応札3"]])
            pres_df = comp_df[comp_df != ""].value_counts().reset_index()
            pres_df.columns = ["企業名", "出現回数"]
            fig_p = px.bar(pres_df.head(8), x="出現回数", y="企業名", orientation='h', title="競合出現シェア (TOP 8)")
            fig_p.update_traces(marker_color='#0176D3')
            fig_p.update_layout(**chart_layout)
            st.plotly_chart(fig_p, use_container_width=True)

        if st.session_state.search_words:
            dash_search_data = []
            for word in st.session_state.search_words:
                counts = st.session_state.search_counts.get(word, {"NJSS": 0, "入札王": 0})
                dash_search_data.append({"検索ワード": word, "NJSS件数": counts["NJSS"], "入札王件数": counts["入札王"]})
            
            df_dash_sw = pd.DataFrame(dash_search_data)
            fig_dash_sw = px.bar(df_dash_sw, x="検索ワード", y=["NJSS件数", "入札王件数"], barmode="group", title="ワード別 ヒット件数比較", color_discrete_map=color_map)
            fig_dash_sw.update_layout(**chart_layout)
            st.plotly_chart(fig_dash_sw, use_container_width=True)

elif page == "実測データ入力":
    st.markdown('<div class="slds-page-header"><h1>📝 PoC 実測データ入力</h1></div>', unsafe_allow_html=True)
    
    # 既存データの読み込みと整理（空行を排除）
    df_current = load_data()
    valid_df = df_current[df_current["自治体名"].notna() & (df_current["自治体名"] != "")].copy()
    next_id = len(valid_df) + 1

    # CSVインポートデータがある場合の一括保存ボタン
    if 'temp_df' in st.session_state and not st.session_state.temp_df.empty:
        st.warning(f"📥 インポートされた {len(st.session_state.temp_df)} 件の未保存データがあります。")
        if st.button("☁️ インポートデータを一括保存する", use_container_width=True):
            try:
                import_data = st.session_state.temp_df.fillna("")
                import_data = import_data.replace({None: ""})
                updated_df = pd.concat([valid_df, import_data], ignore_index=True)
                url = st.secrets["connections"]["gsheets"]["spreadsheet"]
                conn.update(spreadsheet=url, data=updated_df)
                del st.session_state.temp_df
                st.success("インポートデータの保存が完了しました！")
                st.rerun()
            except Exception as e:
                st.error(f"保存に失敗しました。詳細エラー:\n```\n{traceback.format_exc()}\n```")
        st.markdown("---")

    st.info("💡 以下のフォームに各項目の実測結果を入力し、「この案件を保存する」ボタンを押して1件ずつ登録してください。")

    # 入力フォーム（Salesforce風カードデザイン内）
    st.markdown('<div class="slds-card">', unsafe_allow_html=True)
    with st.form("entry_form", clear_on_submit=True):
        st.markdown("#### 🏢 基本情報", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            municipality = st.text_input("自治体名 (必須)", placeholder="例：横浜市")
            budget = st.number_input("予算 (千円)", min_value=0, step=100)
        with c2:
            summary = st.text_area("案件概要", placeholder="例：R6年度 住民税システム改修", height=110)
        
        st.markdown("<br>#### 🏆 落札・応札情報", unsafe_allow_html=True)
        c3, c4 = st.columns(2)
        with c3:
            winner = st.text_input("落札企業", placeholder="例：株式会社ジール")
            winning_bid = st.number_input("落札金額 (千円)", min_value=0, step=100)
        with c4:
            bidder1 = st.text_input("応札企業 1")
            bidder2 = st.text_input("応札企業 2")
            bidder3 = st.text_input("応札企業 3")
        
        st.markdown("<br>#### ✅ ツール掲載確認", unsafe_allow_html=True)
        c5, c6, c7 = st.columns(3)
        with c5:
            spec = st.checkbox("📄 仕様書あり")
        with c6:
            njss_listed = st.checkbox("🔵 NJSS に掲載あり")
        with c7:
            king_listed = st.checkbox("🟠 入札王 に掲載あり")
            
        st.markdown("---")
        submitted = st.form_submit_button("☁️ この案件を保存する", use_container_width=True)

    # 保存処理
    if submitted:
        if not municipality:
            st.error("⚠️ 「自治体名」は必須項目です。入力してください。")
        else:
            new_record = pd.DataFrame([{
                "ID": next_id,
                "自治体名": municipality,
                "案件概要": summary,
                "仕様書": spec,
                "予算(千円)": budget,
                "落札金額(千円)": winning_bid,
                "落札企業": winner,
                "応札1": bidder1,
                "応札2": bidder2,
                "応札3": bidder3,
                "NJSS掲載": njss_listed,
                "入札王掲載": king_listed
            }])
            
            # データのお掃除と結合
            new_record = new_record.fillna("")
            updated_df = pd.concat([valid_df, new_record], ignore_index=True)
            
            try:
                url = st.secrets["connections"]["gsheets"]["spreadsheet"]
                conn.update(spreadsheet=url, data=updated_df)
                st.success(f"🎉 「{municipality}」の案件データを保存しました！")
                st.rerun()
            except Exception as e:
                st.error(f"保存に失敗しました。詳細エラー:\n```\n{traceback.format_exc()}\n```")
    st.markdown('</div>', unsafe_allow_html=True)

    # 登録済みデータの一覧表示（確認用）
    if not valid_df.empty:
        st.markdown("### 📋 登録済みデータ一覧")
        st.dataframe(valid_df, use_container_width=True, hide_index=True)

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
    * 案件ごとに実測結果を入力・登録できるフォームです。
    * 必須項目（自治体名など）を入力し、**「☁️ この案件を保存する」**ボタンを押すことで、クラウド上のスプレッドシートにデータが蓄積されます。
    * フォームの下部には、これまで登録したデータの一覧が確認用に表示されます。

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
                st.success("反映しました。「実測データ入力」画面に移動して一括保存してください。")
        except Exception as e:
            st.error(f"CSVの読み込みに失敗しました: {e}")
