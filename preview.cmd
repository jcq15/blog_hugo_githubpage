@echo off
cd /d "%~dp0"
echo Open http://localhost:1313/ in your browser.
python scripts\blog.py preview
pause
