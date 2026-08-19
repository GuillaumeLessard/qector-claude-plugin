<#
.SYNOPSIS
    1-Click Windows PowerShell Connector Installer for QECTOR in Claude Desktop.
.DESCRIPTION
    Registers QECTOR in Claude Desktop (both Developer MCP and Settings -> Connectors).
#>

[CmdletBinding()]
param (
    [switch]$CheckOnly,
    [switch]$Remove,
    [string]$PythonPath
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ConfigureScript = Join-Path $ScriptDir "configure_claude_desktop.py"

$ArgsList = @()
if ($CheckOnly) {
    $ArgsList += "--check-only"
} else {
    $ArgsList += "--confirm"
}

if ($Remove) {
    $ArgsList += "--remove"
}

if ($PythonPath) {
    $ArgsList += "--python-path"
    $ArgsList += $PythonPath
}

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  QECTOR Claude Desktop Windows App Connector & Extension Installer" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

python $ConfigureScript @ArgsList
