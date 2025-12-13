import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin


def find_and_inspect(url):
    print(f"Inspecting: {url}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
    }

    s = requests.Session()
    r = s.get(url, headers=headers)

    # Save raw page source
    with open("debug_page_source_last.html", "w", encoding="utf-8") as f:
        f.write(r.text)

    soup = BeautifulSoup(r.text, "html.parser")

    # Check if this is a list page
    if "/data/" in url:
        print("This is a list page. Finding first question link...")
        links = soup.find_all("a", href=re.compile(r"/q/\d+"))
        if links:
            target_href = links[0].get("href")
            full_target = urljoin(url, target_href)
            print(f"Found question link: {full_target}")
            # Recurse
            find_and_inspect(full_target)
            return

    # Assuming this is a question page
    q_id = None
    inputs = soup.find_all("input", onclick=True)
    for inp in inputs:
        match = re.search(r"answer\((\d+),", inp["onclick"])
        if match:
            q_id = match.group(1)
            break

    if q_id:
        print(f"Found QID: {q_id}")
        api_url = "https://sharousi-kakomon.com/q/check_q_a.php"
        data = {"q": q_id, "a": "1"}
        api_headers = headers.copy()
        api_headers["Origin"] = "https://sharousi-kakomon.com"
        api_headers["Referer"] = url

        resp = s.post(api_url, headers=api_headers, data=data)
        print(f"API Status: {resp.status_code}")

        with open("debug_kaisetsu.html", "w", encoding="utf-8") as f:
            f.write(resp.text)
        print("Saved debug_kaisetsu.html")

        soup_api = BeautifulSoup(resp.text, "html.parser")
        kaisetsu = soup_api.find("div", class_="kaisetu")
        if kaisetsu:
            print("\n--- Kaisetsu HTML snippet ---")
            print(kaisetsu.prettify()[:1000])

            tables = kaisetsu.find_all("table")
            print(f"\nTables found: {len(tables)}")

            if not tables:
                # Check for div tables
                div_table = kaisetsu.find_all(
                    "div", class_=lambda x: x and "table" in x
                )
                print(f"Divs with 'table' in class: {len(div_table)}")
    else:
        print("QID not found on this page.")


if __name__ == "__main__":
    # 失敗しているURLを調査
    find_and_inspect("https://sharousi-kakomon.com/q/2018/0/10/c")
