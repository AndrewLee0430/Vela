# deploy.ps1 — Fly.io deploy + auto-restart stopped machines

$ErrorActionPreference = "Stop"
$fly = "C:\Users\andre\.fly\bin\fly.exe"

Write-Host "`n=== Step 1: fly deploy ===" -ForegroundColor Cyan
# Build provenance: stamp the deployed commit into the image so /health and the image
# LABEL can be read back and matched to a commit. See TECH_DEBT [P2 · build provenance].
$sha = (git rev-parse HEAD).Trim()
Write-Host "  GIT_SHA = $sha" -ForegroundColor DarkGray
& $fly deploy --build-arg GIT_SHA=$sha
if ($LASTEXITCODE -ne 0) {
    Write-Host "Deploy failed (exit code $LASTEXITCODE)" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Step 2: Waiting 10s for machines to stabilize ===" -ForegroundColor Cyan
Start-Sleep -Seconds 10

Write-Host "`n=== Step 3: Checking for stopped machines ===" -ForegroundColor Cyan
$status = & $fly status
$status | ForEach-Object { Write-Host $_ }

# fly status machine rows are indented (leading space, codepoint 32) and
# box-char-separated (codepoint 9474), so neither ^\S+ nor a second-token
# capture reaches the machine ID. The ID is the row's only 14-hex-char token:
# match it directly, independent of table layout (flyctl auto-upgrades; the
# format may drift). Keep this file pure ASCII: PS 5.1 reads BOM-less files
# as ANSI and mangles multibyte characters.
$stopped = $status |
    Where-Object { $_ -match "\bstopped\b" } |
    ForEach-Object { if ($_ -match "\b([0-9a-f]{14})\b") { $Matches[1] } }

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
