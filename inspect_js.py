import requests
import re

url = "https://sharousi-kakomon.com/q/2016/0/1/a"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

response = requests.get(url, headers=headers)
html = response.text

print("--- JS Scripts Content ---")
scripts = re.findall(r"<script.*?>.*?</script>", html, re.DOTALL)
for s in scripts:
    if "answer" in s:
        print(f"Found 'answer' in script: {s[:500]}...")

# Also look for external script src
srcs = re.findall(r'<script[^>]+src="([^"]+)"', html)
print("External scripts:", srcs)

# Check if there is any hidden inputs that might hold the answer
hiddens = re.findall(r'<input type="hidden"[^>]+>', html)
print("Hidden inputs:", hiddens)
