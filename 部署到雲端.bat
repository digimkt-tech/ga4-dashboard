@echo off
chcp 65001 >nul
echo ==================================================
echo   GA4 儀表板  —  上傳到 GitHub
echo ==================================================
echo.

cd /d "%~dp0"

where git >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 找不到 git，請先安裝 Git for Windows：
    echo        https://git-scm.com/download/win
    pause
    exit /b 1
)

if not exist ".git" (
    git init
    echo [OK] 已初始化 git 倉庫
)

echo.
set /p REPO_URL="請貼上你的 GitHub 倉庫網址（例如 https://github.com/your-name/ga4-dashboard.git）：
echo.

git remote remove origin 2>nul
git remote add origin %REPO_URL%

git add .
git commit -m "deploy: update dashboard"

git branch -M main
git push -u origin main

if errorlevel 1 (
    echo.
    echo [提示] 如果推送失敗，請先在 GitHub 網站建立新倉庫後再試一次。
    pause
    exit /b 1
)

echo.
echo ==================================================
echo   上傳完成！
echo.
echo   下一步：
echo   1. 前往 https://share.streamlit.io
echo   2. 點「New app」
echo   3. 選擇你的倉庫與 app.py
echo   4. 在「Advanced settings」→「Secrets」貼上：
echo.
echo      VIEWER_PASSWORD = "GA4view2024"
echo.
echo   5. 點「Deploy」，等待約 2 分鐘即完成
echo ==================================================
echo.
pause
