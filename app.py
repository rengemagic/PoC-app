import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import json

# ─────────────────────────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────────────────────────
st.set_page_config(page_title="入札 PoC Board", layout="wide")

# ─────────────────────────────────────────────────────────────────
#  DATA LAYER (構造修復機能付き)
# ─────────────────────────────────────────────────────────────────
conn = st.connection("gsheets", type=GSheetsConnection)
COLS_BIDS = ["ID","自治体名","担当部署名","案件概要","公示日","入札日","履行期間","入札方式","参加資格","予算(千円)","落札金額(千円)","自社結果","落札企業","競合1","競合2","競合3","仕様書","NJSS掲載","入札王掲載","URL1","URL2","URL3","URL4","URL5", "検索タグ", "備考"]
COLS_SETTINGS = ["種別", "項目名", "値1", "値2", "値3", "値4", "値5"]

def force_fix_spreadsheet():
    """スプレッドシートの構造をA1セルから強制的に作り直す"""
    try:
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        # 空の見出しデータを作成
        df_bids = pd.DataFrame(columns=COLS_BIDS)
        df_sets = pd.DataFrame(columns=COLS_SETTINGS)
        
        # 強制上書き
        conn.update(spreadsheet=url, worksheet="案件データ", data=df_bids)
        conn.update(spreadsheet=url, worksheet="設定データ", data=df_sets)
        return True
    except Exception as e:
        st.error(f"修復失敗: {e}")
        return False

# ─────────────────────────────────────────────────────────────────
#  MAIN UI (修復モード)
# ─────────────────────────────────────────────────────────────────
st.title("🚨 システム復旧モード")

with st.container(border=True):
    st.error("スプレッドシートの構造が崩れ、読み込みができない状態です。")
    st.markdown("""
    スプレッドシートを直接編集したことにより、アプリが「どこにデータがあるか」を見失っています。
    下のボタンを押すと、スプレッドシートの **『案件データ』『設定データ』シートをA1セルから正しい項目名で強制的に上書き** します。
    
    **※ 注意: 現在スプレッドシートに入っているデータは消去されます。**
    """)
    
    if st.button("強制的にスプレッドシートの構造を再構築する", type="primary", use_container_width=True):
        if force_fix_spreadsheet():
            st.success("スプレッドシートの構造を修復しました！")
            st.info("一度スプレッドシートを開いて、A1セルから項目名が並んでいるか確認してください。")
            st.balloons()
            if st.button("修復完了：アプリを再起動する"):
                # ここで元のメニューに戻るためのフラグを立てるか、リロードを促す
                st.rerun()

st.markdown("---")
st.caption("修復が完了したら、先ほどの【完全版】のコードを再度貼り付けてください。")
