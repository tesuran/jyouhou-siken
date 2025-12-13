import json
import os

SAVE_FILE = "sharousi_data.json"


def is_broken(card):
    front = card.get("front", "")
    if not front:
        return True

    # 1. 既知のエラーメッセージ
    error_keywords = [
        "解説が見つかりませんでした",
        "解説情報がありませんでした",
        "解説取得失敗",
        "APIエラー",
        "通信エラー",
    ]
    if any(k in front for k in error_keywords):
        return True

    # 2. 解説ヘッダーがない
    if "【解説】" not in front:
        return True

    # 3. 解説の中身が空
    try:
        parts = front.split("【解説】")
        if len(parts) > 1:
            after_kaisetsu = parts[1]
            if "【条文】" in after_kaisetsu:
                content = after_kaisetsu.split("【条文】")[0]
            else:
                content = after_kaisetsu

            if not content.strip():
                return True
    except:
        pass

    return False


if os.path.exists(SAVE_FILE):
    with open(SAVE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    targets = [i for i, c in enumerate(data) if is_broken(c)]

    print(f"Total items: {len(data)}")
    print(f"Candidates for repair (broken): {len(targets)}")

    if targets:
        print("First 5 candidates:")
        for idx in targets[:5]:
            print(f"Index: {idx}")
            print(f"URL: {data[idx].get('source')}")
            print(f"Front start: {data[idx].get('front')[:50]}...")
            print("-" * 20)
else:
    print(f"{SAVE_FILE} not found.")
