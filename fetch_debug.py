import requests
from bs4 import BeautifulSoup
import re

url = "https://sharousi-kakomon.com/q/2013/0/5/a"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

s = requests.Session()
r = s.get(url, headers=headers)
print(f"Page status: {r.status_code}")

# Extract q_id
q_id = None
match = re.search(r"answer\((\d+),", r.text)
if match:
    q_id = match.group(1)
    print(f"Found q_id: {q_id}")
else:
    print("q_id not found")
    exit()

# Get explanation
api_url = "https://sharousi-kakomon.com/q/check_q_a.php"
headers["X-Requested-With"] = "XMLHttpRequest"
headers["Referer"] = url

data = {"q": q_id, "a": "1"}
resp = s.post(api_url, headers=headers, data=data)
print(f"API status: {resp.status_code}")

soup = BeautifulSoup(resp.text, "html.parser")
kaisetu = soup.find("div", class_="kaisetu")
if kaisetu:
    print(kaisetu.prettify())
else:
    print("Kaisetu div not found in API response")
