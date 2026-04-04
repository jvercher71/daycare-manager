@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM build_windows.bat  — Build Daycare Manager v2 as a Windows .exe installer
REM
REM Requirements:
REM   - Run this script on Windows
REM   - Python venv activated: venv\Scripts\activate.bat
REM   - Inno Setup installed: https://jrsoftware.org/isinfo.php
REM
REM Usage:
REM   cd C:\path\to\daycare-manager
REM   installer\build_windows.bat
REM ─────────────────────────────────────────────────────────────────────────────

echo 📦 Building Daycare Manager v2 for Windows...

REM Install build deps
pip install pyinstaller pillow -q

REM Clean previous builds
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Run PyInstaller
pyinstaller installer\daycare_manager.spec --noconfirm

echo ✅ Executable built in: dist\DaycareManagerV2\

REM ── Run Inno Setup to create installer ──────────────────────────────────────
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist %ISCC% (
    echo 💿 Creating Windows installer with Inno Setup...
    %ISCC% installer\setup.iss
    echo ✅ Installer created: dist\DaycareManagerV2_Setup.exe
) else (
    echo ⚠️  Inno Setup not found at %ISCC%
    echo    Download from: https://jrsoftware.org/isinfo.php
    echo    Then run: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\setup.iss
)

echo.
echo Done! Distribute: dist\DaycareManagerV2_Setup.exe
