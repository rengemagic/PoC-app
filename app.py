import streamlit as st
import pandas as pd

st.set_page_config(page_title="入札ツール精密評価ボード", layout="wide")

st.title("🛡️ 入札ツール精密PoC評価システム")
st.caption("実測データに基づく「NJSS vs 入札王」の自動判定レポート作成ツール")

# --- 1. 推奨検索ワード比較（自動判定） ---
st.header("1. 検索ヒット件数比較（精度検証）")
search_words = ["ETL", "データ基盤", "DX推進", "データ分析", "AI・機械学習"]
search_data = []

col_sw1, col_sw2 = st.columns(2)
with col_sw1:
    st.subheader("NJSS ヒット数")
    njss_counts = {word: st.number_input(f"NJSS: {word}", min_value=0, key=f"njss_sw_{word}") for word in search_words}
with col_sw2:
    st.subheader("入札王 ヒット数")
    king_counts = {word: st.number_input(f"入札王: {word}", min_value=0, key=f"king_sw_{word}") for word in search_words}

for word in search_words:
    n = njss_counts[word]
    k = king_counts[word]
    njss_j = "○" if n >= k and n > 0 else "×"
    king_j = "○" if k >= n and k > 0 else "×"
    search_data.append({"ワード": word, "NJSS件数": n, "NJSS判定": njss_j, "入札王件数": k, "入札王判定": king_j})

st.table(pd.DataFrame(search_data))

# --- 2. 過去案件 50件データ検証 ---
st.header("2. 過去案件データ充足度（50件検証）")
st.info("過去の案件について、どこまで情報が取得できるか50件分の枠を用意しました。")

# 50件分のデータ入力用の器（データエディタ）
if 'past_cases' not in st.session_state:
    st.session_state.past_cases = pd.DataFrame(
        [{"ID": i+1, "自治体名": "", "案件概要": "", "仕様書": False, "予算(千円)": 0, "製品名": "", "NJSS確認": False, "入札王確認": False} for i in range(50)]
    )

edited_cases = st.data_editor(
    st.session_state.past_cases,
    column_config={
        "仕様書": st.column_config.CheckboxColumn("仕様書有"),
        "NJSS確認": st.column_config.CheckboxColumn("NJSS掲載"),
        "入札王確認": st.column_config.CheckboxColumn("入札王掲載"),
    },
    hide_index=True,
    num_rows="fixed"
)

# 過去案件の自動判定ロジック
njss_hit_rate = (edited_cases["NJSS確認"].sum() / 50) * 100
king_hit_rate = (edited_cases["入札王確認"].sum() / 50) * 100

c1, c2 = st.columns(2)
c1.metric("NJSS 過去案件網羅率", f"{njss_hit_rate}%")
c2.metric("入札王 過去案件網羅率", f"{king_hit_rate}%")

# --- 3. 機能チェックリスト（優劣自動判定） ---
st.header("3. 機能チェックリスト")
features = ["メール送信機能", "カテゴリ検索", "AIレコメンド", "スマホ対応", "CSV一括DL", "API連携", "予算書検索", "落札傾向分析"]
feature_checks = []

col_f1, col_f2 = st.columns(2)
with col_f1:
    st.subheader("NJSS 機能")
    njss_f = {f: st.checkbox(f, key=f"njss_f_{f}") for f in features}
with col_f2:
    st.subheader("入札王 機能")
    king_f = {f: st.checkbox(f, key=f"king_f_{f}") for f in features}

njss_score = sum(njss_f.values())
king_score = sum(king_f.values())

st.subheader("🏁 最終優劣判定")
if njss_score > king_score:
    st.success(f"機能面では 【NJSS】 が優勢です（{njss_score} vs {king_score}）")
elif king_score > njss_score:
    st.success(f"機能面では 【入札王】 が優勢です（{king_score} vs {njss_score}）")
else:
    st.warning(f"機能面は 【引き分け】 です（{njss_score} vs {king_score}）")

# --- 4. CSV出力 ---
st.header("4. 結果の出力")

# 全データをまとめる作業（複数の表を一つのCSVにするため簡略化して結合）
if st.button("全データを集計してダウンロード準備"):
    # 各セクションの結果を文字列として結合したり、複数のCSVボタンを用意したりできますが、
    # ここでは「過去案件の精査データ」をメインに出力します。
    final_csv = edited_cases.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📩 50件検証データをCSVで保存", data=final_csv, file_name="poc_full_report.csv", mime="text/csv")
    
    # 検索ワード結果もCSV化
    sw_csv = pd.DataFrame(search_data).to_csv(index=False).encode('utf-8-sig')
    st.download_button("📩 検索ワード比較をCSVで保存", data=sw_csv, file_name="search_word_comparison.csv", mime="text/csv")
