import requests
import re

url = "https://sharousi-kakomon.com/q/2016/0/1/a"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

response = requests.get(url, headers=headers)
html = response.text

# Try to find the question text
print("--- Searching for Question ---")
# Usually question text is long, let's look for known text in the page content
# "労働条件は、労働者が人たるに値する生活を営むための必要を充たすべきものでなければならない。" (This is the likely content of H28 Labor Standards Q1-A)
match_q = re.search(r"労働条件は、.*", html)
if match_q:
    print(f"Found Question Text snippet: {match_q.group(0)[:50]}...")
    # Print context around it
    start = max(0, match_q.start() - 200)
    end = min(len(html), match_q.end() + 200)
    print(html[start:end])
else:
    print("Question text not found by simple regex.")
    # Print the "question" area structure usually found in such sites
    # Look for "mondai" or "question" classes
    matches = re.findall(
        r'<div[^>]*class="[^"]*mondai[^"]*"[^>]*>.*?</div>', html, re.DOTALL
    )
    for m in matches:
        print(f"Found div with 'mondai': {m[:200]}")

print("\n--- Searching for Explanation (Kaisetsu) ---")
# Look for "kaisetsu" or hidden text
match_k = re.search(r"kaisetsu|解説", html)
if match_k:
    print(f"Found 'kaisetsu' keyword at: {match_k.start()}")
    start = max(0, match_k.start() - 500)
    end = min(len(html), match_k.end() + 1000)
    print(html[start:end])
