import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="入札ツール精密評価・分析ボード", layout="wide")

st.title("🛡️ 入札ツール精密PoC評価 & グラフ分析システム")
st.caption("検索ワード任意追加 ・ 50件実測 ・ 機能比較 ・ 自動判定レポート")

# --- セッション状態の初期化 ---
if 'search_words' not in st.session_state:
    st.session_state.search_words = ["DX推進", "データ分析基盤"]

if 'past_cases' not in st.session_state:
    st.session_state.past_cases = pd.DataFrame(
        [{"ID": i+1, "自治体名": "", "案件概要": "", "仕様書": False, "予算(千円)": 0, "落札企業": "", "応札企業(名・数)": "", "NJSS掲載": False, "入札王掲載": False} for i in range(50)]
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
    df_sw = pd.DataFrame(search_data)
    fig_sw = px.bar(df_sw, x="ワード", y=["NJSS", "入札王"], barmode="group", title="ワード別ヒット件数（実測値）")
    st.plotly_chart(fig_sw, use_container_width=True)

# --- 2. 過去案件 50件データ検証 ---
st.header("2. 過去案件・競合データ入力（50件）")
st.write("各ツールで「落札・応札企業名」や「仕様書」まで辿り着けるか実測してください。")
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

# --- 3. 主要機能チェックリスト（復活版） ---
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

st.subheader("🏁 機能面での総合判定")
if njss_f_scores > king_f_scores:
    st.success(f"機能の充実度では 【NJSS】 が優勢です。 ({njss_f_scores} / {len(features)})")
elif king_f_scores > njss_f_scores:
    st.success(f"機能の充実度では 【入札王】 が優勢です。 ({king_f_scores} / {len(features)})")
else:
    st.warning(f"機能面は 【互角】 です。 ({njss_f_scores}項目)")

# --- 4. 過去案件データの自動分析レポート ---
st.header("📊 PoCデータ分析レポート")
valid_df = edited_cases[edited_cases["自治体名"] != ""]

if not valid_df.empty:
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        nj_hits = valid_df["NJSS掲載"].sum()
        ki_hits = valid_df["入札王掲載"].sum()
        fig_hits = px.bar(x=["NJSS", "入札王"], y=[nj_hits, ki_hits], color=["NJSS", "入札王"],
                          title=f"案件捕捉数（検証 {len(valid_df)} 件中）", labels={'x': 'ツール', 'y': 'ヒット数'})
        st.plotly_chart(fig_hits, use_container_width=True)
        
    with col_g2:
        spec_count = valid_df["仕様書"].sum()
        budget_count = (valid_df["予算(千円)"] > 0).sum()
        fig_info = px.pie(values=[spec_count, budget_count], names=["仕様書あり", "予算額あり"], title="詳細情報の充足度", hole=0.3)
        st.plotly_chart(fig_info, use_container_width=True)

    # 落札企業ランキング
    comp_df = valid_df[valid_df["落札企業"] != ""]["落札企業"].value_counts().reset_index()
    if not comp_df.empty:
        comp_df.columns = ["企業名", "落札数"]
        fig_comp = px.bar(comp_df.head(5), x="落札数", y="企業名", orientation='h', title="競合他社の落札シェア(TOP5)")
        st.plotly_chart(fig_comp, use_container_width=True)
else:
    st.info("上の表に自治体名を入力すると分析グラフが表示されます。")

# --- 5. 出力 ---
st.header("5. エクスポート")
if st.button("全データを集計してCSV作成"):
    csv_out = edited_cases.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📩 検証結果CSVを保存", data=csv_out, file_name="bid_poc_final_report.csv", mime="text/csv")
