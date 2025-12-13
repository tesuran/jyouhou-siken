import requests
from bs4 import BeautifulSoup
import re

url = "https://sharousi-kakomon.com/data/1"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.text, "html.parser")

print(f"Title: {soup.title.get_text(strip=True)}")

# Check items count
rows = soup.find_all("tr")
question_links = []
for row in rows:
    link = row.find("a", href=re.compile(r"/q/\d+"))
    if link:
        question_links.append(link.get("href"))
print(f"Questions found on page 1: {len(question_links)}")

# Check Pagination
pagination = soup.find("div", class_="pagination")
if pagination:
    print("Pagination DIV found.")
    links = pagination.find_all("a")
    for l in links:
        print(
            f"Pagination Link: text='{l.get_text(strip=True)}', href='{l.get('href')}'"
        )
else:
    print("Pagination DIV NOT FOUND.")

# Check for other pagination styles
pg_nav = soup.find("nav", attrs={"aria-label": "Page navigation"})
if pg_nav:
    print("Found 'nav' pagination.")
else:
    # Try finding any link with 'page=2'
    p2 = soup.find("a", href=re.compile(r"page=2"))
    if p2:
        print(f"Found explicit page 2 link: {p2}")
    else:
        print("No page 2 link found anywhere.")
