import streamlit as st
import pandas as pd

st.set_page_config(page_title="入札ツール精密評価ボード", layout="wide")

st.title("🛡️ 入札ツール精密PoC評価システム")
st.caption("検索ワード任意追加・50件実測・機能比較・自動判定ツール")

# --- セッション状態の初期化 ---
if 'search_words' not in st.session_state:
    st.session_state.search_words = ["DX推進", "データ基盤"] # 初期値

if 'past_cases' not in st.session_state:
    st.session_state.past_cases = pd.DataFrame(
        [{"ID": i+1, "自治体名": "", "案件概要": "", "仕様書": False, "予算(千円)": 0, "製品名": "", "NJSS確認": False, "入札王確認": False} for i in range(50)]
    )

# --- 1. 検索ワードの任意設定とヒット数比較 ---
st.header("1. 検索ヒット件数比較（ワード任意設定）")

with st.expander("🔍 検索ワードの追加・管理", expanded=True):
    new_word = st.text_input("追加したい検索ワードを入力してください", placeholder="例：ETL、BIツール、AI活用")
    if st.button("ワードを追加"):
        if i_word := new_word.strip():
            if i_word not in st.session_state.search_words:
                st.session_state.search_words.append(i_word)
                st.success(f"「{i_word}」を追加しました")
            else:
                st.warning("そのワードは既に追加されています")

    if st.button("ワードリストをリセット"):
        st.session_state.search_words = []
        st.rerun()

st.subheader("📊 ワード別ヒット件数入力")
search_data = []
if st.session_state.search_words:
    for word in st.session_state.search_words:
        col_w1, col_w2, col_w3 = st.columns([2, 2, 2])
        with col_w1:
            n_val = st.number_input(f"NJSS: {word}", min_value=0, key=f"n_{word}")
        with col_w2:
            k_val = st.number_input(f"入札王: {word}", min_value=0, key=f"k_{word}")
        
        # 自動判定ロジック
        n_j = "○" if n_val >= k_val and n_val > 0 else "×"
        k_j = "○" if k_val >= n_val and k_val > 0 else "×"
        search_data.append({"ワード": word, "NJSS件数": n_val, "NJSS判定": n_j, "入札王件数": k_val, "入札王判定": k_j})

    st.table(pd.DataFrame(search_data))
else:
    st.info("検索ワードを追加してください。")

# --- 2. 過去案件 50件データ検証 ---
st.header("2. 過去案件データ充足度（50件検証）")
st.write("自治体名、案件概要、仕様書の有無、予算、製品名などを入力し、両ツールの網羅性を確認します。")

edited_cases = st.data_editor(
    st.session_state.past_cases,
    column_config={
        "仕様書": st.column_config.CheckboxColumn("仕様書有"),
        "NJSS確認": st.column_config.CheckboxColumn("NJSS掲載"),
        "入札王確認": st.column_config.CheckboxColumn("入札王掲載"),
        "予算(千円)": st.column_config.NumberColumn("予算(千円)", format="%d"),
    },
    hide_index=True,
    num_rows="fixed",
    use_container_width=True
)

# 過去案件の自動判定（網羅率）
njss_hit_count = edited_cases["NJSS確認"].sum()
king_hit_count = edited_cases["入札王確認"].sum()

c1, c2 = st.columns(2)
c1.metric("NJSS 過去案件捕捉数", f"{njss_hit_count} / 50 件", f"{njss_hit_count*2}%")
c2.metric("入札王 過去案件捕捉数", f"{king_hit_count} / 50 件", f"{king_hit_count*2}%")

# --- 3. 機能チェックリスト（優劣自動判定） ---
st.header("3. 主要機能チェックリスト")
features = ["メール通知精度", "カテゴリ検索", "一括CSVダウンロード", "API連携", "予算書・予定情報検索", "落札企業分析", "スマホ閲覧対応"]
njss_f_scores = 0
king_f_scores = 0

f
