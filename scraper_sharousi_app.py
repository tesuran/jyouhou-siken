import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
import random
import re
import json
import os

import concurrent.futures
import socket
from urllib.parse import urljoin

try:
    from pyngrok import ngrok  # 外部アクセス用
except ImportError:
    ngrok = None

# page config
st.set_page_config(page_title="社労士過去問スクレイパー", page_icon="📝")

st.title("📝 社労士過去問 スクレイパー & カード作成")
st.markdown(
    "指定された過去問ページの「問題」と「解説」を取得し、AIでフラッシュカードを作成します。"
)

# 定数定義
SAVE_FILE = "sharousi_data.json"


def load_data_with_retry(filepath, retries=3, delay=0.5):
    """
    ファイルを読み込む際、競合エラーが発生したらリトライする関数
    """
    for i in range(retries):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError, PermissionError):
            if i < retries - 1:
                time.sleep(delay)
            else:
                return []
    return []


# Sidebar
st.sidebar.markdown("## 📊 収集状況")
if os.path.exists(SAVE_FILE):
    try:
        d = load_data_with_retry(SAVE_FILE)
        st.sidebar.metric("総カード数", f"{len(d)} 枚")

        # Breakdown
        subjects = {}
        for x in d:
            s = x.get("subject", "不明")
            subjects[s] = subjects.get(s, 0) + 1

        if subjects:
            st.sidebar.markdown("### 科目別")
            st.sidebar.bar_chart(subjects)
    except Exception:
        st.sidebar.caption("データ読み込み中...")
else:
    st.sidebar.caption("データなし")

st.sidebar.markdown("---")

# スマホ接続用情報表示
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip_addr = s.getsockname()[0]
    s.close()
    st.sidebar.markdown("### 📱 スマホで見るとき")
    st.sidebar.info(f"スマホのブラウザで以下にアクセス:\n\nhttp://{ip_addr}:8501")

    # QRコード表示
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=http://{ip_addr}:8501"
    st.sidebar.image(qr_url, caption="スマホでスキャンして接続")

    st.sidebar.caption("※同じWi-Fiに接続してください")
except Exception:
    pass

st.sidebar.markdown("---")

# --- 外部アクセス機能 (ngrok) ---
st.sidebar.markdown("### 🌐 屋外からアクセス")
with st.sidebar.expander("外部公開設定 (ngrok)"):
    st.caption("外出先からアクセスするにはngrokの設定が必要です。")
    st.markdown(
        "[ngrok公式サイト](https://dashboard.ngrok.com/get-started/your-authtoken) でAuthtokenを取得してください。"
    )

    # Token保存用ファイル
    TOKEN_FILE = ".ngrok_token"
    saved_token = ""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            saved_token = f.read().strip()

    auth_token = st.text_input("Authtokenを入力", value=saved_token, type="password")

    if st.button("設定を保存 & 接続開始"):
        if auth_token:
            # Token保存
            with open(TOKEN_FILE, "w") as f:
                f.write(auth_token)

            try:
                # ngrok設定
                if ngrok:
                    ngrok.set_auth_token(auth_token)

                    # 既存のトンネルを確認して閉じる (再起動時用)
                    tunnels = ngrok.get_tunnels()
                    for t in tunnels:
                        ngrok.disconnect(t.public_url)

                    # トンネル開始 (ポート8501)
                    public_url = ngrok.connect(8501).public_url
                    st.session_state["ngrok_url"] = public_url
                    st.success("接続しました！")
                else:
                    st.error(
                        "現在この環境ではngrokライブラリが利用できません(requirements.txtを確認してください)"
                    )

            except Exception as e:
                st.error(f"接続エラー: {e}")
        else:
            st.warning("Authtokenを入力してください。")

    # 接続済みならQR表示
    if "ngrok_url" in st.session_state:
        pub_url = st.session_state["ngrok_url"]
        st.success("🌐 公開中")
        st.code(pub_url)

        # QRコード
        qr_ngrok = (
            f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={pub_url}"
        )
        st.image(qr_ngrok, caption="外出先からスキャン")

        if st.button("切断する"):
            if ngrok:
                ngrok.kill()
            del st.session_state["ngrok_url"]
            st.rerun()

st.sidebar.markdown("---")


target_url = st.text_input(
    "対象URL (例: https://sharousi-kakomon.com/data/1)",
    "https://sharousi-kakomon.com/data/1",
)

st.sidebar.markdown("---")
max_count = st.sidebar.slider(
    "取得する問題数 (通常モードのみ有効)",
    1,
    100,
    10,
    help="「作成開始」ボタンでの実行時のみ適用されます。全自動クローラーでは無視されます（無制限）。",
)
sleep_min = st.sidebar.slider("待機時間(最小)", 2.0, 5.0, 3.0)
sleep_max = st.sidebar.slider("待機時間(最大)", 5.0, 15.0, 6.0)


def parse_html_text(element):
    """
    HTML要素からテキストを抽出し、赤文字・緑文字をStreamlitのMarkdown記法に変換する
    """
    if not element:
        return ""

    text = ""
    for child in element.contents:
        if child.name is None:  # Text Node
            text += child.string if child.string else ""
        elif child.name == "br":
            text += "\n"
        else:
            # Recursive parse
            inner_text = parse_html_text(child)

            # Check color
            color = ""
            cls = child.get("class", [])
            if isinstance(cls, str):
                cls = [cls]

            style = child.get("style", "").lower()

            # 赤・緑の判定 (クラス名やスタイル)
            # 判明しているクラス: clr2 -> 赤
            styles_str = style.lower()
            classes_set = set([c.lower() for c in cls])

            if (
                "clr2" in classes_set
                or any("red" in c for c in classes_set)
                or "color:red" in styles_str
                or "color: red" in styles_str
                or "#ff0000" in styles_str
            ):
                color = "red"
            elif (
                any("green" in c for c in classes_set)
                or "color:green" in styles_str
                or "color: green" in styles_str
            ):
                color = "green"

            # テーブルが含まれている場合（Markdownのセパレータ等で判定）、色指定で囲むと崩れるのでスキップ
            if "| --- |" in inner_text or "\n| " in inner_text:
                color = ""  # 強制的に無効化

            if color:
                text += f":{color}[{inner_text}]"
            else:
                text += inner_text

    return text


def get_explanation(session, q_id, referer_url):
    """APIを叩いて解説を取得する"""
    api_url = "https://sharousi-kakomon.com/q/check_q_a.php"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://sharousi-kakomon.com",
        "Referer": referer_url,
    }
    data = {"q": q_id, "a": "1"}  # 1=Maru, 0=Batsu (Either returns explanation)

    try:
        # タイムアウト延長
        resp = session.post(api_url, headers=headers, data=data, timeout=15)
        if resp.status_code == 200:
            # Response is HTML snippet
            soup = BeautifulSoup(resp.text, "html.parser")
            kaisetsu_div = soup.find("div", class_="kaisetu")
            joubun_div = soup.find("div", class_="joubun")
            point_div = soup.find("div", class_="point")

            # 何も取得できなかった場合は、APIレスポンス不正の可能性がある
            if not kaisetsu_div and not joubun_div and not point_div:
                # レスポンスが極端に短い場合はエラー扱い
                if len(resp.text) < 50:
                    return "APIエラー: レスポンス不正(Empty)", "", ""
                # 十分な長さがあるなら「解説なし」かもしれないが、念のため

            kaisetsu_text = (
                parse_html_text(kaisetsu_div).strip()
                if kaisetsu_div
                else "解説が見つかりませんでした"
            )
            joubun_text = parse_html_text(joubun_div).strip() if joubun_div else ""
            point_text = parse_html_text(point_div).strip() if point_div else ""

            return kaisetsu_text, joubun_text, point_text
        else:
            return f"APIエラー: {resp.status_code}", "", ""
    except Exception as e:
        return f"通信エラー: {e}", "", ""


def generate_rewrite(question, explanation, article="", point=""):
    """
    ユーザー要望:
    表面: ポイント + 解説 + 条文 (要約なし)
    裏面: ソースURL (呼び出し元で設定)
    """

    # AIを使用せず、そのまま結合して返す
    components = []

    # ポイント
    if point:
        components.append(f"【ポイント】\n{point}")

    # 解説
    components.append(f"【解説】\n{explanation}")

    # 条文
    if article:
        components.append(f"【条文】\n{article}")

    front_text = "\n\n---\n".join(components)

    return front_text, explanation


# --- メイン処理 ---
tab1, tab2, tab3 = st.tabs(
    ["🚀 通常スクレイピング", "📂 保存データ確認", "🤖 全自動クローラー"]
)

# 保存ファイルのパス
# SAVE_FILE は上部で定義済み

bulk_progress_file = "bulk_progress.json"

with tab3:
    st.header("🤖 全自動クローラー (全問取得)")
    st.warning(
        "⚠️ この機能はサイト内の全問題を順番に取得します。非常に時間がかかります。"
    )

    # 前回進捗の読み込み
    default_subject = 1
    default_page = 1
    if os.path.exists(bulk_progress_file):
        try:
            with open(bulk_progress_file, "r", encoding="utf-8") as f:
                prog = json.load(f)
                default_subject = prog.get("subject", 1)
                default_page = prog.get("page", 1)
        except Exception:
            pass

    col1, col2 = st.columns(2)
    with col1:
        start_subject = st.number_input("開始科目ID (1-10)", 1, 10, default_subject)
        start_page = st.number_input("開始ページ", 1, 100, default_page)
    with col2:
        # ランダム待機の幅設定
        wait_min = st.number_input("待機(最小)秒", 3.0, 10.0, 5.0)
        wait_max = st.number_input("待機(最大)秒", 5.0, 30.0, 10.0)

    # オプション
    stop_every_subject = st.checkbox("1科目完了ごとに一時停止する (推奨)", value=True)

    # 停止ボタン用プレースホルダー
    stop_placeholder = st.empty()

    # 進行状況表示
    status_text = st.empty()
    progress_bar_bulk = st.progress(0)

    # リセットボタン (追記) - ループの外
    st.markdown("---")
    with st.expander("⚠️ データのリセット（最初からやり直す場合）"):
        st.warning(
            "「全データを削除」を押すと、これまでに保存したカードデータと進捗がすべて消えます。"
        )
        if st.button("🗑️ 全データを削除してリセット"):
            if os.path.exists(SAVE_FILE):
                os.remove(SAVE_FILE)
            if os.path.exists(bulk_progress_file):
                os.remove(bulk_progress_file)

            st.cache_data.clear()
            st.success("データを削除しました。ページをリロードしてください。")
            time.sleep(1)
            st.rerun()

    # データ修復ボタン
    st.markdown("---")
    with st.expander("🛠️ データ修復（解説取得失敗などをリトライ）"):
        st.info(
            "AI生成エラーなどで表面が正しく保存されなかったカードを、再度サイトから問題文を取得して修正します。"
        )
        if st.button("🔧 データの修復を開始"):
            if os.path.exists(SAVE_FILE):
                try:
                    data = load_data_with_retry(SAVE_FILE)

                    count_fixed = 0
                    count_unfixable = 0
                    repair_bar = st.progress(0)
                    status_repair = st.empty()

                    session_repair = requests.Session()
                    session_repair.headers.update(
                        {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                        }
                    )

                    # 修復が必要かどうかを判定する関数
                    def is_broken(card):
                        front = card.get("front", "")
                        if not front:
                            return True

                        # 1. 既知のエラーメッセージ
                        error_keywords = [
                            "解説が見つかりませんでした",
                            "解説情報がありませんでした",  # 追加
                            "解説取得失敗",
                            "APIエラー",
                            "通信エラー",
                        ]
                        if any(k in front for k in error_keywords):
                            return True

                        # 2. 解説ヘッダーがない
                        if "【解説】" not in front:
                            return True

                        # 3. 解説の中身が空（【解説】の直後に【条文】が来る、または末尾）
                        try:
                            parts = front.split("【解説】")
                            if len(parts) > 1:
                                after_kaisetsu = parts[1]
                                # 【条文】があればそこまで、なければ最後まで
                                if "【条文】" in after_kaisetsu:
                                    content = after_kaisetsu.split("【条文】")[0]
                                else:
                                    content = after_kaisetsu

                                # 空白を除いて空っぽならアウト
                                if not content.strip():
                                    return True
                        except Exception:
                            pass

                        return False

                    # 修復対象を特定
                    targets = [i for i, c in enumerate(data) if is_broken(c)]

                    if not targets:
                        st.success("修復が必要なデータは見つかりませんでした。")
                    else:
                        st.info(
                            f"{len(targets)} 件のデータを並列修復しています... (最大5並列)"
                        )

                        repair_bar = st.progress(0)
                        status_repair = st.empty()

                        count_fixed = 0
                        count_unfixable = 0
                        count_processed = 0
                        total_targets = len(targets)

                        def repair_single_card(target_info):
                            """並列実行用関数"""
                            idx, card = target_info
                            url = card.get("source")
                            if not url:
                                return idx, None, "URLなし", False, False

                            local_session = requests.Session()
                            local_session.headers.update(
                                {
                                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                                }
                            )

                            max_retries = 5
                            for attempt in range(max_retries):
                                try:
                                    time.sleep(random.uniform(2.0, 5.0))
                                    r = local_session.get(url, timeout=15)
                                    if r.status_code == 200:
                                        soup_r = BeautifulSoup(r.text, "html.parser")
                                        q_div = soup_r.find("div", class_="q_body")
                                        question_text = (
                                            q_div.get_text(strip=True) if q_div else ""
                                        )

                                        q_id = None
                                        inputs = soup_r.find_all("input", onclick=True)
                                        for inp in inputs:
                                            match = re.search(
                                                r"answer\((\d+),", inp["onclick"]
                                            )
                                            if match:
                                                q_id = match.group(1)
                                                break

                                        if q_id:
                                            (
                                                explanation_text,
                                                article_text,
                                                point_text,
                                            ) = get_explanation(
                                                local_session, q_id, url
                                            )

                                            if (
                                                "APIエラー" in explanation_text
                                                or "通信エラー" in explanation_text
                                            ):
                                                continue

                                            is_missing_msg = (
                                                "解説が見つかりませんでした"
                                                in explanation_text
                                                or "解説情報がありませんでした"
                                                in explanation_text
                                                or "解説取得失敗" in explanation_text
                                            )
                                            has_sub_info = bool(
                                                article_text or point_text
                                            )

                                            final_exp = explanation_text
                                            if is_missing_msg and not has_sub_info:
                                                final_exp = "（公式に解説情報がありませんでした）"

                                            new_front, _ = generate_rewrite(
                                                question_text,
                                                final_exp,
                                                article_text,
                                                point_text,
                                            )
                                            card["front"] = new_front

                                            is_unfixable = (
                                                is_missing_msg and not has_sub_info
                                            )
                                            return (
                                                idx,
                                                card,
                                                f"完了: {url}",
                                                True,
                                                is_unfixable,
                                            )
                                        else:
                                            pass
                                    elif r.status_code == 404:
                                        card["front"] += "\n(ページが削除されています)"
                                        return idx, card, "404 Not Found", True, True

                                except Exception:
                                    time.sleep(1)

                            return idx, None, f"失敗: {url}", False, False

                        with concurrent.futures.ThreadPoolExecutor(
                            max_workers=5
                        ) as executor:
                            target_infos = [(i, data[i].copy()) for i in targets]
                            future_to_idx = {
                                executor.submit(repair_single_card, info): info[0]
                                for info in target_infos
                            }

                            for future in concurrent.futures.as_completed(
                                future_to_idx
                            ):
                                idx, new_card, msg, success, unfixable = future.result()
                                count_processed += 1
                                repair_bar.progress(count_processed / total_targets)
                                status_repair.write(
                                    f"修復中... {count_processed}/{total_targets} (成功: {count_fixed}, 解説なし: {count_unfixable})"
                                )

                                if success:
                                    if new_card:
                                        data[idx] = new_card
                                    if unfixable:
                                        count_unfixable += 1
                                    else:
                                        count_fixed += 1

                                if count_processed % 10 == 0:
                                    try:
                                        with open(
                                            SAVE_FILE, "w", encoding="utf-8"
                                        ) as f:
                                            json.dump(
                                                data, f, ensure_ascii=False, indent=2
                                            )
                                    except Exception:
                                        pass

                        with open(SAVE_FILE, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)

                        st.success(
                            f"修復完了！ {count_fixed} 件を修正、{count_unfixable} 件を解説なしとしてマークしました。"
                        )
                        time.sleep(2)
                        st.rerun()

                except Exception as e:
                    st.error(f"修復中にエラーが発生しました: {e}")
            else:
                st.warning("データファイルがありません。")

    # 全データ更新ボタン（表形式適用など）
    st.markdown("---")
    with st.expander("🔄 全データの強制更新 (表形式の適用など)"):
        st.warning(
            "すべてのデータを再取得して上書きします。完了まで非常に時間がかかります。途中で止める場合はブラウザを閉じてください。"
        )
        if st.button("🚨 全データを再取得・更新する"):
            if os.path.exists(SAVE_FILE):
                try:
                    data = load_data_with_retry(SAVE_FILE)

                    # 全件対象
                    targets = list(range(len(data)))

                    count_updated = 0
                    update_bar = st.progress(0)
                    status_update = st.empty()

                    session_update = requests.Session()
                    session_update.headers.update(
                        {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                        }
                    )

                    for idx, i in enumerate(targets):
                        card = data[i]
                        url = card.get("source")
                        if url:
                            status_update.write(
                                f"更新中 ({idx + 1}/{len(targets)}): {url}"
                            )
                            # リトライロジック
                            max_retries = 3
                            for attempt in range(max_retries):
                                try:
                                    r = session_update.get(url, timeout=10)
                                    if r.status_code == 200:
                                        soup_r = BeautifulSoup(r.text, "html.parser")
                                        q_div = soup_r.find("div", class_="q_body")
                                        question_text = (
                                            q_div.get_text(strip=True) if q_div else ""
                                        )

                                        # q_id を取得
                                        q_id = None
                                        inputs = soup_r.find_all("input", onclick=True)
                                        for inp in inputs:
                                            match = re.search(
                                                r"answer\((\d+),", inp["onclick"]
                                            )
                                            if match:
                                                q_id = match.group(1)
                                                break

                                        if q_id:
                                            # 解説を再取得 (ここで新しいMarkdown変換が適用される)
                                            (
                                                explanation_text,
                                                article_text,
                                                point_text,
                                            ) = get_explanation(
                                                session_update, q_id, url
                                            )

                                            # 成功したら更新
                                            if "解説取得失敗" not in explanation_text:
                                                front, _ = generate_rewrite(
                                                    question_text,
                                                    explanation_text,  # Markdown変換済み
                                                    article_text,
                                                    point_text,
                                                )
                                                data[i]["front"] = front
                                                count_updated += 1
                                                break

                                    elif r.status_code == 404:
                                        break

                                except Exception:
                                    # print(f"Error attempt {attempt}: {e}")
                                    time.sleep(1)

                        update_bar.progress((idx + 1) / len(targets))

                        # 中間保存 (10件ごと)
                        if (idx + 1) % 10 == 0:
                            try:
                                with open(SAVE_FILE, "w", encoding="utf-8") as f:
                                    json.dump(data, f, ensure_ascii=False, indent=2)
                            except Exception:
                                pass

                        time.sleep(0.5)  # 負荷軽減

                    # 最終保存
                    with open(SAVE_FILE, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)

                    st.success(
                        f"全データの更新が完了しました！ ({count_updated} 件更新)"
                    )
                    time.sleep(2)
                    st.rerun()

                except Exception as e:
                    st.error(f"更新中にエラーが発生しました: {e}")
            else:
                st.warning("データファイルがありません。")

    if st.button("全自動スクレイピング開始", key="bulk_start"):
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )

        # 既存データ読み込み
        all_cards = []
        if os.path.exists(SAVE_FILE):
            try:
                all_cards = load_data_with_retry(SAVE_FILE)
            except Exception:
                pass

        existing_urls = set([c.get("source") for c in all_cards])

        stop_button = stop_placeholder.button("⛔ 停止する", key="stop_bulk")

        try:
            # APIエラーカウンター初期化
            api_error_count = 0

            # 科目ループ (1~10: 労働基準法, 安衛法 etc...)
            for subject_id in range(start_subject, 11):
                page = start_page if subject_id == start_subject else 1

                while True:  # ページループ
                    # 進捗保存
                    try:
                        with open(bulk_progress_file, "w", encoding="utf-8") as f:
                            json.dump({"subject": subject_id, "page": page}, f)
                    except Exception:
                        pass

                    list_url = (
                        f"https://sharousi-kakomon.com/data/{subject_id}?page={page}"
                    )
                    status_text.text(f"巡回中... 科目ID: {subject_id}, ページ: {page}")

                    # リストページ取得
                    resp = session.get(list_url)
                    if resp.status_code != 200:
                        st.error(f"ページ取得エラー: {list_url}")
                        break

                    soup = BeautifulSoup(resp.text, "html.parser")

                    # 科目名
                    page_title = (
                        soup.title.get_text(strip=True) if soup.title else "不明"
                    )
                    subject_name = page_title.split("-")[0]

                    # データ抽出
                    rows = soup.find_all("tr")
                    page_items = []
                    for row in rows:
                        cols = row.find_all("td")
                        if len(cols) >= 3:
                            level_text = cols[2].get_text(strip=True)
                            link_tag = row.find("a", href=re.compile(r"/q/\d+"))
                            if link_tag:
                                href = link_tag.get("href")
                                full_url = urljoin(list_url, href)
                                if full_url not in existing_urls:
                                    page_items.append(
                                        {
                                            "url": full_url,
                                            "level": level_text,
                                            "subject": subject_name,
                                        }
                                    )

                    if not page_items:
                        # 問題が見つからない = ページ切れの可能性
                        status_text.write(
                            f"科目ID {subject_id} のページ {page} に問題がありません。次の科目へ移動します。"
                        )
                        break

                    # 各問題をスクレイピング
                    for i, item in enumerate(page_items):
                        # ランダム待機 (Bot対策)
                        sleep_time = random.uniform(wait_min, wait_max)
                        status_text.info(f"待機中... {sleep_time:.1f}秒 (Bot回避用)")
                        time.sleep(sleep_time)

                        full_link = item["url"]
                        status_text.write(
                            f"[{subject_name}] P.{page} ({i + 1}/{len(page_items)}) 取得中"
                        )

                        # 詳細ページ
                        try:
                            q_resp = session.get(full_link)
                            q_soup = BeautifulSoup(q_resp.text, "html.parser")

                            q_div = q_soup.find("div", class_="q_body")
                            question_text = (
                                q_div.get_text(strip=True) if q_div else "取得失敗"
                            )

                            q_id = None
                            inputs = q_soup.find_all("input", onclick=True)
                            for inp in inputs:
                                match = re.search(r"answer\((\d+),", inp["onclick"])
                                if match:
                                    q_id = match.group(1)
                                    break

                            explanation_text = "解説取得失敗"
                            article_text = ""
                            point_text = ""

                            if q_id:
                                explanation_text, article_text, point_text = (
                                    get_explanation(session, q_id, full_link)
                                )

                            # AIなし、直接結合
                            front, _ = generate_rewrite(
                                question_text,
                                explanation_text,
                                article_text,
                                point_text,
                            )
                            # 裏面はソースURL
                            back = full_link

                            new_card = {
                                "front": front,
                                "back": back,
                                "source": full_link,
                                "subject": item["subject"],
                                "level": item["level"],
                            }
                            # 保存 (他プロセスでの変更を反映するため、都度読み込んで保存)
                            try:
                                current_data = load_data_with_retry(SAVE_FILE)
                                current_data.append(new_card)
                                with open(SAVE_FILE, "w", encoding="utf-8") as f:
                                    json.dump(
                                        current_data, f, ensure_ascii=False, indent=2
                                    )
                                # メモリ上のリストも更新(念のため)
                                all_cards = current_data
                            except Exception as e:
                                st.error(f"保存エラー: {e}")

                        except Exception as e:
                            st.write(f"エラースキップ: {e}")
                            continue

                    # 次のページへ
                    next_link = soup.find("a", string=re.compile("次へ"))
                    if not next_link:
                        next_link = soup.find("a", href=re.compile(f"page={page + 1}"))

                    if not next_link:
                        break

                    page += 1
                    time.sleep(random.uniform(2.0, 4.0))

                # 科目ループ終わり
                if stop_every_subject:
                    st.warning(
                        f"✅ 科目ID {subject_id} の全ページ取得が完了しました。「1科目ごとに一時停止」設定のため、ここでストップします。続きは ID {subject_id + 1} から開始してください。"
                    )
                    break

            st.success("全自動スクレイピングが完了しました！")

        except Exception as e:
            st.error(f"予期せぬエラーで停止しました: {e}")

with tab1:
    if st.button("作成開始", key="start_btn"):
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ... Chrome/91.0.4472.124"
            }
        )

        # UI Cleanup
        st.info("処理を開始しました。完了までお待ちください...")
        progress_bar = st.progress(0)
        log_expander = st.expander("詳細ログを表示", expanded=False)
        status_area = log_expander.empty()

        # 既存データを読み込む
        cards = []
        if os.path.exists(SAVE_FILE):
            try:
                cards = load_data_with_retry(SAVE_FILE)
            except Exception:
                pass

        try:
            # 1. リストページからリンクを取得
            status_area.write(f"リストページを取得中: {target_url}")
            resp = session.get(target_url)
            soup = BeautifulSoup(resp.text, "html.parser")

            page_title = soup.title.get_text(strip=True) if soup.title else "不明な科目"
            subject_name = page_title.split("-")[0]

            target_data = []

            rows = soup.find_all("tr")
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 3:
                    level_text = cols[2].get_text(strip=True)
                    link_tag = row.find("a", href=re.compile(r"/q/\d+"))
                    if link_tag:
                        href = link_tag.get("href")
                        if "/q/" in href and re.search(r"/q/\d+/\d+/\d+/[a-e]", href):
                            full_url = urljoin(target_url, href)
                            target_data.append(
                                {
                                    "url": full_url,
                                    "level": level_text,
                                    "subject": subject_name,
                                }
                            )

            unique_data = []
            seen_urls = set()
            for d in target_data:
                if d["url"] not in seen_urls:
                    unique_data.append(d)
                    seen_urls.add(d["url"])

            st.write(f"見つかった問題: {len(unique_data)} 件")
            targets_to_scrape = unique_data[:max_count]

            for i, item in enumerate(targets_to_scrape):
                full_link = item["url"]
                level = item["level"]
                subject = item["subject"]

                if i > 0:
                    wait_time = random.uniform(sleep_min, sleep_max)
                    status_area.write(f"待機中... ({wait_time:.1f}s)")
                    time.sleep(wait_time)

                status_area.write(
                    f"処理中 ({i + 1}/{len(targets_to_scrape)}): {full_link} (ランク: {level})"
                )

                # 2. 詳細ページ取得
                q_resp = session.get(full_link)
                q_soup = BeautifulSoup(q_resp.text, "html.parser")

                q_div = q_soup.find("div", class_="q_body")
                question_text = (
                    q_div.get_text(strip=True) if q_div else "問題文取得失敗"
                )

                q_id = None
                inputs = q_soup.find_all("input", onclick=True)
                for inp in inputs:
                    match = re.search(r"answer\((\d+),", inp["onclick"])
                    if match:
                        q_id = match.group(1)
                        break

                explanation_text = "解説取得失敗"
                article_text = ""
                point_text = ""

                if q_id:
                    explanation_text, article_text, point_text = get_explanation(
                        session, q_id, full_link
                    )

                # 4. 生成 (AIなし)
                front, _ = generate_rewrite(
                    question_text, explanation_text, article_text, point_text
                )
                back = full_link

                new_card = {
                    "front": front,
                    "back": back,
                    "source": full_link,
                    "subject": subject,
                    "level": level,
                }
                try:
                    current_cards = load_data_with_retry(SAVE_FILE)
                    current_cards.append(new_card)
                    with open(SAVE_FILE, "w", encoding="utf-8") as f:
                        json.dump(current_cards, f, ensure_ascii=False, indent=2)
                    cards = current_cards
                except Exception as e:
                    st.error(f"保存エラー: {e}")

                progress_bar.progress((i + 1) / len(targets_to_scrape))

            status_area.success(
                f"完了しました！ データは {SAVE_FILE} に自動保存されました。"
            )

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")

with tab2:
    st.header("📂 保存データ確認 (フラッシュカードモード)")
    if os.path.exists(SAVE_FILE):
        try:
            all_data = load_data_with_retry(SAVE_FILE)

            if not all_data:
                st.warning("データが空です。")
            else:
                # --- フィルタリング機能 (メインエリア配置) ---
                with st.expander("🔍 絞り込み検索 (科目・難易度)", expanded=False):
                    # 1. 科目フィルタ
                    available_subjects = sorted(
                        list(set([d.get("subject", "不明") for d in all_data]))
                    )
                    selected_subjects = st.multiselect(
                        "科目で絞り込み",
                        options=available_subjects,
                        default=available_subjects,
                    )

                    # 2. 難易度フィルタ
                    available_levels = sorted(
                        list(set([d.get("level", "不明") for d in all_data]))
                    )
                    selected_levels = st.multiselect(
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

                # --- Anki用エクスポート (Mobile対応) ---
                st.sidebar.markdown("---")
                st.sidebar.markdown("### 📱 スマホ学習用 (Anki)")
                if saved_data:
                    # CSV作成 (Front, Back, Tag)
                    csv_lines = []
                    for d in saved_data:
                        # 改行を<br>に置換 (Anki仕様)
                        f_txt = (
                            d.get("front", "").replace("\n", "<br>").replace('"', '""')
                        )
                        b_txt = (
                            d.get("back", "").replace("\n", "<br>").replace('"', '""')
                        )
                        tag = f"{d.get('subject', '不明')} {d.get('level', '-')}"
                        # CSV format: "Front","Back","Tag"
                        line = f'"{f_txt}","{b_txt}","{tag}"'
                        csv_lines.append(line)

                    csv_data = "\n".join(csv_lines)

                    st.sidebar.download_button(
                        label="Anki用CSVをダウンロード",
                        data=csv_data.encode("utf-8-sig"),  # BOM付きUTF-8
                        file_name="anki_cards.csv",
                        mime="text/csv",
                        help="AnkiDroid(Android)やAnkiMobile(iPhone)にインポートして使えます。文字化け防止のためBOM付きUTF-8で出力します。",
                    )

                st.caption(f"全 {len(all_data)} 件中、{len(saved_data)} 件を表示中")

                # --- 表示モード切り替え ---
                view_mode = st.radio(
                    "表示モード",
                    ["カードモード (1枚ずつ)", "一覧表示モード (リスト)"],
                    horizontal=True,
                )

                if view_mode == "カードモード (1枚ずつ)":
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

                        # メタデータ取得
                        subject_info = card.get("subject", "不明")
                        level_info = card.get("level", "-")

                        front_text = card["front"]
                        back_text = card["back"]
                        # source_url = card.get("source", "")

                        # エラー時のフォールバック
                        if (
                            front_text.startswith("AI生成エラー")
                            or "AI生成エラー" in front_text
                        ):
                            pass

                        # --- 画面レイアウト ---
                        # ヘッダーに科目とレベルを表示
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
                        # スライダー操作でインデックス変更
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

                        # 操作ボタン (3カラム)
                        col_prev, col_flip, col_next = st.columns([1, 2, 1])

                        with col_prev:
                            if st.button("⬅️ 前へ"):
                                st.session_state.card_idx = max(
                                    0, st.session_state.card_idx - 1
                                )
                                st.session_state.is_flipped = False
                                st.rerun()

                        with col_flip:
                            button_label = "答えを見る / 戻る 🔄"
                            if st.button(button_label, use_container_width=True):
                                st.session_state.is_flipped = (
                                    not st.session_state.is_flipped
                                )
                                st.rerun()

                        with col_next:
                            if st.button("次へ ➡️"):
                                st.session_state.card_idx = min(
                                    len(saved_data) - 1, st.session_state.card_idx + 1
                                )
                                st.session_state.is_flipped = False
                                st.rerun()

                else:
                    # --- 一覧表示モード ---
                    st.markdown("---")

                    if not saved_data:
                        st.warning("条件に一致するデータがありません。")
                    else:
                        # ページネーション設定
                        items_per_page = 50
                        total_pages = (len(saved_data) - 1) // items_per_page + 1

                        if "list_page" not in st.session_state:
                            st.session_state.list_page = 1

                        # ページ選択 (上部)
                        col_p1, col_p2 = st.columns([2, 1])
                        with col_p1:
                            st.markdown(
                                f"**全 {len(saved_data)} 件中、{items_per_page} 件ずつ表示**"
                            )
                        with col_p2:
                            st.session_state.list_page = st.number_input(
                                "ページ番号",
                                min_value=1,
                                max_value=total_pages,
                                value=st.session_state.list_page,
                            )

                        start_idx = (st.session_state.list_page - 1) * items_per_page
                        end_idx = min(start_idx + items_per_page, len(saved_data))

                        current_batch = saved_data[start_idx:end_idx]

                        for i, d in enumerate(current_batch):
                            global_idx = start_idx + i + 1
                            subject = d.get("subject", "不明")
                            level = d.get("level", "-")
                            front = d.get("front", "")
                            back_url = d.get("back", "")  # backはURLが入っている前提

                            # 問題文の１行目をタイトルにする（長すぎたらカット）
                            title_line = front.split("\n")[0]
                            if len(title_line) > 30:
                                title_line = title_line[:30] + "..."

                            label = f"No.{global_idx} [{subject}] {title_line}"

                            with st.expander(label):
                                st.markdown("#### 📝 問題")
                                st.text(
                                    front
                                )  # Markdownだと崩れることがあるのでtext推奨だが、要件次第。一旦textで。
                                st.markdown("---")
                                st.markdown("#### 💡 解説・リンク")
                                st.write(f"ランク: {level}")
                                st.link_button(
                                    f"🔗 元サイトを開く ({back_url})", back_url
                                )

                        # ページ選択 (下部)
                        st.markdown("---")
                        if total_pages > 1:
                            st.success(
                                f"現在: {st.session_state.list_page} / {total_pages} ページ"
                            )

        except Exception as e:
            st.error(f"読み込みエラー: {e}")
    else:
        st.info(
            "まだ保存されたデータはありません。「スクレイピング実行」タブで作成してください。"
        )
