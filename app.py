import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ページ設定
st.set_page_config(page_title="入札サービス比較PoC", layout="wide")

st.title("⚖️ 入札情報サービス PoC評価ダッシュボード")
st.caption("NJSS vs 入札王：実用性・コスト・精度の比較管理ツール")

# --- データ保持の仕組み（簡易版） ---
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=['サービス', '網羅性', '分析機能', '利便性', 'サポート', 'コスト感'])

# --- サイドバー：評価入力 ---
with st.sidebar:
    st.header("📋 評価スコア入力")
    target = st.radio("評価対象を選択", ["NJSS", "入札王"])
    
    st.markdown("---")
    s1 = st.slider("1. 情報の網羅性 (官公庁・自治体数など)", 1, 5, 3)
    s2 = st.slider("2. 戦略的分析 (過去落札データ等)", 1, 5, 3)
    s3 = st.slider("3. チーム利便性 (管理・通知機能)", 1, 5, 3)
    s4 = st.slider("4. サポート体制 (導入支援等)", 1, 5, 3)
    s5 = st.slider("5. コストパフォーマンス", 1, 5, 3)
    
    if st.button("評価を確定して更新"):
        new_data = pd.DataFrame([[target, s1, s2, s3, s4, s5]], 
                                columns=['サービス', '網羅性', '分析機能', '利便性', 'サポート', 'コスト感'])
        # 既存データがあれば更新、なければ追加
        st.session_state.data = pd.concat([st.session_state.data[st.session_state.data['サービス'] != target], new_data])
        st.success(f"{target} の評価を保存しました！")

# --- メイン画面：分析レポート ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📊 比較レーダーチャート")
    if not st.session_state.data.empty:
        categories = ['網羅性', '分析機能', '利便性', 'サポート', 'コスト感']
        fig = go.Figure()

        for i, row in st.session_state.data.iterrows():
            fig.add_trace(go.Scatterpolar(
                r=[row[c] for c in categories],
                theta=categories,
                fill='toself',
                name=row['サービス']
            ))

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
            showlegend=True
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("サイドバーから評価を入力してください。グラフが表示されます。")

with col2:
    st.subheader("📝 サービス別メモ")
    st.text_area("NJSSの懸念・備考", placeholder="例：情報の網羅性は高いが、月額費用がネック...")
    st.text_area("入札王の懸念・備考", placeholder="例：UIがシンプルで使いやすいが、過去分析機能が...")

# --- 下部：簡易シミュレーション ---
st.markdown("---")
st.subheader("💰 ROI（投資対効果）シミュレーター")
c1, c2, c3 = st.columns(3)
with c1:
    man_hours = st.number_input("月間の情報収集工数（時間）", value=20)
with c2:
    hourly_rate = st.number_input("担当者の時給換算（円）", value=3000)
with c3:
    tool_cost = st.number_input("ツール月額費用（円）", value=50000)

reduction_rate = 0.8 # ツール導入で80%削減と仮定
saved_money = (man_hours * hourly_rate) * reduction_rate
profit = saved_money - tool_cost

st.metric("導入による月間期待削減効果", f"{int(profit)} 円", delta=f"{int(saved_money)} 円の工数削減")
