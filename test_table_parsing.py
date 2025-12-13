from bs4 import BeautifulSoup


def parse_html_text(element):
    """
    HTML要素からテキストを抽出し、赤文字・緑文字をStreamlitのMarkdown記法に変換する
    TableタグはMarkdownの表形式に変換する
    """
    if not element:
        return ""

    # テーブル対応
    if element.name == "table":
        rows = element.find_all("tr")
        if not rows:
            return ""

        md_lines = []
        # ヘッダー行の特定
        first_row_cols = rows[0].find_all(["th", "td"])

        # セル内の改行は <br> に置換して1行にする
        header_texts = [
            parse_html_text(c).strip().replace("\n", "<br>") for c in first_row_cols
        ]
        md_lines.append("| " + " | ".join(header_texts) + " |")

        # セパレータ
        md_lines.append("| " + " | ".join(["---"] * len(header_texts)) + " |")

        # データ行
        for row in rows[1:]:
            cols = row.find_all(["td", "th"])
            col_texts = []
            for c in cols:
                # 再帰的にパースし、改行を <br> に
                cell_text = parse_html_text(c).strip().replace("\n", "<br>")
                col_texts.append(cell_text)

            # 列数が足りない場合は空文字で埋める
            while len(col_texts) < len(header_texts):
                col_texts.append("")
            # 列数が多い場合は切り捨てる
            col_texts = col_texts[: len(header_texts)]

            md_lines.append("| " + " | ".join(col_texts) + " |")

        return "\n\n" + "\n".join(md_lines) + "\n\n"

    text = ""
    if hasattr(element, "contents"):
        for child in element.contents:
            if child.name is None:  # Text Node
                text += child.string if child.string else ""
            elif child.name == "br":
                text += "\n"
            elif child.name == "table":
                # テーブルがネストしている場合や、トップレベル以外の位置にある場合
                text += parse_html_text(child)
            else:
                # Recursive parse
                inner_text = parse_html_text(child)

                # Check color
                color = ""
                cls = child.get("class", [])
                if isinstance(cls, str):
                    cls = [cls]

                style = child.get("style", "").lower()

                # 赤・緑の判定
                styles_str = style.lower()
                classes_set = set([c.lower() for c in cls])

                if (
                    "clr2" in classes_set
                    or any("red" in c for c in classes_set)
                    or "color:red" in styles_str
                    or "color: red" in styles_str
                    or "#ff0000" in styles_str
                ):
                    color = "red"
                elif (
                    any("green" in c for c in classes_set)
                    or "color:green" in styles_str
                    or "color: green" in styles_str
                ):
                    color = "green"

                if color:
                    text += f":{color}[{inner_text}]"
                else:
                    text += inner_text

    return text


# Test cases
html_with_table = """
<div class="kaisetu">
    Some intro text.
    <table class="xyz">
        <tr><th>Header 1</th><th>Header 2</th></tr>
        <tr><td>Row 1 Col 1</td><td>Row 1 Col 2</td></tr>
        <tr><td>Row 2 Col 1</td><td><span class="clr2">Red Text</span></td></tr>
    </table>
    Some outro text.
</div>
"""

html_nested_div = """
<div class="kaisetu">
    <div>
        <table>
            <tr><td>Cell 1</td></tr>
        </table>
    </div>
</div>
"""

print("--- Test 1: Standard Table ---")
soup = BeautifulSoup(html_with_table, "html.parser")
parsed = parse_html_text(soup.find("div"))
print(parsed)

print("\n--- Test 2: Nested Table ---")
soup = BeautifulSoup(html_nested_div, "html.parser")
parsed = parse_html_text(soup.find("div"))
print(parsed)
