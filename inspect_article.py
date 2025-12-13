import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

session = requests.Session()
list_url = "https://sharousi-kakomon.com/data/1"

try:
    print(f"Fetching list: {list_url}")
    resp = session.get(list_url, headers=headers)
    soup = BeautifulSoup(resp.text, "html.parser")

    # Find a valid question link
    link = soup.find("a", href=re.compile(r"/q/\d+"))

    if link:
        href = link.get("href")
        full_url = urljoin(list_url, href)
        print(f"Inspecting Question: {full_url}")

        q_resp = session.get(full_url, headers=headers)
        q_soup = BeautifulSoup(q_resp.text, "html.parser")

        # 1. Search for text "表示切替"
        print("\n--- Search for '表示切替' ---")
        elements = q_soup.find_all(string=re.compile("表示切替"))
        for e in elements:
            parent = e.parent
            if parent:
                print(f"Found '表示切替' in: {parent.name}, {parent.attrs}")
                print(f"Parent HTML: {parent.prettify()[:300]}")

        # 2. Look for Scripts
        print("\n--- Scripts ---")
        scripts = q_soup.find_all("script")
        found_ajax = False
        for s in scripts:
            if s.string and ("ajax" in s.string or "load" in s.string):
                print(f"Script content: {s.string.strip()[:200]}...")
                found_ajax = True

        if not found_ajax:
            print("No obvious AJAX scripts found.")

        # 3. Check for specific ID 'joubun' or similar
        print("\n--- ID checks ---")
        ids = [tag.get("id") for tag in q_soup.find_all(True) if tag.get("id")]
        print(f"IDs found: {ids}")

        # 4. Check for 'block_kaisetu' or similar structure
        print("\n--- Kaisetu Area ---")
        kaisetu = q_soup.find("div", class_="kaisetu")
        if kaisetu:
            print("Found div.kaisetu")
            # Look for siblings
            next_sib = kaisetu.find_next_sibling()
            if next_sib:
                print(
                    f"Next Sibling to Kaisetu: {next_sib.name}, class={next_sib.get('class')}"
                )
                print(f"Content: {next_sib.get_text(strip=True)[:100]}")

    else:
        print("Could not find any question link on the list page.")

except Exception as e:
    print(f"Error: {e}")
