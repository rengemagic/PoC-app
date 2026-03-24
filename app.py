import streamlit as st
import pandas as pd

# ページ設定
st.set_page_config(page_title="入札ツール比較PoC", layout="wide")

st.title("⚖️ 入札情報サービス 比較評価ボード")
st.caption("NJSS vs 入札王：PoC（概念実証）における機能適合性チェック")

# --- 評価項目の定義（一般的かつ実用的な10項目） ---
eval_items = [
    "機関網羅性（中央省庁・地方自治体・外郭団体）",
    "情報の速報性（公示当日の反映・メール通知）",
    "検索の柔軟性（キーワード・除外設定・条件保存）",
    "過去データの蓄積（落札価格・応札社数・落札率）",
    "案件管理機能（検討中・辞退・応募のステータス管理）",
    "データ出力（CSV/Excel形式のダウンロード）",
    "付加価値情報（予算書・予定情報・予兆の把握）",
    "競合分析（他社の落札傾向・得意地域の可視化）",
    "操作性・UI（直感的な画面・スマホ対応）",
    "コスト・サポート（料金体系・導入支援・電話対応）"
]

# データ保持の仕組み
if 'results' not in st.session_state:
    # 各項目に対して、サービスごとの[判定, コメント]を保持
    st.session_state.results = {
        item: {"NJSS": {"judge": "×", "note": ""}, "入札王": {"judge": "×", "note": ""}}
        for item in eval_items
    }

# --- メイン画面：評価セクション ---
st.info("💡 判定（○/×）をクリックして切り替え、右側の欄に具体的な理由や気づきを記入してください。")

for item in eval_items:
    with st.expander(f"🔍 {item}", expanded=True):
        col1, col2 = st.columns(2)
        
        # NJSSの評価
        with col1:
            st.markdown(f"**【NJSS】**")
            c1_1, c1_2 = st.columns([1, 4])
            with c1_1:
                if st.button("○/×", key=f"btn_njss_{item}"):
                    st.session_state.results[item]["NJSS"]["judge"] = "○" if st.session_state.results[item]["NJSS"]["judge"] == "×" else "×"
                st.write(f"判定: **{st.session_state.results[item]['NJSS']['judge']}**")
            with c1_2:
                st.session_state.results[item]["NJSS"]["note"] = st.text_input(
                    "メモ", value=st.session_state.results[item]["NJSS"]["note"], key=f"note_njss_{item}", placeholder="例：検索漏れなし"
                )

        # 入札王の評価
        with col2:
            st.markdown(f"**【入札王】**")
            c2_1, c2_2 = st.columns([1, 4])
            with c2_1:
                if st.button("○/×", key=f"btn_king_{item}"):
                    st.session_state.results[item]["入札王"]["judge"] = "○" if st.session_state.results[item]["入札王"]["judge"] == "×" else "×"
                st.write(f"判定: **{st.session_state.results[item]['入札王']['judge']}**")
            with c2_2:
                st.session_state.results[item]["入札王"]["note"] = st.text_input(
                    "メモ", value=st.session_state.results[item]["入札王"]["note"], key=f"note_king_{item}", placeholder="例：予算書が便利"
                )

# --- 集計とエクスポート ---
st.markdown("---")
st.subheader("📊 最終集計結果")

# 表示用データフレームの作成
summary_data = []
for item in eval_items:
    summary_data.append({
        "評価項目": item,
        "NJSS判定": st.session_state.results[item]["NJSS"]["judge"],
        "NJSSメモ": st.session_state.results[item]["NJSS"]["note"],
        "入札王判定": st.session_state.results[item]["入札王"]["judge"],
        "入札王メモ": st.session_state.results[item]["入札王"]["note"]
    })
df = pd.DataFrame(summary_data)

st.table(df)

# CSVエクスポート
csv = df.to_csv(index=False).encode('utf-8-sig')
st.download_button(
    label="📩 評価結果をCSV（スプレッドシート用）でダウンロード",
    data=csv,
    file_name="bid_tool_poc_summary.csv",
    mime="text/csv",
)
