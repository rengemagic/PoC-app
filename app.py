import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="入札ツール精密評価・分析ボード", layout="wide")

st.title("🛡️ 入札ツール精密PoC評価 & 競合分析システム")
st.caption("検索ワード任意追加 ・ 50件実測（応札3社個別入力） ・ 機能比較 ・ 自動判定")

# --- セッション状態の初期化 ---
if 'search_words' not in st.session_state:
    st.session_state.search_words = ["DX推進", "データ分析基盤"]

if 'past_cases' not in st.session_state:
    # 列定義を拡張：応札企業を3社まで個別入力できるように設定
    st.session_state.past_cases = pd.DataFrame(
        [{"ID": i+1, "自治体名": "", "案件概要": "", "仕様書": False, "予算(千円)": 0, 
          "落札企業": "", "応札1": "", "応札2": "", "応札3": "",
          "NJSS掲載": False, "入札王掲載": False} for i in range(50)]
    )

# --- 1. 検索ワード比較（任意設定） ---
st.header("1. 検索ヒット件数比較")
with st.expander("🔍 検索ワードの追加・管理", expanded=False):
    col_add1, col_add2 = st.columns([3, 1])
    with col_add1:
        new_word = st.text_input("追加したい検索ワードを入力", key="input_new_word")
    with col_add2:
        if st.button("ワードを追加"):
            if new_word and new_word not in st.session_state.search_words:
                st.session_state.search_words.append(new_word)
                st.rerun()
    if st.button("ワードリストをリセット"):
        st.session_state.search_words = []
        st.rerun()

search_data = []
if st.session_state.search_words:
    for word in st.session_state.search_words:
        col_w1, col_w2 = st.columns(2)
        n_val = col_w1.number_input(f"NJSSヒット数: {word}", min_value=0, key=f"n_{word}")
        k_val = col_w2.number_input(f"入札王ヒット数: {word}", min_value=0, key=f"k_{word}")
        n_j = "○" if n_val >= k_val and n_val > 0 else "×"
        k_j = "○" if k_val >= n_val and k_val > 0 else "×"
        search_data.append({"ワード": word, "NJSS": n_val, "NJSS判定": n_j, "入札王": k_val, "入札王判定": k_j})
    
    st.table(pd.DataFrame(search_data))

# --- 2. 過去案件 50件データ検証（競合分析強化版） ---
st.header("2. 過去案件・競合データ入力（50件）")
st.write("落札企業だけでなく、応札していた競合3社まで入力し、各ツールで捕捉できるか検証します。")

edited_cases = st.data_editor(
    st.session_state.past_cases,
    column_config={
        "仕様書": st.column_config.CheckboxColumn("仕様書有"),
        "NJSS掲載": st.column_config.CheckboxColumn("NJSS掲載"),
        "入札王掲載": st.column_config.CheckboxColumn("入札王掲載"),
        "予算(千円)": st.column_config.NumberColumn("予算(千円)", format="%d"),
        "応札1": st.column_config.TextColumn("応札企業1"),
        "応札2": st.column_config.TextColumn("応札企業2"),
        "応札3": st.column_config.TextColumn("応札企業3"),
    },
    hide_index=True,
    num_rows="fixed",
    use_container_width=True
)

# --- 3. 主要機能チェックリスト ---
st.header("3. 主要機能チェックリスト")
features = ["メール通知精度", "カテゴリ検索", "一括CSVダウンロード", "API連携可能", "予算書・予定情報検索", "落札企業分析機能", "同時アクセス数上限", "スマホ閲覧対応"]
njss_f_scores = 0
king_f_scores = 0

f_col1, f_col2 = st.columns(2)
with f_col1:
    st.subheader("NJSS 機能有無")
    for feat in features:
        if st.checkbox(f"NJSS: {feat}", key=f"nj_f_{feat}"):
            njss_f_scores += 1
with f_col2:
    st.subheader("入札王 機能有無")
    for feat in features:
        if st.checkbox(f"入札王: {feat}", key=f"ki_f_{feat}"):
            king_f_scores += 1

# --- 4. データの可視化レポート ---
st.header("📊 PoCデータ分析レポート")
valid_df = edited_cases[edited_cases["自治体名"] != ""]

if not valid_df.empty:
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        # 捕捉数比較
        nj_hits = valid_df["NJSS掲載"].sum()
        ki_hits = valid_df["入札王掲載"].sum()
        fig_hits = px.bar(x=["NJSS", "入札王"], y=[nj_hits, ki_hits], color=["NJSS", "入札王"],
                          title=f"案件捕捉数（検証 {len(valid_df)} 件中）")
        st.plotly_chart(fig_hits, use_container_width=True)
        
    with col_g2:
        # 落札企業のシェア分析
        comp_df = valid_df[valid_df["落札企業"] != ""]["落札企業"].value_counts().reset_index()
        comp_df.columns = ["企業名", "落札数"]
        fig_comp = px.pie(comp_df.head(5), values="落札数", names="企業名", title="落札企業のシェア(TOP5)", hole=0.3)
        st.plotly_chart(fig_comp, use_container_width=True)

    # 競合全体の出現回数（落札＋応札1〜3）
    st.subheader("🏢 競合企業の出現頻度（マーケット・プレゼンス）")
    all_competitors = pd.concat([
        valid_df["落札企業"], valid_df["応札1"], valid_df["応札2"], valid_df["応札3"]
    ])
    presence_df = all_competitors[all_competitors != ""].value_counts().reset_index()
    presence_df.columns = ["企業名", "出現回数"]
    if not presence_df.empty:
        fig_pres = px.bar(presence_df.head(10), x="出現回数", y="企業名", orientation='h', 
                          title="応札・落札によく登場する企業（TOP10）", color="出現回数")
        st.plotly_chart(fig_pres, use_container_width=True)
else:
    st.info("表に自治体名を入力すると分析グラフが表示されます。")

# --- 5. 出力 ---
st.header("5. エクスポート")
if st.button("全データを集計してCSV作成"):
    csv_out = edited_cases.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📩 検証結果CSVを保存", data=csv_out, file_name="bid_poc_final_report.csv", mime="text/csv")
