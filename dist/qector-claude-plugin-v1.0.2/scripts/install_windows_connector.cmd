@echo off
REM QECTOR 1-Click Windows Connector Installer for Claude Desktop
REM Grounded in Reference Manual v1.0.0 (DOI: 10.5281/zenodo.21941046)
setlocal

echo ======================================================================
echo   QECTOR Claude Desktop Windows App Connector Installer
echo ======================================================================
echo.

REM Locate Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python not found in system PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

echo [INFO] Running pre-flight diagnostic and configuration...
python "%~dp0configure_claude_desktop.py" --confirm

if %errorlevel% equ 0 (
    echo.
    echo [SUCCESS] QECTOR is now installed in Claude Desktop!
    echo Please restart Claude Desktop to view QECTOR in Settings -> Connectors.
) else (
    echo.
    echo [ERROR] Configuration failed. See diagnostics above.
)

echo.
pause
