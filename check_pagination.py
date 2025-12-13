import requests
from bs4 import BeautifulSoup

url = "https://sharousi-kakomon.com/data/1"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.text, "html.parser")

print(f"Title: {soup.title.text}")

# Look for pagination links (e.g., "next", "page", or just numbers)
paginations = soup.find_all("div", class_="pagination")
if paginations:
    print(f"Found Pagination Div: {paginations}")
else:
    print("No specific 'pagination' class found. Checking generic links...")
    # Check for links with params like ?page=
    links = soup.find_all("a", href=True)
    page_links = [l["href"] for l in links if "page=" in l["href"] or "p=" in l["href"]]
    print(f"Potential page links: {page_links[:10]}")

# Count total questions on this page
q_links = soup.find_all("a", href=lambda h: h and "/q/" in h)
print(f"Total Question Links on Page: {len(q_links)}")
