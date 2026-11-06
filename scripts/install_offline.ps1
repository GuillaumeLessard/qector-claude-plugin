<#
QECTOR offline installer (Windows PowerShell). Installs the pinned runtime
from a wheelhouse produced by scripts/build_wheelhouse.py without touching
any package index. Fails closed if a checksum does not match.

  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install_offline.ps1 -Wheelhouse D:\wheelhouse [-Venv .\.venv-qector]
(-ExecutionPolicy Bypass is needed because a .ps1 extracted from a downloaded
archive carries the mark-of-the-web and RemoteSigned refuses it.)
#>
param(
  [Parameter(Mandatory = $true)][string]$Wheelhouse,
  [string]$Venv = ".\.venv-qector"
)
$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Resolve-Path (Join-Path $Here "..")
$Launcher = Join-Path $Here "qector-python.cmd"

if (-not (Test-Path $Wheelhouse)) { throw "wheelhouse not found: $Wheelhouse" }
$Sums = Join-Path $Wheelhouse "SHA256SUMS"
if (-not (Test-Path $Sums)) { throw "SHA256SUMS missing in $Wheelhouse" }

Write-Host "== verifying wheelhouse checksums"
$failures = 0
foreach ($line in Get-Content $Sums) {
  if (-not $line.Trim()) { continue }
  $parts = $line -split "\s+", 2
  $expected = $parts[0].ToLower(); $name = $parts[1].Trim()
  $path = Join-Path $Wheelhouse $name
  if (-not (Test-Path $path)) { Write-Host "MISSING  $name"; $failures++; continue }
  $actual = (Get-FileHash -Algorithm SHA256 $path).Hash.ToLower()
  if ($actual -ne $expected) { Write-Host "MISMATCH $name"; $failures++ } else { Write-Host "OK       $name" }
}
if ($failures -gt 0) { throw "$failures wheelhouse file(s) failed verification" }

Write-Host "== creating virtual environment $Venv"
& $Launcher -m venv $Venv
if ($LASTEXITCODE -ne 0) { throw "no supported Python 3.10-3.13 interpreter found (exit $LASTEXITCODE); set QECTOR_PYTHON" }
$VPy = Join-Path $Venv "Scripts\python.exe"
if (-not (Test-Path $VPy)) { throw "virtual environment was not created at $Venv" }

Write-Host "== installing pinned runtime with --no-index"
& $VPy -m pip install --no-index --find-links $Wheelhouse --require-virtualenv --disable-pip-version-check -r (Join-Path $Root "requirements.lock")
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

Write-Host "== verifying runtime"
$env:QECTOR_SILENT = "1"
& $VPy (Join-Path $Root "scripts\qector_runtime_check.py")
if ($LASTEXITCODE -ne 0) { throw "runtime check failed (exit $LASTEXITCODE)" }
Write-Host "== verifying integrity manifest"
& $VPy (Join-Path $Root "scripts\generate_integrity_manifest.py") --check | Out-Null
if ($LASTEXITCODE -eq 0) { Write-Host "INTEGRITY.json OK" } else { Write-Host "WARNING: INTEGRITY.json drift" }
Write-Host ""
Write-Host "Done. Set QECTOR_PYTHON=$VPy before starting Claude Code / Claude Desktop."
