# 社労士フラッシュカードアプリ デプロイ手順

このアプリを屋外（スマートフォンなど）で利用するために、Streamlit Cloudへデプロイする手順です。
GitHubアカウントとStreamlit Cloudアカウント（無料）が必要です。

## 1. 準備

### 1-1. ファイルの確認
以下のファイルがフォルダにあることを確認してください。
- `app.py` (メインアプリ)
- `requirements.txt` (必要なライブラリ一覧)
- `.gitignore` (不要なファイルをアップロードしないための設定)
- `sharousi_data.json` (データファイル)

### 1-2. GitHubリポジトリの作成
リポジトリ URL: **https://github.com/tesuran/flashcard-maker.git**

## 2. GitHubへのアップロード

PCのターミナル（またはコマンドプロンプト）で以下のコマンドを順番に実行し、コードをGitHubにアップロードします。
※ すでに `git init` やコミットは完了済みと想定しています。

```bash
# 1. リモートリポジトリを登録
git remote add origin https://github.com/tesuran/flashcard-maker.git

# ※ もし "remote origin already exists" と出たら以下を実行:
# git remote set-url origin https://github.com/tesuran/flashcard-maker.git

# 2. GitHubへプッシュ（アップロード）
git push -u origin main
```

## 3. Streamlit Cloudへのデプロイ

1. [Streamlit Cloud](https://streamlit.io/cloud) にログインします。
2. 「New app」ボタンをクリックします。
3. 「Use existing repo」を選択します。
4. リポジトリ `tesuran/flashcard-maker` を選択し、ブランチ `main`、メインファイルパス `app.py` を選択します。
5. 「Deploy!」をクリックします。

## 4. APIキーの設定 (AI機能を使う場合)

`app.py` でGoogle Gemini APIを使用する場合、APIキーを設定する必要があります。

1. デプロイされた ऐपの右下の「Manage app」をクリック（またはダッシュボードから設定へ）。
2. 「Settings」 -> 「Secrets」を開きます。
3. 以下のように入力して保存します。

```toml
GOOGLE_API_KEY = "あなたのGeminiAPIキー"
```

これで、スマートフォンからでもアプリのURLにアクセスして利用できるようになります。
