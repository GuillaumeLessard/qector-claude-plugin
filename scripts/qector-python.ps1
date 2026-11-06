# QECTOR cross-platform Python resolver (Windows PowerShell 5.1+ / pwsh).
# Twin of qector-python.cmd for hosts that spawn a real executable rather
# than a batch file:  powershell.exe -NoProfile -ExecutionPolicy Bypass -File qector-python.ps1 <args>
# Supported range: Python 3.10-3.13. Order: $env:QECTOR_PYTHON -> py -3.13 .. py -3.10
# -> py -3 -> python3 -> python. Exhaustion fails closed with exit 127.
# stdin/stdout are inherited by the interpreter untouched (MCP JSON-RPC).
$ErrorActionPreference = "Continue"
$rangeCheck = "import sys; raise SystemExit(0 if (3,10)<=sys.version_info[:2]<(3,14) else 1)"
# Pass 1 prefers an interpreter that already has the runtime installed; pass 2
# accepts any supported version (the server then reports the missing dependency).
$runtimeCheck = "import qector_decoder_v3, mcp, jsonschema"

function Test-Candidate([string[]]$cmd, [string]$code) {
    if ($cmd.Count -eq 0 -or [string]::IsNullOrWhiteSpace($cmd[0])) { return $false }
    $exe = $cmd[0]
    if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { return $false }
    $rest = @()
    if ($cmd.Count -gt 1) { $rest = $cmd[1..($cmd.Count - 1)] }
    try {
        & $exe @rest -c $code *> $null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

# An explicit QECTOR_PYTHON is the operator's decision: use it whenever it is
# a supported version, even if it lacks the runtime (the server then says so).
if ($env:QECTOR_PYTHON -and $env:QECTOR_PYTHON -notlike '${*') {
    if (Test-Candidate @($env:QECTOR_PYTHON) $rangeCheck) {
        & $env:QECTOR_PYTHON @args
        exit $LASTEXITCODE
    }
}
$candidates = @()
$candidates += ,@("py", "-3.13")
$candidates += ,@("py", "-3.12")
$candidates += ,@("py", "-3.11")
$candidates += ,@("py", "-3.10")
$candidates += ,@("py", "-3")
$candidates += ,@("python3")
$candidates += ,@("python")

foreach ($pass in @("runtime", "version")) {
    foreach ($candidate in $candidates) {
        if (-not (Test-Candidate $candidate $rangeCheck)) { continue }
        if ($pass -eq "runtime" -and -not (Test-Candidate $candidate $runtimeCheck)) { continue }
        $exe = $candidate[0]
        $rest = @()
        if ($candidate.Count -gt 1) { $rest = $candidate[1..($candidate.Count - 1)] }
        & $exe @rest @args
        exit $LASTEXITCODE
    }
}

[Console]::Error.WriteLine("QECTOR: no Python 3.10-3.13 interpreter found.")
[Console]::Error.WriteLine("qector-decoder-v3 ships wheels up to Python 3.13 and the MCP SDK needs 3.10+;")
[Console]::Error.WriteLine("newer interpreters (3.14+) are rejected on purpose.")
[Console]::Error.WriteLine("Install a supported Python (https://www.python.org/downloads/) and retry,")
[Console]::Error.WriteLine("or set QECTOR_PYTHON (Claude Desktop: the Python interpreter extension setting).")
exit 127
