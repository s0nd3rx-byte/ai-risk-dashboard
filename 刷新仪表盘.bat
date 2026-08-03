@echo off
cd /d "C:\Users\12820\Desktop\ai-sentiment-dashboard"
echo ============================================================
echo   AI 风险预警指数 — 正在拉取最新数据...
echo ============================================================
python dashboard.py
echo.
start index.html
echo   仪表盘已打开。
pause
