import streamlit as st
import pandas as pd

st.set_page_config(page_title="入札ツールPoC試験エディタ", layout="wide")

st.title("🧪 入札ツールPoC：試験シナリオ＆実測評価")
st.caption("株式会社ジール様向け：仕様・精度・運用負荷の実測検証ボード")

# --- 試験シナリオの定義 ---
scenarios = {
    "1. 検索精度（DX/ETL）": {
        "scenario": "キーワード『ETL』『データ基盤』『DX推進』で検索し、ノイズ（無関係な案件）が混入しないか確認する。",
        "check_point": "ヒット件数の妥当性と、検索フィルタの使い勝手",
        "input_label": "ヒット件数（件）"
    },
    "2. 通知の速報性": {
        "scenario": "特定機関をフォローし、公示から何時間後に通知メールが届くか計測する。",
        "check_point": "メール受信時刻と公示時刻の差分",
        "input_label": "平均通知ラグ（時間）"
    },
    "3. 過去データの深掘り": {
        "scenario": "過去3年間の『システム開発』案件を検索し、落札価格と応札企業一覧が揃っているか確認する。",
        "check_point": "CSV出力した際のデータ欠損の有無",
        "input_label": "データ充足率（%）"
    },
    "4. 予算書からの予兆管理": {
        "scenario": "次年度の予算書情報をキーワード検索し、将来的な案件化の可能性を早期発見できるか試す。",
        "check_point": "予算書から具体的な案件名が特定できるか",
        "input_label": "発見できた有望案件数（件）"
    },
    "5. チーム連携の負荷": {
        "scenario": "気になる案件を『お気に入り』に入れ、コメントを付けて社内共有するフローを試す。",
        "check_point": "共有リンクの開きやすさや、ステータス変更の容易性",
        "input_label": "操作ステップ数（クリック数）"
    }
}

if 'results' not in st.session_state:
    st.session_state.results = {
        name: {
            "NJSS": {"value": 0, "judge": "×", "note": ""},
            "入札王": {"value": 0, "judge": "×", "note": ""}
        } for name in scenarios.keys()
    }

# --- メイン画面 ---
st.info("💡 各シナリオに基づき実測値を入力し、総合的な判断で○/×を選択してください。")

for name, info in scenarios.items():
    with st.expander(f"📖 シナリオ：{name}", expanded=True):
        st.write(f"**試験内容:** {info['scenario']}")
        st.write(f"**着眼点:** {info['check_point']}")
        
        col1, col2 = st.columns(2)
        
        # NJSSの入力
        with col1:
            st.markdown("🟡 **NJSS**")
            val_njss = st.number_input(f"{info['input_label']} ", key=f"val_njss_{name}", min_value=0)
            c1, c2 = st.columns([1, 4])
            with c1:
                if st.button("判定切替", key=f"btn_njss_{name}"):
                    st.session_state.results[name]["NJSS"]["judge"] = "○" if st.session_state.results[name]["NJSS"]["judge"] == "×" else "×"
                st.write(f"判定: **{st.session_state.results[name]['NJSS']['judge']}**")
            with c2:
                st.session_state.results[name]["NJSS"]["note"] = st.text_area(
                    "検証メモ", key=f"note_njss_{name}", placeholder="例：検索結果は多いが、一部保守案件が混ざる"
                )

        # 入札王の入力
        with col2:
            st.markdown("🔵 **入札王**")
            val_king = st.number_input(f"{info['input_label']}  ", key=f"val_king_{name}", min_value=0)
            c1, c2 = st.columns([1, 4])
            with c1:
                if st.button("判定切替", key=f"btn_king_{name}"):
                    st.session_state.results[name]["入札王"]["judge"] = "○" if st.session_state.results[name]["入札王"]["judge"] == "×" else "×"
                st.write(f"判定: **{st.session_state.results[name]['入札王']['judge']}**")
            with c2:
                st.session_state.results[name]["入札王"]["note"] = st.text_area(
                    "検証メモ", key=f"note_king_{name}", placeholder="例：予算書から来年度の大型案件を2件特定"
                )

# --- エクスポート ---
st.markdown("---")
summary_data = []
for name in scenarios.keys():
    summary_data.append({
        "試験項目": name,
        "NJSS実測値": st.session_state.results[name]["NJSS"]["value"],
        "NJSS判定": st.session_state.results[name]["NJSS"]["judge"],
        "NJSS備考": st.session_state.results[name]["NJSS"]["note"],
        "入札王実測値": st.session_state.results[name]["入札王"]["value"],
        "入札王判定": st.session_state.results[name]["入札王"]["judge"],
        "入札王備考": st.session_state.results[name]["入札王"]["note"]
    })
df = pd.DataFrame(summary_data)

st.subheader("📊 試験結果サマリー")
st.table(df)

csv = df.to_csv(index=False).encode('utf-8-sig')
st.download_button("📩 試験結果をCSVでダウンロード", data=csv, file_name="poc_test_report.csv", mime="text/csv")
