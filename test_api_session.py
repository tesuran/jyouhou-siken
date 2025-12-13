import requests

session = requests.Session()
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
session.headers.update(headers)

# 1. Visit main page to get cookies
url_main = "https://sharousi-kakomon.com/q/2016/0/1/a"
print(f"Visiting {url_main}...")
resp_main = session.get(url_main)
print(f"Main Page Status: {resp_main.status_code}")

# 2. POST to API
url_api = "https://sharousi-kakomon.com/q/check_q_a.php"
headers_api = {
    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://sharousi-kakomon.com",
    "Referer": url_main,
}

data = {"q": "20160101", "a": "1"}

print(f"POSTing to {url_api}...")
resp_api = session.post(url_api, headers=headers_api, data=data)

print(f"API Status: {resp_api.status_code}")
print("Response Text Preview:")
print(resp_api.text[:1000])
