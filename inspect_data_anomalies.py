import json
import os

SAVE_FILE = "sharousi_data.json"

if os.path.exists(SAVE_FILE):
    with open(SAVE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Total items: {len(data)}")

    # Check for short content
    short_items = [(i, c) for i, c in enumerate(data) if len(c.get("front", "")) < 50]
    print(f"Items with front < 50 chars: {len(short_items)}")
    for i, c in short_items[:5]:
        print(f"Index: {i}")
        print(f"Front: {c.get('front')}")
        print("-" * 20)

    # Check for items without '【解説】'
    no_kaisetsu = [
        (i, c) for i, c in enumerate(data) if "【解説】" not in c.get("front", "")
    ]
    print(f"Items missing 【解説】: {len(no_kaisetsu)}")
    for i, c in no_kaisetsu[:5]:
        print(f"Index: {i}")
        print(f"Front: {c.get('front')}")
        print("-" * 20)

    # Check for empty "【解説】" content
    # Look for 【解説】 followed immediately by 【条文】 or end of string, possibly with whitespace
    empty_kaisetsu = []
    for i, c in enumerate(data):
        front = c.get("front", "")
        if "【解説】" in front:
            parts = front.split("【解説】")
            if len(parts) > 1:
                after_kaisetsu = parts[1]
                # Check if the next section starts immediately
                # Usually 【条文】 follows
                if "【条文】" in after_kaisetsu:
                    content = after_kaisetsu.split("【条文】")[0].strip()
                else:
                    content = after_kaisetsu.strip()

                if (
                    len(content) < 5
                    or content == "（公式に解説情報がありませんでした）"
                ):  # "（公式に解説情報がありませんでした）" matches known pattern
                    empty_kaisetsu.append((i, c, content))

    print(f"Items with empty/short kaisetsu: {len(empty_kaisetsu)}")
    for i, c, content in empty_kaisetsu[:5]:
        print(f"Index: {i}")
        print(f"Content found: '{content}'")
        print(f"Front start: {c.get('front')[:50]}...")
        print("-" * 20)

else:
    print(f"{SAVE_FILE} not found.")
