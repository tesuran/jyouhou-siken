import streamlit as st
import json
import os

# page config
st.set_page_config(page_title="社労士過去問カードビューアー", page_icon="📝")

st.title("📝 社労士過去問 カードビューアー")
st.caption("作成済みのフラッシュカードデータを閲覧・学習するための専用モードです。")

# 定数定義
SAVE_FILE = "sharousi_data.json"

# Sidebar
st.sidebar.markdown("## 📊 データ状況")
if os.path.exists(SAVE_FILE):
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        st.sidebar.metric("総カード数", f"{len(d)} 枚")

        # Breakdown
        subjects = {}
        for x in d:
            s = x.get("subject", "不明")
            subjects[s] = subjects.get(s, 0) + 1

        if subjects:
            st.sidebar.markdown("### 科目別")
            st.sidebar.bar_chart(subjects)
    except:
        st.sidebar.caption("データ読み込みエラー")
else:
    st.sidebar.warning("データファイル (sharousi_data.json) が見つかりません。")
    st.sidebar.info("このアプリと同じフォルダにデータを配置してください。")

st.sidebar.markdown("---")

# Main Viewer Logic
if os.path.exists(SAVE_FILE):
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            all_data = json.load(f)

        if not all_data:
            st.warning("データが空です。")
        else:
            # --- フィルタリング機能 ---
            st.sidebar.markdown("### 🔍 フィルタ")

            # 1. 科目フィルタ
            available_subjects = sorted(
                list(set([d.get("subject", "不明") for d in all_data]))
            )
            selected_subjects = st.sidebar.multiselect(
                "科目で絞り込み",
                options=available_subjects,
                default=available_subjects,
            )

            # 2. 難易度フィルタ
            available_levels = sorted(
                list(set([d.get("level", "不明") for d in all_data]))
            )
            selected_levels = st.sidebar.multiselect(
                "難易度で絞り込み",
                options=available_levels,
                default=available_levels,
            )

            # フィルタリング実行 (AND条件)
            saved_data = [
                d
                for d in all_data
                if d.get("level", "不明") in selected_levels
                and d.get("subject", "不明") in selected_subjects
            ]

            # --- Anki用エクスポート ---
            st.sidebar.markdown("---")
            if saved_data:
                csv_lines = []
                for d in saved_data:
                    f_txt = d.get("front", "").replace("\n", "<br>").replace('"', '""')
                    b_txt = d.get("back", "").replace("\n", "<br>").replace('"', '""')
                    tag = f"{d.get('subject', '不明')} {d.get('level', '-')}"
                    line = f'"{f_txt}","{b_txt}","{tag}"'
                    csv_lines.append(line)

                csv_data = "\n".join(csv_lines)

                st.sidebar.download_button(
                    label="Anki用CSVをダウンロード",
                    data=csv_data,
                    file_name="anki_cards.csv",
                    mime="text/csv",
                )

            st.caption(f"全 {len(all_data)} 件中、{len(saved_data)} 件を表示中")

            if not saved_data:
                st.warning("条件に一致するカードがありません。")
            else:
                # --- Session State 初期化 ---
                if "card_idx" not in st.session_state:
                    st.session_state.card_idx = 0
                if "is_flipped" not in st.session_state:
                    st.session_state.is_flipped = False

                # 範囲チェック
                if st.session_state.card_idx >= len(saved_data):
                    st.session_state.card_idx = 0

                # 現在のカードデータを取得
                card = saved_data[st.session_state.card_idx]

                subject_info = card.get("subject", "不明")
                level_info = card.get("level", "-")
                front_text = card.get("front", "")
                back_text = card.get("back", "")

                # --- 画面レイアウト ---
                st.markdown(f"#### 🏷️ {subject_info} / ランク: {level_info}")
                st.markdown(
                    f"**No. {st.session_state.card_idx + 1} / {len(saved_data)}**"
                )

                new_index = st.slider(
                    "カード移動",
                    min_value=1,
                    max_value=len(saved_data),
                    value=st.session_state.card_idx + 1,
                    label_visibility="collapsed",
                )
                if new_index - 1 != st.session_state.card_idx:
                    st.session_state.card_idx = new_index - 1
                    st.session_state.is_flipped = False
                    st.rerun()

                # カード表示エリア
                card_container = st.container(border=True)
                with card_container:
                    if st.session_state.is_flipped:
                        st.markdown("### 💡 ソースURL (裏面)")
                        st.code(back_text, language=None)
                        st.link_button("元サイトを開く", back_text)
                    else:
                        st.markdown("### 📝 カード内容 (表面)")
                        st.markdown(front_text)

                # 操作ボタン
                col_prev, col_flip, col_next = st.columns([1, 2, 1])

                with col_prev:
                    if st.button("⬅️ 前へ"):
                        st.session_state.card_idx = max(
                            0, st.session_state.card_idx - 1
                        )
                        st.session_state.is_flipped = False
                        st.rerun()

                with col_flip:
                    if st.button("答えを見る / 戻る 🔄", use_container_width=True):
                        st.session_state.is_flipped = not st.session_state.is_flipped
                        st.rerun()

                with col_next:
                    if st.button("次へ ➡️"):
                        st.session_state.card_idx = min(
                            len(saved_data) - 1, st.session_state.card_idx + 1
                        )
                        st.session_state.is_flipped = False
                        st.rerun()

    except Exception as e:
        st.error(f"読み込みエラー: {e}")
else:
    st.info("データがありません。")
