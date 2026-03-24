import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="入札ツール精密評価・分析ボード", layout="wide")

st.title("🛡️ 入札ツール精密PoC評価 & 競合分析システム")
st.caption("実測データに基づく「NJSS vs 入札王」の可視化レポート")

# --- セッション状態の初期化 ---
if 'search_words' not in st.session_state:
    st.session_state.search_words = ["DX推進", "データ分析基盤"]

if 'past_cases' not in st.session_state:
    st.session_state.past_cases = pd.DataFrame(
        [{"ID": i+1, "自治体名": "", "案件概要": "", "仕様書": False, "予算(千円)": 0, "落札企業": "", "応札企業(名・数)": "", "NJSS掲載": False, "入札王掲載": False} for i in range(50)]
    )

# --- 1. 検索ワード比較 ---
st.header("1. 検索ヒット件数比較")
with st.expander("🔍 ワード管理", expanded=False):
    new_word = st.text_input("追加したい検索ワードを入力", key="input_new_word")
    if st.button("ワードを追加"):
        if new_word and new_word not in st.session_state.search_words:
            st.session_state.search_words.append(new_word)
            st.rerun()

search_data = []
for word in st.session_state.search_words:
    col_w1, col_w2 = st.columns(2)
    n_val = col_w1.number_input(f"NJSS: {word}", min_value=0, key=f"n_{word}")
    k_val = col_w2.number_input(f"入札王: {word}", min_value=0, key=f"k_{word}")
    search_data.append({"ワード": word, "NJSS": n_val, "入札王": k_val})

if search_data:
    df_sw = pd.DataFrame(search_data)
    fig_sw = px.bar(df_sw, x="ワード", y=["NJSS", "入札王"], barmode="group", title="ワード別ヒット件数比較")
    st.plotly_chart(fig_sw, use_container_width=True)

# --- 2. 過去案件 50件データ検証（入力エリア） ---
st.header("2. 過去案件・競合データ入力（50件）")
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

# --- 3. データの自動グラフ化（分析セクション） ---
st.header("📊 PoCデータ分析レポート")

# 有効なデータのみ抽出（自治体名が入っているもの）
valid_df = edited_cases[edited_cases["自治体名"] != ""]

if not valid_df.empty:
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        # 1. 網羅率の比較グラフ
        njss_hits = valid_df["NJSS掲載"].sum()
        king_hits = valid_df["入札王掲載"].sum()
        hit_df = pd.DataFrame({"ツール": ["NJSS", "入札王"], "掲載数": [njss_hits, king_hits]})
        fig_hits = px.bar(hit_df, x="ツール", y="掲載数", color="ツール", 
                           title=f"案件捕捉数（検証対象 {len(valid_df)} 件中）",
                           color_discrete_map={"NJSS": "#1f77b4", "入札王": "#ff7f0e"})
        st.plotly_chart(fig_hits, use_container_width=True)
        
    with col_g2:
        # 2. 仕様書・予算情報の保持率
        spec_count = valid_df["仕様書"].sum()
        budget_count = (valid_df["予算(千円)"] > 0).sum()
        info_df = pd.DataFrame({
            "項目": ["仕様書あり", "予算額あり"],
            "件数": [spec_count, budget_count]
        })
        fig_info = px.pie(info_df, values="件数", names="項目", title="取得情報の充実度", hole=0.4)
        st.plotly_chart(fig_info, use_container_width=True)

    # 3. 落札企業ランキング（競合分析）
    st.subheader("🏆 過去案件の落札企業シェア（TOP 5）")
    competitor_counts = valid_df[valid_df["落札企業"] != ""]["落札企業"].value_counts().reset_index()
    competitor_counts.columns = ["企業名", "落札数"]
    if not competitor_counts.empty:
        fig_comp = px.bar(competitor_counts.head(5), x="落札数", y="企業名", orientation='h', 
                          title="主要な競合他社", color="落札数", color_continuous_scale="Viridis")
        fig_comp.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.info("落札企業名を入力すると、ここに競合分析グラフが表示されます。")

else:
    st.warning("分析を表示するには、上の表に自治体名やチェックを入力してください。")

# --- 4. 機能・結果エクスポート ---
st.header("4. エクスポート")
if st.button("最終集計CSVを作成"):
    csv = edited_cases.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📩 検証結果をダウンロード", data=csv, file_name="full_poc_analysis.csv", mime="text/csv")
