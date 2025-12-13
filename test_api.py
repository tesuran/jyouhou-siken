import requests

url = "https://sharousi-kakomon.com/q/check_q_a.php"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://sharousi-kakomon.com",
    "Referer": "https://sharousi-kakomon.com/q/2016/0/1/a",
}
data = {"q": "20160101", "a": "1"}

print(f"POSTing to {url} with data {data}")
response = requests.post(url, headers=headers, data=data)

print(f"Status Code: {response.status_code}")
print("Response Text Preview:")
print(response.text[:1000])
