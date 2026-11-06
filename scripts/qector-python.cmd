@echo off
rem QECTOR cross-platform Python resolver (Windows).
rem Supported range: Python 3.10-3.13 (mcp SDK needs 3.10+; qector-decoder-v3 wheels stop at 3.13).
rem Order: %%QECTOR_PYTHON%% (explicit choice, used whenever it is a supported
rem version) -> py -3.13 .. py -3.10 -> py -3 -> python3 -> python. Pass 1 prefers
rem an interpreter that already has the runtime installed; pass 2 accepts any
rem supported version (the server then reports the missing dependency itself).
rem Exhaustion fails closed (exit 127). Written flat (no parenthesised blocks, no
rem delayed expansion) so paths containing ( ) ! ^ or spaces survive.
setlocal
set "RANGE_CHECK=import sys; raise SystemExit(0 if (3,10)<=sys.version_info[:2]<(3,14) else 1)"
set "RUNTIME_CHECK=import qector_decoder_v3, mcp, jsonschema"
set "PASS=runtime"

if not defined QECTOR_PYTHON goto try_py313
"%QECTOR_PYTHON%" -c "%RANGE_CHECK%" >nul 2>nul
if errorlevel 1 goto try_py313
"%QECTOR_PYTHON%" %*
exit /b %ERRORLEVEL%

:try_py313
py -3.13 -c "%RANGE_CHECK%" >nul 2>nul
if errorlevel 1 goto try_py312
if "%PASS%"=="version" goto run_py313
py -3.13 -c "%RUNTIME_CHECK%" >nul 2>nul
if errorlevel 1 goto try_py312
:run_py313
py -3.13 %*
exit /b %ERRORLEVEL%

:try_py312
py -3.12 -c "%RANGE_CHECK%" >nul 2>nul
if errorlevel 1 goto try_py311
if "%PASS%"=="version" goto run_py312
py -3.12 -c "%RUNTIME_CHECK%" >nul 2>nul
if errorlevel 1 goto try_py311
:run_py312
py -3.12 %*
exit /b %ERRORLEVEL%

:try_py311
py -3.11 -c "%RANGE_CHECK%" >nul 2>nul
if errorlevel 1 goto try_py310
if "%PASS%"=="version" goto run_py311
py -3.11 -c "%RUNTIME_CHECK%" >nul 2>nul
if errorlevel 1 goto try_py310
:run_py311
py -3.11 %*
exit /b %ERRORLEVEL%

:try_py310
py -3.10 -c "%RANGE_CHECK%" >nul 2>nul
if errorlevel 1 goto try_py3
if "%PASS%"=="version" goto run_py310
py -3.10 -c "%RUNTIME_CHECK%" >nul 2>nul
if errorlevel 1 goto try_py3
:run_py310
py -3.10 %*
exit /b %ERRORLEVEL%

:try_py3
py -3 -c "%RANGE_CHECK%" >nul 2>nul
if errorlevel 1 goto try_python3
if "%PASS%"=="version" goto run_py3
py -3 -c "%RUNTIME_CHECK%" >nul 2>nul
if errorlevel 1 goto try_python3
:run_py3
py -3 %*
exit /b %ERRORLEVEL%

:try_python3
python3 -c "%RANGE_CHECK%" >nul 2>nul
if errorlevel 1 goto try_python
if "%PASS%"=="version" goto run_python3
python3 -c "%RUNTIME_CHECK%" >nul 2>nul
if errorlevel 1 goto try_python
:run_python3
python3 %*
exit /b %ERRORLEVEL%

:try_python
python -c "%RANGE_CHECK%" >nul 2>nul
if errorlevel 1 goto exhausted
if "%PASS%"=="version" goto run_python
python -c "%RUNTIME_CHECK%" >nul 2>nul
if errorlevel 1 goto exhausted
:run_python
python %*
exit /b %ERRORLEVEL%

:exhausted
if "%PASS%"=="version" goto none
set "PASS=version"
goto try_py313

:none
echo QECTOR: no Python 3.10-3.13 interpreter found. 1>&2
echo qector-decoder-v3 ships wheels up to Python 3.13 and the MCP SDK needs 3.10+; 1>&2
echo newer interpreters (3.14+) are rejected on purpose. 1>&2
echo Install a supported Python (https://www.python.org/downloads/) and retry, 1>&2
echo or set QECTOR_PYTHON (Claude Desktop: the Python interpreter extension setting). 1>&2
exit /b 127
