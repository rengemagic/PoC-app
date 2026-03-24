import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="ZEAL用 入札ツール比較PoC", layout="wide")

st.title("⚖️入札ツールPoC評価")
st.caption("NJSS vs 入札王：データプラットフォーム事業・アライアンス営業視点での評価")

# --- 評価項目の定義 ---
eval_items = [
    "データ網羅性", "更新スピード", "過去落札データ", "予算書・予定情報",
    "検索精度(DX/ETL)", "データ出力(CSV)", "競合・市場分析",
    "組織連携・管理", "サポート体制", "ROI(費用対効果)"
]

if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=['サービス'] + eval_items)

# --- サイドバー：詳細入力 ---
with st.sidebar:
    st.header("📋 詳細スコアリング")
    target = st.radio("評価対象", ["NJSS", "入札王"])
    
    scores = {}
    for item in eval_items:
        scores[item] = st.slider(f"{item}", 1, 5, 3)
    
    if st.button("評価を確定して更新"):
        row_data = [target] + [scores[item] for item in eval_items]
        new_df = pd.DataFrame([row_data], columns=['サービス'] + eval_items)
        st.session_state.data = pd.concat([st.session_state.data[st.session_state.data['サービス'] != target], new_df])
        st.success(f"{target} の評価を保存しました")

# --- メイン画面 ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📊 比較分析チャート")
    if len(st.session_state.data) > 0:
        fig = go.Figure()
        for i, row in st.session_state.data.iterrows():
            fig.add_trace(go.Scatterpolar(
                r=[row[m] for m in eval_items],
                theta=eval_items,
                fill='toself',
                name=row['サービス']
            ))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("左側のサイドバーからスコアを入力してください。")

with col2:
    st.subheader("📑 稟議用メモ")
    st.text_area("データ連携に関する所感", placeholder="API連携やCSV加工の手間について...")
    st.text_area("ターゲット(官公庁)の網羅感", placeholder="横浜市や特定団体の案件漏れについて...")

# --- データ書き出し機能 ---
st.markdown("---")
st.subheader("📥 評価データのエクスポート")
if not st.session_state.data.empty:
    csv = st.session_state.data.to_csv(index=False).encode('utf-8-sig')
    st.download_button("評価結果をCSVとして保存", data=csv, file_name="bid_tool_poc_results.csv", mime="text/csv")
else:
    st.write("データがありません")

# --- ジール様向けROI計算 ---
st.markdown("---")
st.subheader("💡 投資対効果シミュレーション")
c1, c2 = st.columns(2)
with c1:
    manual_hours = st.number_input("現状の週あたり収集・整理工数(h)", value=10.0)
    bid_count = st.number_input("月間応札検討数", value=5)
with c2:
    potential_value = st.number_input("平均受注単価(万円)", value=1000)
    win_rate_up = st.slider("ツール活用による落札率向上期待(%)", 0, 10, 2)

expected_benefit = (potential_value * (win_rate_up / 100) * bid_count)
st.metric("導入による売上期待向上(月間)", f"{expected_benefit} 万円")
