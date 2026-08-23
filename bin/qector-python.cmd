@echo off
setlocal EnableDelayedExpansion
rem QECTOR cross-platform Python resolver (Windows).
rem Supported range: Python 3.9-3.13 (matches qector-decoder-v3 wheels).
rem Order: %%QECTOR_PYTHON%% -> py -3 -> python3 -> python. Missing or
rem unsupported candidates are skipped; exhaustion fails closed.
set "RANGE_CHECK=import sys; raise SystemExit(0 if (3,9)<=sys.version_info[:2]<(3,14) else 1)"

if defined QECTOR_PYTHON (
  "%QECTOR_PYTHON%" -c "%RANGE_CHECK%" >nul 2>nul
  if not errorlevel 1 (
    "%QECTOR_PYTHON%" %*
    exit /b !ERRORLEVEL!
  )
)
where py >nul 2>nul && (
  py -3 -c "%RANGE_CHECK%" >nul 2>nul && (
    py -3 %*
    exit /b !ERRORLEVEL!
  )
)
where python3 >nul 2>nul && (
  python3 -c "%RANGE_CHECK%" >nul 2>nul && (
    python3 %*
    exit /b !ERRORLEVEL!
  )
)
where python >nul 2>nul && (
  python -c "%RANGE_CHECK%" >nul 2>nul && (
    python %*
    exit /b !ERRORLEVEL!
  )
)
echo QECTOR: no Python 3.9-3.13 interpreter found.
echo qector-decoder-v3 ships wheels for Python 3.9-3.13 only;
echo newer interpreters (3.14+) are rejected on purpose.
echo Install a supported Python ^(https://www.python.org/downloads/^) and retry,
echo or set QECTOR_PYTHON to a supported interpreter.
exit /b 127
