@echo off
REM Launch the PhonePad server as a windowed tray app (no console window).
cd /d "%~dp0"

REM Make sure dependencies are present (quiet; only does work the first time).
python -m pip install -q -r requirements.txt

REM pythonw = no console window. The app lives in the system tray.
start "" pythonw "%~dp0server.py"
