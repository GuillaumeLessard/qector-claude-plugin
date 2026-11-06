@echo off
rem ============================================================
rem  QECTOR plugin: full local validation gate + release build (Windows).
rem  Mirrors RELEASE_VALIDATION.md. Stops on the first failing step.
rem  Uses scripts\qector-python.cmd so a supported interpreter is chosen.
rem  Written without labels so it is safe with any line ending.
rem ============================================================
setlocal
cd /d "%~dp0.."
set "PY=%~dp0qector-python.cmd"
set "QECTOR_SILENT=1"
echo Repo root: %CD%

echo [1/9] runtime check
call "%PY%" scripts\qector_runtime_check.py || exit /b 1
echo [2/9] release metadata
call "%PY%" scripts\release_validate.py || exit /b 1
echo [3/9] source structure
call "%PY%" scripts\validate_source.py || exit /b 1
echo [4/9] schema catalog in sync
call "%PY%" scripts\export_schemas.py --check || exit /b 1
echo [5/9] integrity manifest
call "%PY%" scripts\generate_integrity_manifest.py --check || exit /b 1
echo [6/9] unit, contract and stdio conformance tests
call "%PY%" -m unittest discover -s tests -v || exit /b 1
echo [7/9] five servers over stdio
call "%PY%" mcp\tests\test_mcp_stdio.py || exit /b 1
echo [8/9] ruff
call "%PY%" -m ruff check . || exit /b 1
echo [9/9] release build and bundle validation
call "%PY%" scripts\build_release.py --all %* || exit /b 1
call "%PY%" scripts\validate_plugin_bundle.py || exit /b 1
echo ALL GATES PASSED
exit /b 0
