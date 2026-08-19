@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM  QECTOR plugin: repackage + full local validation gate.
REM  Run this from anywhere; it cd's to the repo root itself.
REM  Stops on the first failing step (errorlevel != 0).
REM ============================================================

cd /d "%~dp0.."
set ROOT=%CD%
echo Repo root: %ROOT%
echo.

echo [1/7] Removing stale dist\ archives...
if exist "dist\qector-claude-plugin-v1.0.0.zip" del /q "dist\qector-claude-plugin-v1.0.0.zip"
if exist "dist\qector-claude-plugin-v1.0.0.zip.sha256" del /q "dist\qector-claude-plugin-v1.0.0.zip.sha256"
if exist "dist\qector-claude-plugin-v1.0.1.zip" del /q "dist\qector-claude-plugin-v1.0.1.zip"
if exist "dist\qector-claude-plugin-v1.0.1.zip.sha256" del /q "dist\qector-claude-plugin-v1.0.1.zip.sha256"
if exist "dist\qector-claude-plugin-v1.0.2.zip" del /q "dist\qector-claude-plugin-v1.0.2.zip"
if exist "dist\qector-claude-plugin-v1.0.2.zip.sha256" del /q "dist\qector-claude-plugin-v1.0.2.zip.sha256"
if exist "dist\qector-qector-core-skill.zip" del /q "dist\qector-qector-core-skill.zip"
if exist "dist\qector-qector-core-skill.zip.sha256" del /q "dist\qector-qector-core-skill.zip.sha256"
echo   done.
echo.

echo [2/7] python scripts\qector_runtime_check.py
python scripts\qector_runtime_check.py
if errorlevel 1 goto :fail
echo.

echo [3/7] python -m unittest discover -s tests -v
python -m unittest discover -s tests -v
if errorlevel 1 goto :fail
echo.

echo [4/7] ruff check .
ruff check .
if errorlevel 1 goto :fail
echo.

echo [5/7] ruff format --check .
ruff format --check .
if errorlevel 1 goto :fail
echo.

echo [6/7] Rebuilding dist\ archives: python scripts\pro_pack.py --all
python scripts\pro_pack.py --all
if errorlevel 1 goto :fail
echo.

echo [7/7] claude plugin validate "%ROOT%" --strict
claude plugin validate "%ROOT%" --strict
if errorlevel 1 goto :fail
echo.

echo ============================================================
echo  ALL GATES PASSED. Fresh archives are in dist\.
echo  Cargo tests for .tmp_core are NOT run by this script because
echo  that directory is vendored/reference (excluded from every
echo  packaged zip by scripts\pro_pack.py). Run them separately
echo  only if you are releasing the decoder core itself:
echo    cargo test --manifest-path .tmp_core\Cargo.toml
echo    cargo test --manifest-path .tmp_core\Cargo.toml --all-features
echo ============================================================
goto :eof

:fail
echo.
echo ============================================================
echo  FAILED at the step above. Fix it, then re-run this script.
echo  Nothing after a failed step has been executed.
echo ============================================================
exit /b 1
