import requests
from bs4 import BeautifulSoup
import re

url = "https://sharousi-kakomon.com/data/1"  # List Page
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.text, "html.parser")

print("--- Title ---")
print(soup.title.text if soup.title else "No title")

print("\n--- Links and Surrounding Text/Images ---")
# Find links to q/ year
links = soup.find_all("a", href=re.compile(r"/q/\d+"))
for i, link in enumerate(links[:5]):  # Check first 5
    print(f"\nLink {i}: {link.get('href')}")
    print(f"Text: {link.get_text(strip=True)}")

    # Check siblings/parent for difficulty
    parent = link.parent
    print(f"Parent: {parent.name} class={parent.get('class')}")
    print(f"Parent Text: {parent.get_text(strip=True)}")

    # Check for img in parent
    imgs = parent.find_all("img")
    for img in imgs:
        print(f"  Img: src='{img.get('src')}' alt='{img.get('alt')}'")

    # Check previous/next siblings of parent (maybe table cells?)
    if parent.name == "td":
        siblings = parent.parent.find_all("td")
        for sib in siblings:
            print(
                f"  Row Cell: {sib.get_text(strip=True)} | Imgs: {[m.get('src') for m in sib.find_all('img')]}"
            )

print("\n--- H1/H2 Headers ---")
for h in soup.find_all(["h1", "h2"]):
    print(h.get_text(strip=True))
