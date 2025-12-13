import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import os
import json

# ページ設定
st.set_page_config(page_title="フラッシュカードマスター", page_icon="📚", layout="wide")

# カスタムCSS
st.markdown(
    """
<style>
    .card-container {
        perspective: 1000px;
        width: 100%;
        max-width: 600px;
        margin: 0 auto;
        height: 300px;
    }
    .card {
        position: relative;
        width: 100%;
        height: 100%;
        text-align: center;
        transition: transform 0.6s;
        transform-style: preserve-3d;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-radius: 15px;
        cursor: pointer;
    }
    .card-face {
        position: absolute;
        width: 100%;
        height: 100%;
        backface-visibility: hidden;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        border-radius: 15px;
        padding: 20px;
    }
    .card-front {
        background-color: white;
        color: #333;
        border: 2px solid #e2e8f0;
    }
    .card-back {
        background-color: #4f46e5;
        color: white;
        transform: rotateY(180deg);
    }
    .card.flipped {
        transform: rotateY(180deg);
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
    }
</style>
""",
    unsafe_allow_html=True,
)

# セッション状態の初期化
if "cards" not in st.session_state:
    st.session_state.cards = [
        {
            "front": "Google Antigravityとは？",
            "back": "AIエージェントを使用してソフトウェアを開発・テスト・修正できる、Googleの新しい統合開発環境（IDE）。",
        },
        {
            "front": "Artifacts（アーティファクト）",
            "back": "エージェントが生成する成果物のこと。コード、計画書、UIのプレビューなどが含まれる。",
        },
        {
            "front": "PDFの直接編集はできる？",
            "back": "基本的には不可。Antigravityはコードを書くツールであり、PDFエディタではない。Googleドキュメントなどを使用するのが推奨される。",
        },
    ]

if "current_index" not in st.session_state:
    st.session_state.current_index = 0

if "is_flipped" not in st.session_state:
    st.session_state.is_flipped = False

# サイドバー設定
st.sidebar.title("📚 メニュー")

# APIキー設定
api_key = st.sidebar.text_input("Gemini APIキー", type="password", key="api_key_input")
if api_key:
    os.environ["GOOGLE_API_KEY"] = api_key
    genai.configure(api_key=api_key)

mode = st.sidebar.radio("モード選択", ["学習モード", "編集モード"])

# --- 関数定義 ---


def next_card():
    st.session_state.is_flipped = False
    st.session_state.current_index = (st.session_state.current_index + 1) % len(
        st.session_state.cards
    )


def prev_card():
    st.session_state.is_flipped = False
    st.session_state.current_index = (st.session_state.current_index - 1) % len(
        st.session_state.cards
    )


def toggle_flip():
    st.session_state.is_flipped = not st.session_state.is_flipped


def add_card(front, back):
    if front and back:
        st.session_state.cards.append({"front": front, "back": back})
        st.success("カードを追加しました！")
    else:
        st.warning("表面と裏面の両方を入力してください。")


def process_pdf(uploaded_file):
    reader = PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"

    if not text.strip():
        st.error("PDFからテキストを抽出できませんでした。")
        return

    # APIキーがある場合はAI生成
    if api_key:
        try:
            model = genai.GenerativeModel("gemini-pro")
            prompt = f"""
            以下のテキストから、学習用のフラッシュカードを作成してください。
            重要な用語とその定義（または質問と答え）のペアを抽出し、以下のJSON形式で返してください。
            リスト形式で、キーは "front" と "back" にしてください。
            
            出力例:
            [
                {{"front": "用語1", "back": "意味1"}},
                {{"front": "質問2", "back": "答え2"}}
            ]

            対象テキスト:
            {text[:5000]} 
            """
            # Token limit safety: text[:5000]

            with st.spinner("AIが思考中..."):
                response = model.generate_content(prompt)
                json_text = (
                    response.text.replace("```json", "").replace("```", "").strip()
                )
                new_cards = json.loads(json_text)

                if isinstance(new_cards, list):
                    st.session_state.cards.extend(new_cards)
                    st.success(f"{len(new_cards)}枚のカードをAI生成しました！")
                else:
                    st.error("AIの応答形式が正しくありませんでした。")

        except Exception as e:
            st.error(f"AI生成エラー: {e}")

    # APIキーがない場合は簡易抽出（ルールベース）
    else:
        with st.spinner("テキストを解析中（簡易モード）..."):
            new_cards = []
            lines = text.split("\n")
            for line in lines:
                # コロン、タブ、矢印などで分割を試みる
                import re

                separator = re.search(r"[:：\t→]|->", line)
                if separator:
                    parts = line.split(separator.group())
                    if len(parts) >= 2:
                        front = parts[0].strip()
                        back = " ".join(parts[1:]).strip()
                        if front and back:
                            new_cards.append({"front": front, "back": back})

            if new_cards:
                st.session_state.cards.extend(new_cards)
                st.success(f"{len(new_cards)}枚のカードを抽出しました（簡易モード）。")
                st.info(
                    "※ APIキーが設定されていないため、区切り文字（コロンなど）を含む行のみを抽出しました。"
                )
            else:
                st.warning(
                    "有効なカードが見つかりませんでした。「用語 : 意味」のような形式が含まれているか確認してください。"
                )


# --- メインコンテンツ ---

st.title("Flashcard Master")

if mode == "学習モード":
    if not st.session_state.cards:
        st.info("カードがありません。編集モードで追加してください。")
    else:
        current_card = st.session_state.cards[st.session_state.current_index]

        # 進捗表示
        st.write(
            f"カード {st.session_state.current_index + 1} / {len(st.session_state.cards)}"
        )

        # カード表示エリア
        card_content = (
            current_card["back"]
            if st.session_state.is_flipped
            else current_card["front"]
        )
        card_label = "答え" if st.session_state.is_flipped else "質問"
        bg_color = (
            "bg-indigo-600 text-white"
            if st.session_state.is_flipped
            else "bg-white text-gray-800"
        )

        # Streamlitでの簡易カードUI（CSSアニメーションは複雑なため、条件分岐で表示）
        container = st.container(border=True)
        with container:
            st.caption(card_label)
            st.markdown(f"### {card_content}")
            if st.session_state.is_flipped:
                st.info("💡 裏面を表示中")
            else:
                st.write("")  # スペーサー

        col1, col2, col3 = st.columns([1, 2, 1])

        with col1:
            if st.button("前のカード"):
                prev_card()
                st.rerun()

        with col2:
            btn_text = "質問に戻る" if st.session_state.is_flipped else "答えを見る"
            if st.button(btn_text, use_container_width=True):
                toggle_flip()
                st.rerun()

        with col3:
            if st.button("次のカード"):
                next_card()
                st.rerun()

else:  # 編集モード
    tab1, tab2 = st.tabs(["手動追加", "PDFから自動生成"])

    with tab1:
        st.subheader("新しいカードを追加")
        new_front = st.text_area("表面（質問）", height=100)
        new_back = st.text_area("裏面（答え）", height=100)

        if st.button("リストに追加"):
            add_card(new_front, new_back)

    with tab2:
        st.subheader("PDFをアップロード")
        if not api_key:
            st.info(
                "APIキー未設定: 簡易抽出モード（「用語:意味」の形式のみ抽出）で動作します。"
            )
        else:
            st.info("APIキー設定済み: AIが内容を理解してカードを生成します。")

        uploaded_file = st.file_uploader("PDFファイルを選択", type=["pdf"])

        if uploaded_file is not None:
            if st.button("読み込んでカードを生成"):
                process_pdf(uploaded_file)

    st.divider()
    st.subheader("現在のカード一覧")
    for i, card in enumerate(st.session_state.cards):
        with st.expander(f"{i + 1}. {card['front']}"):
            st.write(f"**答え:** {card['back']}")
            if st.button("削除", key=f"del_{i}"):
                st.session_state.cards.pop(i)
                st.rerun()
