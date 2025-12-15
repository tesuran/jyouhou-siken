import requests
from bs4 import BeautifulSoup

url = "https://www.ap-siken.com/kakomon/07_haru/pm01.html"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

print(f"--- Inspecting: {url} ---")
try:
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")

        # Check for #mondai
        mondai = soup.find(id="mondai")
        print(f"#mondai found: {bool(mondai)}")

        # Check main content area
        main_col = soup.find(id="mainCol")
        if main_col:
            # Look for whatever contains the question text
            # Often PM questions might be in a different container or just directly in mainCol
            print("mainCol found.")
            # Print first few divs in mainCol
            for i, child in enumerate(main_col.find_all("div", recursive=False)[:5]):
                print(
                    f"Child {i}: <{child.name} class='{child.get('class')}'> ID='{child.get('id')}'"
                )

        # Check for answer/explanation area
        kaisetsu = soup.find(id="kaisetsu")
        print(f"#kaisetsu found: {bool(kaisetsu)}")

        with open("ap_siken_pm_debug.html", "w", encoding="utf-8") as f:
            f.write(response.text)

    else:
        print(f"Status: {response.status_code}")

except Exception as e:
    print(f"Error: {e}")
