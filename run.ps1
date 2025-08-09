Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

& .\env.ps1

$venvPython = Join-Path (Resolve-Path ".").Path ".venv/Scripts/python.exe"

Write-Host "[run] Launching Othello Coach via venv" -ForegroundColor Cyan

# Prefer console script if available; fallback to module
try {
  & $venvPython -m othello_coach.main
} catch {
  & $venvPython -m othello_coach
}


