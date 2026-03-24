import streamlit as st
import pandas as pd

st.set_page_config(page_title="入札ツール精密評価ボード", layout="wide")

st.title("🛡️ 入札ツール精密PoC評価システム")
st.caption("検索ワード任意追加・50件実測・機能比較・自動判定ツール")

# --- セッション状態の初期化 ---
if 'search_words' not in st.session_state:
    st.session_state.search_words = ["DX推進", "データ分析基盤"]

if 'past_cases' not in st.session_state:
    st.session_state.past_cases = pd.DataFrame(
        [{"ID": i+1, "自治体名": "", "案件概要": "", "仕様書": False, "予算(千円)": 0, "製品名": "", "NJSS掲載": False, "入札王掲載": False} for i in range(50)]
    )

# --- 1. 検索ワードの任意設定とヒット数比較 ---
st.header("1. 検索ヒット件数比較（ワード任意設定）")

with st.expander("🔍 検索ワードの追加・管理", expanded=True):
    col_add1, col_add2 = st.columns([3, 1])
    with col_add1:
        new_word = st.text_input("追加したい検索ワードを入力", placeholder="例：ETL、BIツール", key="input_new_word")
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
    st.subheader("📊 ワード別ヒット件数入力")
    for word in st.session_state.search_words:
        col_w1, col_w2 = st.columns(2)
        with col_w1:
            n_val = st.number_input(f"NJSS: {word}", min_value=0, key=f"n_{word}")
        with col_w2:
            k_val = st.number_input(f"入札王: {word}", min_value=0, key=f"k_{word}")
        
        n_j = "○" if n_val >= k_val and n_val > 0 else "×"
        k_j = "○" if k_val >= n_val and k_val > 0 else "×"
        search_data.append({"ワード": word, "NJSS件数": n_val, "NJSS判定": n_j, "入札王件数": k_val, "入札王判定": k_j})
    st.table(pd.DataFrame(search_data))

# --- 2. 過去案件 50件データ検証（自動判定） ---
st.header("2. 過去案件データ充足度（50件検証）")
st.write("自治体名、案件概要、予算、製品名を入力し、掲載の有無をチェックしてください。")

edited_cases = st.data_editor(
    st.session_state.past_cases,
    column_config={
        "仕様書": st.column_config.CheckboxColumn("仕様書有"),
        "NJSS掲載": st.column_config.CheckboxColumn("NJSS掲載"),
        "入札王掲載": st.column_config.CheckboxColumn("入札王掲載"),
        "予算(千円)": st.column_config.NumberColumn("予算(千円)", format="%d"),
    },
    hide_index=True,
    num_rows="fixed",
    use_container_width=True
)

# 過去案件の自動判定
njss_hit_count = edited_cases["NJSS掲載"].sum()
king_hit_count = edited_cases["入札王掲載"].sum()

st.subheader("🏁 過去案件 網羅性判定")
c1, c2 = st.columns(2)
with c1:
    st.metric("NJSS 過去案件捕捉数", f"{njss_hit_count} / 50 件", f"網羅率 {njss_hit_count*2}%")
    if njss_hit_count > king_hit_count: st.success("NJSSが網羅性で勝っています")
with c2:
    st.metric("入札王 過去案件捕捉数", f"{king_hit_count} / 50 件", f"網羅率 {king_hit_count*2}%")
    if king_hit_count > njss_hit_count: st.success("入札王が網羅性で勝っています")

# --- 3. 主要機能チェックリスト（自動判定） ---
st.header("3. 主要機能チェックリスト")
features = ["メール通知精度", "カテゴリ検索", "一括CSVダウンロード", "API連携", "予算書・予定情報検索", "落札企業分析", "スマホ閲覧対応"]
njss_f_scores = 0
king_f_scores = 0

f_col1, f_col2 = st.columns(2)
with f_col1:
    st.subheader("NJSS 機能")
    for feat in features:
        if st.checkbox(f"NJSS: {feat}", key=f"nj_check_{feat}"):
            njss_f_scores += 1
with f_col2:
    st.subheader("入札王 機能")
    for feat in features:
        if st.checkbox(f"入札王: {feat}", key=f"ki_check_{feat}"):
            king_f_scores += 1

st.subheader("🏁 機能面での総合判定")
if njss_f_scores > king_f_scores:
    st.success(f"機能の充実度では 【NJSS】 が優勢です。 ({njss_f_scores}項目)")
elif king_f_scores > njss_f_scores:
    st.success(f"機能の充実度では 【入札王】 が優勢です。 ({king_f_scores}項目)")
else:
    st.warning("機能面では両者互角です。")

# --- 4. CSV出力 ---
st.header("4. 結果の出力")
if st.button("全データを集計してダウンロード準備"):
    # 過去案件シートの書き出し
    csv_cases = edited_cases.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📩 1.過去案件検証データを保存", data=csv_cases, file_name="poc_case_study.csv", mime="text/csv")
    
    # 検索ワード比較の書き出し
    if search_data:
        csv_sw = pd.DataFrame(search_data).to_csv(index=False).encode('utf-8-sig')
        st.download_button("📩 2.検索ワード比較結果を保存", data=csv_sw, file_name="poc_search_results.csv", mime="text/csv")
