Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Write-Host "[env] Ensuring virtual environment at .\\.venv" -ForegroundColor Cyan

if (!(Test-Path ".venv/Scripts/python.exe")) {
  Write-Host "[env] Creating venv (.venv)" -ForegroundColor Yellow
  try {
    py -m venv .venv
  } catch {
    python -m venv .venv
  }
}

$venvPython = Join-Path (Resolve-Path ".").Path ".venv/Scripts/python.exe"
if (!(Test-Path $venvPython)) {
  throw "Failed to create/find .venv Python at $venvPython"
}

Write-Host "[env] Using: $venvPython" -ForegroundColor Green

& $venvPython -m pip install --upgrade pip | Write-Output
& $venvPython -m pip install -e . | Write-Output

Write-Host "[env] Python executable:" -NoNewline; Write-Host " $(& $venvPython -c 'import sys; print(sys.executable)')"
Write-Host "[env] sys.prefix:" -NoNewline; Write-Host " $(& $venvPython -c 'import sys; print(sys.prefix)')"
$pgInfo = & $venvPython -m pip show pygame 2>$null
if ($LASTEXITCODE -eq 0 -and $pgInfo) {
  $pgLine = ($pgInfo -split "`n") | Where-Object { $_ -match '^Version:' } | Select-Object -First 1
  if ($pgLine) {
    $pgVer = ($pgLine -split ':')[1].Trim()
    Write-Host "[env] pygame version: $pgVer"
  }
}

Write-Host "[env] Done." -ForegroundColor Cyan


