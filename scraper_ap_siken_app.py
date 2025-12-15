import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
import random
import json
import os
import re
from urllib.parse import urljoin

# page config
st.set_page_config(
    page_title="応用情報技術者 過去問スクレイパー & 学習", page_icon="💻", layout="wide"
)

st.title("💻 応用情報技術者 過去問スクレイパー & 学習")

# 定数定義
SAVE_FILE = "ap_siken_data.json"
BASE_URL = "https://www.ap-siken.com"

# 年度リスト (新しい順)
EXAM_PERIODS = [
    # 令和
    ("07_haru", "令和7年春期"),
    ("06_aki", "令和6年秋期"),
    ("06_haru", "令和6年春期"),
    ("05_aki", "令和5年秋期"),
    ("05_haru", "令和5年春期"),
    ("04_aki", "令和4年秋期"),
    ("04_haru", "令和4年春期"),
    ("03_aki", "令和3年秋期"),
    ("03_haru", "令和3年春期"),
    ("02_aki", "令和2年秋期"),
    ("01_aki", "令和元年秋期"),
    # 平成
    ("31_haru", "平成31年春期"),
    ("30_aki", "平成30年秋期"),
    ("30_haru", "平成30年春期"),
    ("29_aki", "平成29年秋期"),
    ("29_haru", "平成29年春期"),
    ("28_aki", "平成28年秋期"),
    ("28_haru", "平成28年春期"),
    ("27_aki", "平成27年秋期"),
    ("27_haru", "平成27年春期"),
    ("26_aki", "平成26年秋期"),
    ("26_haru", "平成26年春期"),
    ("25_aki", "平成25年秋期"),
    ("25_haru", "平成25年春期"),
    ("24_aki", "平成24年秋期"),
    ("24_haru", "平成24年春期"),
    ("23_aki", "平成23年秋期"),
    ("23_toku", "平成23年特別"),
    ("22_aki", "平成22年秋期"),
    ("22_haru", "平成22年春期"),
    ("21_aki", "平成21年秋期"),
    ("21_haru", "平成21年春期"),
]


def load_data():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []


def save_data(data):
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# スクレイピング関数
def parse_question_page(url, session):
    try:
        resp = session.get(url, timeout=10)
        if resp.status_code != 200:
            return None, f"ステータスコード異常: {resp.status_code}"

        soup = BeautifulSoup(resp.text, "html.parser")

        # 1. 問題IDとタイトル
        title = soup.title.get_text(strip=True) if soup.title else ""

        # 2. 問題文
        question_text = ""
        mondai_elm_id = soup.find(id="mondai")
        if mondai_elm_id:
            question_text = mondai_elm_id.get_text(separator="\n", strip=True)

        else:
            # 午後: class="mondai" をすべて取得して結合
            mondai_divs = soup.find_all("div", class_="mondai")
            if mondai_divs:
                parts = []
                for div in mondai_divs:
                    prev = div.find_previous_sibling("h3")
                    if prev:
                        parts.append(f"【{prev.get_text(strip=True)}】")
                    parts.append(div.get_text(separator="\n", strip=True))
                question_text = "\n\n".join(parts)
            else:
                return None, "問題文解析失敗: #mondai も .mondai も見つかりません"

        # 3. 選択肢 (午前のみ)
        options_text = ""
        select_list = soup.find("ul", class_="selectList")
        if select_list:
            options = []
            for li in select_list.find_all("li"):
                btn = li.find("button", class_="selectBtn")
                val = btn.get_text(strip=True) if btn else ""

                content_span = li.find(
                    "span", id=lambda x: x and x.startswith("select_")
                )
                if content_span:
                    content = content_span.get_text(separator="", strip=True)
                else:
                    content = li.get_text(strip=True).replace(val, "", 1)

                options.append(f"{val}: {content}")
            options_text = "\n".join(options)

        # 4. 正解と解説
        answer_char = ""
        kaisetsu_text = ""

        # 午前
        ans_span = soup.find("span", id="answerChar")
        if ans_span:
            answer_char = ans_span.get_text(strip=True)

        kaisetsu_div_id = soup.find(id="kaisetsu")
        if kaisetsu_div_id:
            kaisetsu_text = kaisetsu_div_id.get_text(separator="\n", strip=True)

        else:
            # 午後
            kaisetsu_divs = soup.find_all("div", class_="kaisetsu")
            if kaisetsu_divs:
                parts_k = []
                for div in kaisetsu_divs:
                    parts_k.append(div.get_text(separator="\n", strip=True))
                kaisetsu_text = "\n\n---\n\n".join(parts_k)

            ans_spans = soup.find_all("span", id=re.compile(r"ans_\w+"))
            if ans_spans:
                ans_list = []
                for sp in ans_spans:
                    ans_list.append(sp.get_text(strip=True))
                answer_char = ", ".join(ans_list)

        # データ構築
        front = f"{question_text}"
        if options_text:
            front += f"\n\n---\n【選択肢】\n{options_text}"

        back = ""
        if answer_char:
            back += f"【正解】 {answer_char}\n\n"
        back += f"【解説】\n{kaisetsu_text}\n\n(出典: {url})"

        return {"front": front, "back": back, "source": url, "title": title}, "OK"

    except Exception as e:
        return None, f"エラー: {str(e)}"


# Sidebar: データ状況と設定
data = load_data()
st.sidebar.header("📊 データ状況")
st.sidebar.metric("保存済みカード数", f"{len(data)} 枚")

if st.sidebar.button("データをリセット"):
    if os.path.exists(SAVE_FILE):
        os.remove(SAVE_FILE)
        st.success("削除しました")
        st.rerun()

st.sidebar.markdown("---")


# --- Tabs ---
tab1, tab2 = st.tabs(["📚 学習モード", "🕷️ スクレイピング"])

# Tab 1: 学習モード
with tab1:
    if not data:
        st.info(
            "データがありません。「スクレイピング」タブでデータを取得してください。"
        )
    else:
        st.subheader("📚 フラッシュカード学習")

        # フィルタリング
        st.markdown("##### フィルタ設定")
        periods = sorted(
            list(set([d.get("period", "不明") for d in data])), reverse=True
        )
        selected_periods = st.multiselect("年度で絞り込み", periods, default=periods)

        filtered_data = [d for d in data if d.get("period") in selected_periods]

        if not filtered_data:
            st.warning("条件に一致するカードがありません。")
        else:
            # Session State
            if "card_idx" not in st.session_state:
                st.session_state.card_idx = 0
            if "is_flipped" not in st.session_state:
                st.session_state.is_flipped = False

            # インデックス調整
            if st.session_state.card_idx >= len(filtered_data):
                st.session_state.card_idx = 0

            current_card = filtered_data[st.session_state.card_idx]

            # UI
            st.markdown(
                f"**Card No. {st.session_state.card_idx + 1} / {len(filtered_data)}**"
            )
            st.caption(f"年度: {current_card.get('period', '-')}")

            # ナビゲーションスライダー
            new_idx = st.slider(
                "カード移動",
                1,
                len(filtered_data),
                st.session_state.card_idx + 1,
                label_visibility="collapsed",
            )
            if new_idx - 1 != st.session_state.card_idx:
                st.session_state.card_idx = new_idx - 1
                st.session_state.is_flipped = False
                st.rerun()

            # カード表示
            container = st.container(border=True)
            with container:
                # CSSでカードの高さを確保
                st.markdown(
                    """
                    <style>
                    .card-content {
                        min-height: 300px;
                        padding: 20px;
                        font-size: 1.1em;
                        line-height: 1.6;
                    }
                    </style>
                    """,
                    unsafe_allow_html=True,
                )

                if st.session_state.is_flipped:
                    st.markdown("<div class='card-content'>", unsafe_allow_html=True)
                    st.error("💡 正解・解説 (裏面)")
                    st.markdown(current_card.get("back", "解説なし"))
                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div class='card-content'>", unsafe_allow_html=True)
                    st.info("📝 問題 (表面)")
                    st.markdown(current_card.get("front", "問題なし"))
                    st.markdown("</div>", unsafe_allow_html=True)

            # 操作ボタン
            c1, c2, c3 = st.columns([1, 2, 1])
            with c1:
                if st.button("⬅️ 前へ"):
                    st.session_state.card_idx = max(0, st.session_state.card_idx - 1)
                    st.session_state.is_flipped = False
                    st.rerun()
            with c2:
                btn_label = (
                    "答えを見る 🔄"
                    if not st.session_state.is_flipped
                    else "問題に戻る 🔄"
                )
                if st.button(btn_label, use_container_width=True, type="primary"):
                    st.session_state.is_flipped = not st.session_state.is_flipped
                    st.rerun()
            with c3:
                if st.button("次へ ➡️"):
                    st.session_state.card_idx = min(
                        len(filtered_data) - 1, st.session_state.card_idx + 1
                    )
                    st.session_state.is_flipped = False
                    st.rerun()

# Tab 2: スクレイピング
with tab2:
    st.subheader("🕷️ データ取得設定")

    # 設定
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### 取得範囲")
        st.caption("指定した範囲の過去問リストを巡回します。")
        period_options = [label for code, label in EXAM_PERIODS]
        # デフォルト (R7春 ～ H27秋)
        idx_s = 0
        idx_e = len(period_options) - 1
        for i, (c, l) in enumerate(EXAM_PERIODS):
            if c == "07_haru":
                idx_s = i
            if c == "27_aki":
                idx_e = i

        sp_label = st.selectbox(
            "開始（新しい年度）", period_options, index=idx_s, key="sp"
        )
        ep_label = st.selectbox(
            "終了（古い年度）", period_options, index=idx_e, key="ep"
        )

    with c2:
        st.markdown("##### 待機設定 (Safety)")
        st.caption("サーバー負荷軽減とBot検知回避のため、ランダムに待機します。")
        s_min = st.slider("待機時間(最小)", 1.0, 5.0, 2.0, key="s_min")
        s_max = st.slider("待機時間(最大)", 3.0, 10.0, 5.0, key="s_max")

    # 対象期間抽出
    target_periods = []
    found = False
    for code, label in EXAM_PERIODS:
        if label == sp_label:
            found = True
        if found:
            target_periods.append((code, label))
        if label == ep_label:
            break

    if not target_periods:
        st.error("範囲指定が正しくありません")
    else:
        st.info(f"対象スキーム: {len(target_periods)} 期分")

    # 実行
    st.markdown("---")
    if st.button("🚀 スクレイピング開始", type="primary"):
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )

        progress_bar = st.progress(0)
        status_text = st.empty()
        stop_btn = st.button("⛔ 中断")

        existing_urls = set([d.get("source") for d in data])
        new_data_count = 0
        total_periods = len(target_periods)

        try:
            for p_idx, (code, label) in enumerate(target_periods):
                status_text.write(f"📂 {label} の問題一覧を取得中...")

                index_url = f"{BASE_URL}/kakomon/{code}/"
                try:
                    r = session.get(index_url, timeout=10)
                    if r.status_code != 200:
                        st.error(f"取得失敗: {label}")
                        continue

                    soup_idx = BeautifulSoup(r.text, "html.parser")
                    links = []
                    main_col = soup_idx.find("div", id="mainCol") or soup_idx

                    anchors = main_col.find_all("a", href=re.compile(r"q\d+\.html$"))
                    for a in anchors:
                        links.append(urljoin(index_url, a.get("href")))

                    pm_anchors = main_col.find_all(
                        "a", href=re.compile(r"pm\d+\.html$")
                    )
                    for a in pm_anchors:
                        links.append(urljoin(index_url, a.get("href")))

                    links = sorted(list(set(links)))

                    for l_idx, link in enumerate(links):
                        if stop_btn:
                            raise KeyboardInterrupt("Stop")

                        if link in existing_urls:
                            continue

                        # Random Wait
                        time.sleep(random.uniform(s_min, s_max))

                        status_text.write(
                            f"📝 [{label}] {l_idx + 1}/{len(links)}: {link}"
                        )

                        card_data, msg = parse_question_page(link, session)

                        if card_data:
                            card_data["period"] = label
                            data.append(card_data)
                            existing_urls.add(link)
                            new_data_count += 1
                            if new_data_count % 5 == 0:
                                save_data(data)
                        else:
                            st.warning(f"Error: {link} - {msg}")

                        tp = (p_idx + (l_idx + 1) / len(links)) / total_periods
                        progress_bar.progress(min(tp, 1.0))

                except KeyboardInterrupt:
                    st.warning("中断しました")
                    break
                except Exception as e:
                    st.error(f"Error: {e}")

        except KeyboardInterrupt:
            st.warning("中断しました")

        save_data(data)
        st.success(f"完了: {new_data_count} 件追加")
        st.rerun()

    # Preview
    st.markdown("---")
    st.caption("直近取得した20件")
    if data:
        preview_list = []
        for d in data[-20:]:
            preview_list.append(
                {
                    "年度": d.get("period", ""),
                    "問題": d.get("front", "")[:30] + "...",
                    "正解": d.get("back", "").split("\n")[0],
                }
            )
        st.table(preview_list)
