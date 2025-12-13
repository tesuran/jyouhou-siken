@echo off
echo スマホからアクセス可能なモードで起動します...
echo 起動後、画面左側に表示されるURLをスマホで入力してください。
echo.
streamlit run scraper_sharousi_app.py --server.address 0.0.0.0
pause
