import requests
from bs4 import BeautifulSoup
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://sharousi-kakomon.com",
    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
}

session = requests.Session()
# 1. Get a QID from a page
start_url = "https://sharousi-kakomon.com/q/1"
# We need to find a VALID page that has questions.
# Let's try to get one from the list page first roughly.
list_url = "https://sharousi-kakomon.com/data/1"
resp = session.get(list_url, headers=headers)
soup = BeautifulSoup(resp.text, "html.parser")
link = soup.find("a", href=re.compile(r"/q/\d+"))

from urllib.parse import urljoin

if link:
    href = link.get("href")
    full_url = urljoin("https://sharousi-kakomon.com/data/1", href)
    print(f"Target Page: {full_url}")

    q_resp = session.get(full_url, headers=headers)
    q_soup = BeautifulSoup(q_resp.text, "html.parser")

    # Extract QID from onclick="answer(12345, ...)"
    inputs = q_soup.find_all("input", onclick=True)
    q_id = None
    for inp in inputs:
        match = re.search(r"answer\((\d+),", inp["onclick"])
        if match:
            q_id = match.group(1)
            break

    if q_id:
        print(f"Found QID: {q_id}")

        # 2. Call API
        api_url = "https://sharousi-kakomon.com/q/check_q_a.php"
        headers["Referer"] = full_url
        data = {"q": q_id, "a": "1"}  # Answer "1" (Maru)

        api_resp = session.post(api_url, headers=headers, data=data)
        print(f"API Context Type: {api_resp.headers.get('Content-Type')}")

        # Inspect API Response
        api_soup = BeautifulSoup(api_resp.text, "html.parser")

        print("\n--- API Response Text (Partial) ---")
        print(api_soup.prettify()[:1000])

        print("\n--- Searching for '条文' in API Response ---")
        found = api_soup.find_all(string=re.compile("条文"))
        for f in found:
            p = f.parent
            print(f"Found in: <{p.name} class={p.get('class')}> {f.strip()[:50]}...")

            # Print Siblings of this Parent
            print("  --- Siblings ---")
            for sib in p.find_next_siblings():
                print(f"  Sibling Tag: {sib.name}, Class: {sib.get('class')}")
                print(f"  Content: {sib.get_text(strip=True)[:100]}...")

    else:
        print("Could not find QID on the page.")
else:
    print("Could not find question link.")
