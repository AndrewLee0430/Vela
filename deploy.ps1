# deploy.ps1 — Fly.io deploy + auto-restart stopped machines

$ErrorActionPreference = "Stop"
$fly = "C:\Users\andre\.fly\bin\fly.exe"

Write-Host "`n=== Step 1: fly deploy ===" -ForegroundColor Cyan
& $fly deploy
if ($LASTEXITCODE -ne 0) {
    Write-Host "Deploy failed (exit code $LASTEXITCODE)" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Step 2: Waiting 10s for machines to stabilize ===" -ForegroundColor Cyan
Start-Sleep -Seconds 10

Write-Host "`n=== Step 3: Checking for stopped machines ===" -ForegroundColor Cyan
$status = & $fly status
$status | ForEach-Object { Write-Host $_ }

$stopped = $status |
    Where-Object { $_ -match "\bstopped\b" } |
    ForEach-Object { if ($_ -match "^(\S+)") { $Matches[1] } }

if (-not $stopped) {
    Write-Host "`nAll machines running." -ForegroundColor Green
    exit 0
}

Write-Host "`nFound stopped machines: $($stopped -join ', ')" -ForegroundColor Yellow

Write-Host "`n=== Step 4: Starting stopped machines ===" -ForegroundColor Cyan
foreach ($id in $stopped) {
    Write-Host "  Starting $id ..."
    & $fly machine start $id
}

Write-Host "`n=== Step 5: Waiting 15s ===" -ForegroundColor Cyan
Start-Sleep -Seconds 15

Write-Host "`n=== Step 6: Final status ===" -ForegroundColor Cyan
$final = & $fly status
$final | ForEach-Object { Write-Host $_ }

$stillStopped = $final | Where-Object { $_ -match "\bstopped\b" }
if ($stillStopped) {
    Write-Host "`nSome machines still stopped." -ForegroundColor Red
    exit 1
} else {
    Write-Host "`nAll machines running." -ForegroundColor Green
}
