import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection
import io
import csv
import traceback

# --- 1. UI & CSS (アイコン・白枠完全消去 & シンプルモダンUI) ---
st.set_page_config(page_title="入札ツール精密評価ボード", layout="wide")

st.markdown("""
    <style>
    /* 1. 上部白枠（ヘッダー）の完全排除 */
    [data-testid="stHeader"] { display: none !important; }
    [data-testid="stAppViewContainer"] { padding-top: 0rem !important; background-color: #FFFFFF !important; }
    [data-testid="block-container"] { padding-top: 2rem !important; padding-bottom: 2rem !important; }

    /* 全体の文字色 */
    .stApp { color: #181818 !important; }
    
    /* サイドバー配色 */
    [data-testid="stSidebar"] { background-color: #1E293B !important; border-right: none !important; }
    [data-testid="stSidebar"] * { color: #CBD5E1 !important; }
    .sidebar-section-header { color: #64748B !important; font-size: 11px !important; font-weight: 700; letter-spacing: 1px; padding: 10px 15px; margin: 20px 0px 5px 0px; text-transform: uppercase; }

    /* ラジオボタンの「丸いボタン」を完全に消し去る */
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label > div:first-child { display: none !important; }
    
    /* メニュー項目をモダンなテキストリンク風に */
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label { padding: 12px 16px !important; margin-bottom: 4px !important; border-radius: 6px !important; background-color: transparent; transition: all 0.2s ease-in-out !important; cursor: pointer; width: 100%; display: block; }
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover { background-color: rgba(255, 255, 255, 0.08) !important; color: #FFFFFF !important; }
    [data-testid="stSidebar"] div.stRadio p { color: #F8FAFC !important; font-size: 14px !important; font-weight: 500 !important; margin: 0 !important; }

    /* 2. ページヘッダーの装飾 (Salesforce Lightning風) */
    .slds-page-header { 
        background-color: #F8FAFC !important; 
        padding: 1.2rem 2rem; 
        border-bottom: 1px solid #E2E8F0; 
        margin: -2rem -4rem 2rem -4rem; 
        border-left: 8px solid #0284C7; 
    }
    .slds-page-header h1 { color: #0F172A !important; font-size: 1.5rem; font-weight: 700; margin: 0; }
    
    /* ボタン・入力ボックスのデザイン */
    .stButton > button { background-color: #0284C7 !important; color: #FFFFFF !important; border-radius: 6px !important; font-weight: 600 !important; border: none !important; padding: 0.5rem 1.5rem !important; transition: all 0.2s ease; }
    .stButton > button:hover { background-color: #0369A1 !important; transform: translateY(-1px); box-shadow: 0 4px 6px rgba(2, 132, 199, 0.2); }
    div[data-baseweb="input"], div[data-baseweb="input"] > div, div[data-baseweb="base-input"], input, textarea { background-color: #F8FAFC !important; color: #0F172A !important; border-color: #CBD5E1 !important; border-radius: 6px !important; }
    div[data-baseweb="input"]:focus-within { border-color: #0284C7 !important; }
    div[data-baseweb="button-group"] button { background-color: #F1F5F9 !important; color: #0F172A !important; }
    </style>
    """, unsafe_allow_html=True)

# --- セッション状態の初期化 ---
if 'search_words' not in st.session_state: st.session_state.search_words = ["DX推進", "データ分析基盤"]
if 'search_counts' not in st.session_state: st.session_state.search_counts = {}
if 'costs' not in st.session_state: 
    st.session_state.costs = {
        "n_init": 0, "n_month": 0, "n_opt": 0,
        "k_init": 0, "k_month": 0, "k_opt": 0,
        "margin": 20
    }

# --- 2. スプレッドシート接続 ---
conn = st.connection("gsheets", type=GSheetsConnection)

CORRECT_COLUMNS = ["ID", "自治体名", "案件概要", "仕様書", "予算(千円)", "落札金額(千円)", "落札企業", "応札1", "応札2", "応札3", "NJSS掲載", "入札王掲載", "URL1", "URL2", "URL3", "URL4", "URL5"]

def load_data():
    try:
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        df = conn.read(spreadsheet=url, ttl="0s")
        if "自治体名" not in df.columns: 
            return pd.DataFrame([{col: "" if col != "ID" else i+1 for col in CORRECT_COLUMNS} for i in range(50)])
        for col in ["URL1", "URL2", "URL3", "URL4", "URL5"]:
            if col not in df.columns: df[col] = ""
        return df
    except Exception as e:
        return pd.DataFrame([{col: "" if col != "ID" else i+1 for col in CORRECT_COLUMNS} for i in range(50)])

# --- 3. サイドバーの構築 ---
with st.sidebar:
    st.markdown('<p class="sidebar-section-header">Menu</p>', unsafe_allow_html=True)
    test_mode = st.toggle("テストモード表示")
    
    menu_options = ["ダッシュボード", "過去案件情報入力", "ワード検索数", "コスト・ROI分析", "マニュアル"]
    if test_mode: menu_options.append("データ管理 (テスト)")

    page = st.radio("メニュー", menu_options, label_visibility="collapsed")

def draw_kpi_card(title, value):
    st.markdown(f"""
        <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 1.5rem; text-align: center; margin-bottom: 1.5rem;">
            <p style="color: #64748B; font-size: 13px; font-weight: 600; margin: 0 0 8px 0; text-transform: uppercase;">{title}</p>
            <p style="color: #0284C7; font-size: 36px; font-weight: 700; margin: 0; line-height: 1;">{value}</p>
        </div>
    """, unsafe_allow_html=True)

# --- 4. コンテンツ表示 ---

if page == "ダッシュボード":
    st.markdown('<div class="slds-page-header"><h1>ダッシュボード</h1></div>', unsafe_allow_html=True)
    
    df = load_data()
    valid_df = df[df["自治体名"].notna() & (df["自治体名"] != "")]

    if valid_df.empty:
        st.warning("データがありません。左のメニューから「過去案件情報入力」を開き、検証結果を登録してください。")
    else:
        st.write("以下のダッシュボードは、入力された実測データに基づきリアルタイムに更新されます。")
        kpi1, kpi2, kpi3 = st.columns(3)
        nj_count = valid_df["NJSS掲載"].astype(str).str.upper().isin(["TRUE", "1", "1.0", "YES"]).sum()
        ki_count = valid_df["入札王掲載"].astype(str).str.upper().isin(["TRUE", "1", "1.0", "YES"]).sum()
        
        with kpi1: draw_kpi_card("NJSS 網羅率", f"{(nj_count/len(valid_df)*100):.1f}%")
        with kpi2: draw_kpi_card("入札王 網羅率", f"{(ki_count/len(valid_df)*100):.1f}%")
        with kpi3: draw_kpi_card("検証完了案件", f"{len(valid_df)} 件")

        chart_layout = dict(template="plotly_white", paper_bgcolor="white", plot_bgcolor="white", font=dict(color="#181818"), margin=dict(l=20, r=20, t=40, b=20))
        color_map = {"NJSS": "#0284C7", "入札王": "#F59E0B", "NJSS件数": "#0284C7", "入札王件数": "#F59E0B"}

        col_l, col_r = st.columns(2)
        with col_l:
            fig_hits = px.bar(x=["NJSS", "入札王"], y=[nj_count, ki_count], title="案件捕捉数の比較", color=["NJSS", "入札王"], color_discrete_map=color_map)
            fig_hits.update_layout(**chart_layout)
            st.plotly_chart(fig_hits, use_container_width=True)
            
        with col_r:
            comp_df = pd.concat([valid_df["落札企業"], valid_df["応札1"], valid_df["応札2"], valid_df["応札3"]])
            pres_df = comp_df[comp_df != ""].value_counts().reset_index()
            pres_df.columns = ["企業名", "出現回数"]
            fig_p = px.bar(pres_df.head(8), x="出現回数", y="企業名", orientation='h', title="競合出現シェア (TOP 8)")
            fig_p.update_traces(marker_color='#0284C7')
            fig_p.update_layout(**chart_layout)
            st.plotly_chart(fig_p, use_container_width=True)

        st.markdown('<div class="slds-page-header" style="margin-top: 3rem; margin-bottom: 2rem;"><h1>総合判定・結果分析</h1></div>', unsafe_allow_html=True)
        
        if st.button("総合判定を実行する", use_container_width=True):
            nj_cov_score = (nj_count / len(valid_df) * 100)
            ki_cov_score = (ki_count / len(valid_df) * 100)
            
            nj_search_win, ki_search_win = 0, 0
            for w, counts in st.session_state.search_counts.items():
                if counts["NJSS"] > counts["入札王"]: nj_search_win += 1
                elif counts["入札王"] > counts["NJSS"]: ki_search_win += 1
                else: nj_search_win += 0.5; ki_search_win += 0.5
            tot_search = nj_search_win + ki_search_win
            nj_search_score = (nj_search_win / tot_search * 100) if tot_search > 0 else 50
            ki_search_score = (ki_search_win / tot_search * 100) if tot_search > 0 else 50
            
            nj_ann = st.session_state.costs["n_init"] + (st.session_state.costs["n_month"] * 12) + st.session_state.costs["n_opt"]
            ki_ann = st.session_state.costs["k_init"] + (st.session_state.costs["k_month"] * 12) + st.session_state.costs["k_opt"]
            min_cost = min(nj_ann, ki_ann)
            nj_cost_score = (min_cost / nj_ann * 100) if nj_ann > 0 else 100
            ki_cost_score = (min_cost / ki_ann * 100) if ki_ann > 0 else 100
            if nj_ann == 0 and ki_ann == 0: nj_cost_score, ki_cost_score = 50, 50

            avg_bid = valid_df["落札金額(千円)"].mean() * 1000 if not valid_df.empty else 0
            profit = avg_bid * (st.session_state.costs["margin"] / 100)
            nj_roi = (profit - nj_ann) / nj_ann * 100 if nj_ann > 0 else 0
            ki_roi = (profit - ki_ann) / ki_ann * 100 if ki_ann > 0 else 0
            max_roi = max(nj_roi, ki_roi)
            nj_roi_score = (nj_roi / max_roi * 100) if max_roi > 0 and nj_roi > 0 else 0
            ki_roi_score = (ki_roi / max_roi * 100) if max_roi > 0 and ki_roi > 0 else 0
            if max_roi <= 0: nj_roi_score, ki_roi_score = 50, 50

            nj_total = nj_cov_score + nj_search_score + nj_cost_score + nj_roi_score
            ki_total = ki_cov_score + ki_search_score + ki_cost_score + ki_roi_score

            categories = ['網羅率', '検索精度', 'コストパフォーマンス', 'ROI(投資対効果)', '網羅率']
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(r=[nj_cov_score, nj_search_score, nj_cost_score, nj_roi_score, nj_cov_score], theta=categories, fill='toself', name='NJSS', line_color='#0284C7'))
            fig_radar.add_trace(go.Scatterpolar(r=[ki_cov_score, ki_search_score, ki_cost_score, ki_roi_score, ki_cov_score], theta=categories, fill='toself', name='入札王', line_color='#F59E0B'))
            fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=True, margin=dict(t=30, b=30))
            
            rc1, rc2 = st.columns([1, 1])
            with rc1:
                st.plotly_chart(fig_radar, use_container_width=True)
            with rc2:
                st.markdown("### 判定結果")
                if nj_total > ki_total: st.success("分析の結果、【 NJSS 】 の導入が推奨されます。")
                elif ki_total > nj_total: st.success("分析の結果、【 入札王 】 の導入が推奨されます。")
                else: st.info("分析の結果、両ツールは 【 互角 】 です。")
                
                st.markdown(f"""
                **各ツールの総合スコア (400点満点)**
                * **NJSS**: {nj_total:.1f} 点
                * **入札王**: {ki_total:.1f} 点
                <br><br>
                <small style="color:#64748B;">※ スコアは「過去案件の網羅率」「キーワード検索の勝敗」「年間コストの低さ」「平均落札額に基づくROI」の4指標を独自に点数化したものです。</small>
                """, unsafe_allow_html=True)

elif page == "過去案件情報入力":
    st.markdown('<div class="slds-page-header"><h1>過去案件情報入力</h1></div>', unsafe_allow_html=True)
    
    df_current = load_data()
    valid_df = df_current[df_current["自治体名"].notna() & (df_current["自治体名"] != "")].copy()
    next_id = len(valid_df) + 1

    if 'temp_df' in st.session_state and not st.session_state.temp_df.empty:
        st.warning(f"インポートされた {len(st.session_state.temp_df)} 件の未保存データがあります。")
        if st.button("インポートデータを一括保存する", use_container_width=True):
            try:
                import_data = st.session_state.temp_df.fillna("").replace({None: ""})
                updated_df = pd.concat([valid_df, import_data], ignore_index=True)
                url = st.secrets["connections"]["gsheets"]["spreadsheet"]
                conn.update(spreadsheet=url, data=updated_df)
                del st.session_state.temp_df
                st.success("インポートデータの保存が完了しました。")
                st.rerun()
            except Exception as e:
                st.error(f"保存に失敗しました。詳細エラー:\n```\n{traceback.format_exc()}\n```")

    st.write("以下のフォームに各項目の情報を入力し、「この案件を保存する」ボタンを押して1件ずつ登録してください。")

    with st.form("entry_form", clear_on_submit=True):
        st.markdown("#### 基本情報")
        c1, c2 = st.columns(2)
        with c1:
            municipality = st.text_input("自治体名 (必須)", placeholder="例：東京都")
            budget = st.number_input("予算 (単位: 千円)", min_value=0, step=100)
            st.markdown(f"<p style='color: #0284C7; font-size: 13px; margin-top: -10px;'>実際の金額: <b>{budget * 1000:,} 円</b></p>", unsafe_allow_html=True)
        with c2:
            summary = st.text_area("案件概要", placeholder="例：R6年度 システム改修", height=110)
        
        st.markdown("---")
        st.markdown("#### 落札・応札情報")
        c3, c4 = st.columns(2)
        with c3:
            winner = st.text_input("落札企業", placeholder="例：株式会社ジール")
            winning_bid = st.number_input("落札金額 (単位: 千円)", min_value=0, step=100)
            st.markdown(f"<p style='color: #0284C7; font-size: 13px; margin-top: -10px;'>実際の金額: <b>{winning_bid * 1000:,} 円</b></p>", unsafe_allow_html=True)
        with c4:
            bidder1 = st.text_input("応札企業 1")
            bidder2 = st.text_input("応札企業 2")
            bidder3 = st.text_input("応札企業 3")
        
        st.markdown("---")
        st.markdown("#### ツール掲載確認")
        c5, c6, c7 = st.columns(3)
        with c5: spec = st.checkbox("仕様書あり")
        with c6: njss_listed = st.checkbox("NJSS に掲載あり")
        with c7: king_listed = st.checkbox("入札王 に掲載あり")

        st.markdown("---")
        st.markdown("#### 参考URL")
        c8, c9 = st.columns(2)
        with c8:
            url1 = st.text_input("URL 1", placeholder="https://...")
            url3 = st.text_input("URL 3", placeholder="https://...")
            url5 = st.text_input("URL 5", placeholder="https://...")
        with c9:
            url2 = st.text_input("URL 2", placeholder="https://...")
            url4 = st.text_input("URL 4", placeholder="https://...")
            
        st.markdown("---")
        submitted = st.form_submit_button("この案件を保存する", use_container_width=True)

    if submitted:
        if not municipality:
            st.error("「自治体名」は必須項目です。入力してください。")
        else:
            new_record = pd.DataFrame([{
                "ID": next_id, "自治体名": municipality, "案件概要": summary, "仕様書": spec,
                "予算(千円)": budget, "落札金額(千円)": winning_bid, "落札企業": winner,
                "応札1": bidder1, "応札2": bidder2, "応札3": bidder3,
                "NJSS掲載": njss_listed, "入札王掲載": king_listed,
                "URL1": url1, "URL2": url2, "URL3": url3, "URL4": url4, "URL5": url5
            }]).fillna("")
            updated_df = pd.concat([valid_df, new_record], ignore_index=True)
            try:
                conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=updated_df)
                st.success(f"「{municipality}」のデータを保存しました。")
                st.rerun()
            except Exception as e:
                st.error(f"保存失敗:\n```\n{traceback.format_exc()}\n```")

    if not valid_df.empty:
        st.markdown("### 登録済みデータ一覧")
        st.dataframe(
            valid_df,
            column_config={
                "仕様書": st.column_config.CheckboxColumn("仕様書有"),
                "NJSS掲載": st.column_config.CheckboxColumn("NJSS確認"),
                "入札王掲載": st.column_config.CheckboxColumn("入札王確認"),
                "予算(千円)": st.column_config.NumberColumn(format="¥%d"),
                "落札金額(千円)": st.column_config.NumberColumn(format="¥%d"),
                "URL1": st.column_config.LinkColumn("URL 1"),
                "URL2": st.column_config.LinkColumn("URL 2"),
                "URL3": st.column_config.LinkColumn("URL 3"),
                "URL4": st.column_config.LinkColumn("URL 4"),
                "URL5": st.column_config.LinkColumn("URL 5"),
            },
            hide_index=True, use_container_width=True
        )

elif page == "ワード検索数":
    st.markdown('<div class="slds-page-header"><h1>ワード検索数</h1></div>', unsafe_allow_html=True)
    
    col_add1, col_add2 = st.columns([3, 1])
    new_word = col_add1.text_input("追加したい検索ワード", placeholder="例：BIツール", key="input_new_word", label_visibility="collapsed")
    if col_add2.button("ワードを追加", use_container_width=True):
        if new_word and new_word not in st.session_state.search_words:
            st.session_state.search_words.append(new_word)
            st.rerun()
            
    if st.button("リストをリセット"):
        st.session_state.search_words = []
        st.session_state.search_counts = {}
        st.rerun()

    st.markdown("---")

    if st.session_state.search_words:
        st.markdown("##### ヒット件数の実測値入力")
        search_data = []
        for word in st.session_state.search_words:
            if word not in st.session_state.search_counts: st.session_state.search_counts[word] = {"NJSS": 0, "入札王": 0}
            col_w1, col_w2 = st.columns(2)
            n_val = col_w1.number_input(f"NJSS: 【 {word} 】", min_value=0, value=st.session_state.search_counts[word]["NJSS"], key=f"n_{word}")
            k_val = col_w2.number_input(f"入札王: 【 {word} 】", min_value=0, value=st.session_state.search_counts[word]["入札王"], key=f"k_{word}")
            st.session_state.search_counts[word]["NJSS"] = n_val
            st.session_state.search_counts[word]["入札王"] = k_val
            search_data.append({"検索ワード": word, "NJSS件数": n_val, "入札王件数": k_val})
        
        st.table(pd.DataFrame(search_data))
        df_sw = pd.DataFrame(search_data)
        fig_sw = px.bar(df_sw, x="検索ワード", y=["NJSS件数", "入札王件数"], barmode="group", title="ワード別 ヒット件数比較", color_discrete_map={"NJSS件数": "#0284C7", "入札王件数": "#F59E0B"})
        fig_sw.update_layout(template="plotly_white", paper_bgcolor="white", plot_bgcolor="white", font=dict(color="#181818"), margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig_sw, use_container_width=True)

elif page == "コスト・ROI分析":
    st.markdown('<div class="slds-page-header"><h1>コスト・ROI分析</h1></div>', unsafe_allow_html=True)
    
    st.markdown("#### 各ツールのコスト設定")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**NJSS**")
        n_init = st.number_input("初期費用 (円)", value=st.session_state.costs["n_init"], step=10000)
        n_month = st.number_input("月額費用 (円)", value=st.session_state.costs["n_month"], step=10000)
        n_opt = st.number_input("年間オプション費用 (円)", value=st.session_state.costs["n_opt"], step=10000)
    with c2:
        st.markdown("**入札王**")
        k_init = st.number_input("初期費用 (円)", value=st.session_state.costs["k_init"], step=10000, key="k_i")
        k_month = st.number_input("月額費用 (円)", value=st.session_state.costs["k_month"], step=10000, key="k_m")
        k_opt = st.number_input("年間オプション費用 (円)", value=st.session_state.costs["k_opt"], step=10000, key="k_o")
    
    st.markdown("---")
    st.markdown("#### ROI（投資対効果）設定")
    st.write("過去案件データと自社の想定粗利率から、ツール費用を回収するために必要な件数（損益分岐点）を計算します。")
    margin = st.number_input("自社の想定粗利率 (%)", value=st.session_state.costs["margin"], min_value=1, max_value=100)

    if st.button("設定を保存して分析する", use_container_width=True):
        st.session_state.costs.update({"n_init": n_init, "n_month": n_month, "n_opt": n_opt, "k_init": k_init, "k_month": k_month, "k_opt": k_opt, "margin": margin})
        st.success("コスト・ROI設定を保存しました。ダッシュボードの総合判定にも反映されます。")

    n_annual = st.session_state.costs["n_init"] + (st.session_state.costs["n_month"] * 12) + st.session_state.costs["n_opt"]
    k_annual = st.session_state.costs["k_init"] + (st.session_state.costs["k_month"] * 12) + st.session_state.costs["k_opt"]

    df_current = load_data()
    valid_df = df_current[df_current["自治体名"].notna() & (df_current["自治体名"] != "")]
    avg_bid = valid_df["落札金額(千円)"].mean() * 1000 if not valid_df.empty else 0
    profit = avg_bid * (st.session_state.costs["margin"] / 100)

    st.markdown("---")
    st.markdown("### 分析結果レポート")
    r1, r2 = st.columns(2)
    with r1:
        st.markdown(f"<h4 style='color:#0284C7;'>NJSS 初年度コスト: {n_annual:,} 円</h4>", unsafe_allow_html=True)
        if profit > 0:
            break_even_n = n_annual / profit
            st.write(f"年間 **{break_even_n:.2f} 件** 落札すればツール費用を回収できます。")
        else:
            st.write("※ 過去案件データを入力すると損益分岐点が表示されます。")
            
    with r2:
        st.markdown(f"<h4 style='color:#F59E0B;'>入札王 初年度コスト: {k_annual:,} 円</h4>", unsafe_allow_html=True)
        if profit > 0:
            break_even_k = k_annual / profit
            st.write(f"年間 **{break_even_k:.2f} 件** 落札すればツール費用を回収できます。")
    
    st.write(f"※ 登録された過去案件の平均落札額は **{avg_bid:,.0f} 円** 、1件あたりの想定利益は **{profit:,.0f} 円** として計算しています。")

elif page == "マニュアル":
    st.markdown('<div class="slds-page-header"><h1>マニュアル</h1></div>', unsafe_allow_html=True)
    st.markdown("""
    ### 1. 本ツールの目的
    本ツールは、入札情報サービス（NJSS、入札王など）の導入検討に向けたPoCにおいて、各ツールの「網羅率」「検索精度」「コストパフォーマンス」「ROI」を定量的に比較・評価するための専用システムです。

    ### 2. 各メニューの利用方法
    * **ダッシュボード**: 全データの集計グラフと、レーダーチャートを用いた「総合判定機能」を利用できます。
    * **過去案件情報入力**: 過去の入札結果を1件ずつフォームから登録し、クラウドに蓄積します。
    * **ワード検索数**: 特定のキーワードでのヒット件数を比較記録します。
    * **コスト・ROI分析**: 各ツールの料金プランと自社の利益率を入力し、損益分岐点を自動計算します。
    """)

elif page == "データ管理 (テスト)":
    st.markdown('<div class="slds-page-header"><h1>データ管理 (テスト)</h1></div>', unsafe_allow_html=True)
    
    st.markdown("### CSVアップロード")
    uploaded_file = st.file_uploader("テスト用CSVファイルをアップロードしてください", type="csv")
    if uploaded_file:
        try:
            try: import_df = pd.read_csv(uploaded_file, encoding="utf-8")
            except:
                uploaded_file.seek(0)
                import_df = pd.read_csv(uploaded_file, encoding="shift-jis")
            
            if len(import_df.columns) == 1 and "," in import_df.columns[0]:
                uploaded_file.seek(0)
                try: import_df = pd.read_csv(uploaded_file, encoding="utf-8", quoting=csv.QUOTE_NONE)
                except:
                    uploaded_file.seek(0)
                    import_df = pd.read_csv(uploaded_file, encoding="shift-jis", quoting=csv.QUOTE_NONE)
                import_df.columns = import_df.columns.str.replace('"', '', regex=False)
                import_df = import_df.replace('"', '', regex=True)
                
            st.dataframe(import_df.head())
            if st.button("このデータを反映する"):
                st.session_state.temp_df = import_df
                st.success("反映しました。「過去案件情報入力」画面で一括保存してください。")
        except Exception as e: st.error("読込失敗")

    st.markdown("---")
    st.markdown("<h3 style='color: #DC2626;'>データの初期化</h3>", unsafe_allow_html=True)
    st.write("スプレッドシートのデータをすべて消去し初期状態に戻します。")
    if st.button("すべてのデータを消去する", use_container_width=True):
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        conn.update(spreadsheet=url, data=pd.DataFrame(columns=CORRECT_COLUMNS))
        if 'temp_df' in st.session_state: del st.session_state.temp_df
        st.success("初期化しました。")
        st.rerun()
