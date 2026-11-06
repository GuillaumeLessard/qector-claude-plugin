@echo off
REM QECTOR 1-Click Windows Connector Installer for Claude Desktop
REM Grounded in Reference Manual v1.0.0 (DOI: 10.5281/zenodo.21941046)
setlocal

echo ======================================================================
echo   QECTOR Claude Desktop Windows App Connector Installer
echo ======================================================================
echo.

REM Resolve a supported interpreter (3.10-3.13) through the shared launcher;
REM "where python" alone would accept the Microsoft Store stub.
echo [INFO] Running pre-flight diagnostic and configuration...
call "%~dp0qector-python.cmd" "%~dp0configure_claude_desktop.py" --confirm
if %errorlevel% equ 127 (
    echo [ERROR] No Python 3.10-3.13 interpreter found.
    echo Install one from https://www.python.org/ or set QECTOR_PYTHON.
    pause
    exit /b 127
)

if %errorlevel% equ 0 (
    echo.
    echo [SUCCESS] QECTOR is now installed in Claude Desktop!
    echo Please restart Claude Desktop to view QECTOR in Settings -> Connectors.
) else (
    echo.
    echo [ERROR] Configuration failed. See diagnostics above.
    set "RC=1"
)

echo.
pause
if defined RC exit /b %RC%
