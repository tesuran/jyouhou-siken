import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import os

# ページ設定
st.set_page_config(page_title="セーフティ・スクレイパー", page_icon="🕷️", layout="wide")

st.title("🕷️ セーフティ・スクレイパー (Rate Limit対策版)")
st.markdown("""
このアプリは、**サーバーへの負荷を最小限に抑えながら**データを取得するために設計されています。
ランダムな待機時間を設けることで、Bot検知やアクセス制限のリスクを低減します。
""")

# --- サイドバー設定 ---
st.sidebar.header("⚙️ スクレイピング設定")

# 1. URL設定
input_method = st.sidebar.radio(
    "URL入力方法", ["単一URL", "URLリスト(改行区切り)", "連番URL生成"]
)

target_urls = []

if input_method == "単一URL":
    url = st.sidebar.text_input("対象URL", "https://example.com")
    if url:
        target_urls = [url]

elif input_method == "URLリスト(改行区切り)":
    urls_text = st.sidebar.text_area(
        "URLリスト", "https://example.com/page1\nhttps://example.com/page2"
    )
    if urls_text:
        target_urls = [u.strip() for u in urls_text.split("\n") if u.strip()]

elif input_method == "連番URL生成":
    base_url = st.sidebar.text_input(
        "ベースURL (番号部分を {} にしてください)", "https://example.com/page/{}"
    )
    start_num = st.sidebar.number_input("開始番号", 1, 1000, 1)
    end_num = st.sidebar.number_input("終了番号", 1, 1000, 5)
    if base_url:
        target_urls = [base_url.format(i) for i in range(start_num, end_num + 1)]

st.sidebar.write(f"対象URL件数: **{len(target_urls)}** 件")

# 2. 抽出ルール
st.sidebar.subheader("抽出ルール (CSSセレクタ)")
selector_container = st.sidebar.text_input(
    "コンテナ (各アイテムを囲む要素)", "div.article"
)
selector_title = st.sidebar.text_input("タイトル/質問", "h2.title")
selector_content = st.sidebar.text_input("内容/答え", "div.content")

# 3. 待機設定（重要）
st.sidebar.subheader("⏱️ 待機設定 (Safety)")
min_sleep = st.sidebar.slider("最小待機時間 (秒)", 1.0, 10.0, 3.0)
max_sleep = st.sidebar.slider("最大待機時間 (秒)", 5.0, 30.0, 10.0)

# --- メイン処理 ---

if st.button("スクレイピング開始", type="primary"):
    if not target_urls:
        st.error("URLが設定されていません。")
    else:
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        # User-Agentの設定（重要）
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        stop_button = st.button("中断")

        for i, url in enumerate(target_urls):
            if stop_button:
                st.warning("処理を中断しました。")
                break

            # 1. ランダムWait (初回以外)
            if i > 0:
                sleep_time = random.uniform(min_sleep, max_sleep)
                status_text.write(f"⏳ 待機中... ({sleep_time:.2f}秒)")
                time.sleep(sleep_time)

            # 2. アクセス
            try:
                status_text.write(f"🔄 アクセス中 ({i + 1}/{len(target_urls)}): {url}")
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()  # エラーなら例外発生

                # 3. 解析
                soup = BeautifulSoup(response.content, "html.parser")

                # コンテナ単位で探すか、単一ページから探すか
                containers = soup.select(selector_container)

                if containers:
                    for item in containers:
                        title_elm = item.select_one(selector_title)
                        content_elm = item.select_one(selector_content)

                        title_text = (
                            title_elm.get_text(strip=True) if title_elm else "N/A"
                        )
                        content_text = (
                            content_elm.get_text(strip=True) if content_elm else "N/A"
                        )

                        results.append(
                            {"URL": url, "Title": title_text, "Content": content_text}
                        )
                else:
                    # コンテナが見つからない場合、ページ全体から1つ探す（詳細ページなどの場合）
                    title_elm = soup.select_one(selector_title)
                    content_elm = soup.select_one(selector_content)

                    if title_elm or content_elm:
                        results.append(
                            {
                                "URL": url,
                                "Title": title_elm.get_text(strip=True)
                                if title_elm
                                else "N/A",
                                "Content": content_elm.get_text(strip=True)
                                if content_elm
                                else "N/A",
                            }
                        )
                    else:
                        st.warning(f"データが見つかりませんでした: {url}")

            except Exception as e:
                st.error(f"エラー発生 ({url}): {e}")

            # プログレスバー更新
            progress_bar.progress((i + 1) / len(target_urls))

        status_text.text("✅ 完了しました！")

        # 結果表示とダウンロード
        if results:
            df = pd.DataFrame(results)
            st.success(f"{len(results)} 件のデータを取得しました。")
            st.dataframe(df)

            csv = df.to_csv(index=False).encode("utf-8_sig")
            st.download_button(
                label="CSVとしてダウンロード",
                data=csv,
                file_name="scraped_data.csv",
                mime="text/csv",
            )
        else:
            st.warning("データが取得できませんでした。セレクタを確認してください。")

with st.expander("使い方"):
    st.markdown("""
    1. **URL入力**: スクレイピングしたいURLを指定します。連番の場合は `https://site.com/page/{}` のように `{}` を使います。
    2. **セレクタ設定**: Chromeの検証ツール(F12)などで、取得したい要素のCSSセレクタを調べます。
       - `div.class_name` や `#id_name` など
    3. **待機設定**: サイトの負荷を考え、デフォルト(3~10秒)以上の時間を設定することをお勧めします。
    4. **実行**: 開始ボタンを押すと、ゆっくりとデータを収集します。
    """)
