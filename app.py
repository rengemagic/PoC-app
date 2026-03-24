import streamlit as st
import pandas as pd

# ページ設定
st.set_page_config(page_title="ZEAL用 入札ツール比較PoC", layout="wide")

st.title("⚖️ 入札ツールPoC評価：2社比較モード")
st.caption("NJSS vs 入札王 適合性チェックリスト")

# --- 評価項目の定義（ジール様のビジネス視点） ---
eval_items = [
    "データ網羅性（横浜市等、ターゲット自治体のカバー）",
    "更新スピード（公示後24時間以内の反映）",
    "過去落札データ（過去3年分以上の蓄積）",
    "予算書・予定情報（案件の予兆把握機能）",
    "検索精度（DX/ETL/BI等のノイズ除去）",
    "データ出力（CSV/Excel形式での一括出力）",
    "競合分析（特定企業の落札履歴追跡）",
    "組織連携（チーム内での案件ステータス管理）",
    "サポート体制（専任担当による条件設定支援）",
    "初期費用・コスト体系（予算との適合性）"
]

# データ保持
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=['評価項目', 'NJSS', '入札王'])
    # 初期データ作成
    initial_df = pd.DataFrame({'評価項目': eval_items, 'NJSS': '×', '入札王': '×'})
    st.session_state.data = initial_df

# --- メイン画面：評価テーブル ---
st.subheader("📋 評価入力テーブル")
st.write("各項目の「○（適合）」または「×（不適合）」を選択してください。")

# データフレームの編集（Streamlitのエディタ機能を使用）
edited_df = st.data_editor(
    st.session_state.data,
    column_config={
        "NJSS": st.column_config.SelectboxColumn("NJSS", options=["○", "×"], required=True),
        "入札王": st.column_config.SelectboxColumn("入札王", options=["○", "×"], required=True),
        "評価項目": st.column_config.TextColumn("評価項目", disabled=True)
    },
    hide_index=True,
    use_container_width=True
)

# データの保存
if st.button("評価を確定する"):
    st.session_state.data = edited_df
    st.success("評価を保存しました。")

# --- 集計と可視化 ---
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 適合数カウント")
    njss_count = (edited_df['NJSS'] == '○').sum()
    king_count = (edited_df['入札王'] == '○').sum()
    st.metric("NJSSの○の数", f"{njss_count} / {len(eval_items)}")
    st.metric("入札王の○の数", f"{king_count} / {len(eval_items)}")

with col2:
    st.subheader("📥 スプレッドシート用エクスポート")
    # CSV変換 (Excel/Googleシートで文字化けしないよう utf-8-sig を使用)
    csv = edited_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="評価結果をCSV(Excel形式)でダウンロード",
        data=csv,
        file_name="bid_tool_comparison_zeal.csv",
        mime="text/csv",
    )

# --- 稟議用コメント ---
st.markdown("---")
st.subheader("📝 総合コメント（稟議補足用）")
comment = st.text_area("選定理由や特記事項", placeholder="例：〇〇の理由により、データ網羅性に勝るNJSSを推奨する。")
