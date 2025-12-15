import requests
from bs4 import BeautifulSoup
import sys

# ユーザー提示のURL（令和7年春）が実在するか確認しつつ、だめなら平成28年秋などを試す
urls_to_try = [
    "https://www.ap-siken.com/kakomon/07_haru/q1.html",  # ユーザー提示
    "https://www.ap-siken.com/kakomon/28_aki/q1.html",  # ユーザー提示の範囲
    "https://www.ap-siken.com/kakomon/27_aki/q1.html",  # ユーザー提示の範囲
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}


def inspect_url(url):
    print(f"--- Inspecting: {url} ---")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            print("Status: 200 OK")
            soup = BeautifulSoup(response.text, "html.parser")

            # 1. Page Title
            print(
                f"Title: {soup.title.get_text(strip=True) if soup.title else 'No Title'}"
            )

            # 2. Main Question Part
            # 多くのサイトで main, article, #main などのIDが使われる
            # ap-siken.com の構造を推測して探す
            q_div = soup.find("div", id="mainCol")  # 推測
            if not q_div:
                q_div = soup.find("main")

            if q_div:
                print("Found main content area")
                # 問題文
                question_part = q_div.find("div", id="mondai")  # 推測
                if question_part:
                    print(
                        f"Question Text Preview: {question_part.get_text(strip=True)[:50]}..."
                    )

                # 選択肢 (ア, イ, ウ, エ)
                # 通常 ul li や div で構成される
                options = q_div.find_all("div", class_="select_list")  # 推測
                if options:
                    print(f"Found {len(options)} option containers")

            # 3. Answer/Explanation
            # "正解を表示する" ボタン周辺
            # 隠し要素で解説があるか？ "kaisetsu", "answer" などのクラス
            answer_area = soup.find("div", id="answerChar")  # 推測 (正解文字)
            kaisetsu_area = soup.find("div", id="kaisetsu")  # 推測 (解説)

            if answer_area:
                print(f"Answer Char: {answer_area.get_text(strip=True)}")
            else:
                print("Answer Char element NOT found directly.")

            if kaisetsu_area:
                print(
                    f"Explanation Preview: {kaisetsu_area.get_text(strip=True)[:50]}..."
                )
                print("Explanation is embedded in HTML.")
            else:
                print(
                    "Explanation element NOT found directly. Might be fetched dynamically."
                )

            # HTMLの一部を保存して構造確認
            with open("ap_siken_debug.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            print("Saved HTML to ap_siken_debug.html")

            return True
        else:
            print(f"Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False


for url in urls_to_try:
    if inspect_url(url):
        break
