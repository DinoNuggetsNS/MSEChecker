@echo off
REM Builds dist\MSECheck.exe (needs: pip install -r requirements.txt -r requirements-build.txt)
python -m PyInstaller --onefile --noconsole --name MSECheck --icon MSECheck.ico --add-data "MSECheck.ico;." --collect-all webview --collect-all spellchecker MSECheck.py
