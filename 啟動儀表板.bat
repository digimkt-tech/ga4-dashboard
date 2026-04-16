@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ==================================================
echo   GA4 與 Google Ads 分析儀表板
echo ==================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [錯誤] 找不到虛擬環境，請確認 .venv 資料夾存在。
    pause & exit /b 1
)

:: 關閉舊的 Streamlit 與 cloudflared（避免衝突）
taskkill /f /im cloudflared.exe >nul 2>&1
taskkill /f /im python.exe >nul 2>&1
timeout /t 2 /nobreak >nul

:: 啟動 Streamlit
start /B "" ".venv\Scripts\python.exe" -m streamlit run app.py ^
    --server.port 8501 --server.headless true
timeout /t 6 /nobreak >nul

:: 啟動 Cloudflare 快速隧道
del /f /q tunnel.log >nul 2>&1
set CF="%LOCALAPPDATA%\Microsoft\WinGet\Links\cloudflared.exe"
start /B "" %CF% tunnel --url http://localhost:8501 --logfile tunnel.log
timeout /t 15 /nobreak >nul

:: 讀取並顯示公開網址
for /f "tokens=*" %%i in ('powershell -Command "(Get-Content tunnel.log | Select-String 'trycloudflare.com').Matches.Value | Select-Object -First 1"') do set URL=%%i

echo ==================================================
echo.
echo   本機網址：http://localhost:8501
echo.
if defined URL (
    echo   公開網址（可給主管）：%URL%
) else (
    echo   公開網址尚未就緒，請稍後查看 tunnel.log
)
echo.
echo   查看密碼：GA4view2024
echo.
echo   ★ 請保持此視窗開啟，關閉後外部連結會中斷。
echo ==================================================
echo.
pause
