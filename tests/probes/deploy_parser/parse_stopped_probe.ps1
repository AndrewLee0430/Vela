# parse_stopped_probe.ps1 -- offline reproduction of the deploy.ps1 Step-3
# stopped-machine parser false-negative, and verification of the 2026-09-02 fix.
# NOTE: this file is deliberately pure ASCII -- PS 5.1 reads BOM-less files as
# ANSI and mangles multibyte characters (the first draft of this probe broke
# exactly that way; see the result JSON's encoding_note).
#
# TECH_DEBT anchor: "[P3 - deploy tooling - surfaced during the fly-211 deploy
# 2026-07-24] deploy.ps1 stopped-machine parser (^\S+) skips fly's indented
# fly status rows". 4 recurrences on record (fly 240 / 241 / 242 / 243), same
# signature each time: the script's own echoed table shows 2879720c66d478
# stopped, and the script prints "All machines running." directly below it.
#
# SAMPLE PROVENANCE (Rule 20, stated honestly): the rows below are RECONSTRUCTED
# from the empirical facts recorded in the TECH_DEBT entry's 2026-08-26 line
# (measured in-shell against live fly status at the fly-240 deploy):
#   (1) \bstopped\b matches exactly 1 row -- detection works;
#   (2) that row's first codepoint is 32 (leading space), so ^\S+ never matches;
#   (3) even absent the leading space, the second whitespace-delimited token is
#       the box char (codepoint 9474), not the machine ID.
# This is NOT a byte-capture of live output (none was retained). The entry's
# close condition -- no recurrence at the next real deploy -- covers that gap.

$ErrorActionPreference = "Stop"

$machineId = "2879720c66d478"
$boxChar = [char]9474

# Reconstructed failing-shape row: leading space + process name + box char + ID + ...
$stoppedRow = " app $boxChar $machineId $boxChar 243 $boxChar nrt $boxChar stopped $boxChar $boxChar 1 total $boxChar 2026-09-02T05:33:12Z"
$startedRow = " app $boxChar 6833909da13358 $boxChar 243 $boxChar nrt $boxChar started $boxChar $boxChar 1 total $boxChar 2026-09-02T05:33:12Z"
$headerRow  = " PROCESS $boxChar ID $boxChar VERSION $boxChar REGION $boxChar STATE $boxChar ROLE $boxChar CHECKS $boxChar LAST UPDATED"
# Legacy (pre-box-char) row shape, kept because flyctl auto-upgrades in place
# (TECH_DEBT [P3 - toolchain drift]) and the table format has already drifted once:
$legacyStoppedRow = "app     $machineId  211     nrt    stopped              2026-07-24T10:00:00Z"

$sample = @($headerRow, $startedRow, $stoppedRow)

# Assert the sample matches the three recorded empirical facts before using it.
$matchingRows = @($sample | Where-Object { $_ -match "\bstopped\b" })
if ($matchingRows.Count -ne 1) { throw "sample invalid: expected exactly 1 \bstopped\b row, got $($matchingRows.Count)" }
if ([int][char]$stoppedRow[0] -ne 32) { throw "sample invalid: first codepoint is not 32" }
$secondToken = ($stoppedRow.Trim() -split "\s+")[1]
if ([int][char]$secondToken[0] -ne 9474) { throw "sample invalid: second token is not codepoint 9474" }

# --- OLD Step-3 pipeline (deploy.ps1 as of 30fbdfb, lines 24-26) ---
$oldStopped = $sample |
    Where-Object { $_ -match "\bstopped\b" } |
    ForEach-Object { if ($_ -match "^\S+\s+(\S+)") { $Matches[1] } }

# --- FIXED Step-3 pipeline (14-hex machine-ID token, layout-independent) ---
$newStopped = $sample |
    Where-Object { $_ -match "\bstopped\b" } |
    ForEach-Object { if ($_ -match "\b([0-9a-f]{14})\b") { $Matches[1] } }

# Fixed pipeline against the legacy row shape (format-drift robustness):
$newStoppedLegacy = @($legacyStoppedRow) |
    Where-Object { $_ -match "\bstopped\b" } |
    ForEach-Object { if ($_ -match "\b([0-9a-f]{14})\b") { $Matches[1] } }

# False-positive check: an all-started sample must yield nothing.
$newAllStarted = @($headerRow, $startedRow) |
    Where-Object { $_ -match "\bstopped\b" } |
    ForEach-Object { if ($_ -match "\b([0-9a-f]{14})\b") { $Matches[1] } }

$result = [ordered]@{
    probe            = "deploy.ps1 Step-3 stopped-machine parser"
    date             = "2026-09-02"
    sample_provenance = "reconstructed from TECH_DEBT 2026-08-26 empirical line (codepoints 32 / 9474, \bstopped\b = 1 row); not a byte-capture"
    encoding_note    = "probe kept pure ASCII: PS 5.1 read the first UTF-8 (no BOM) draft as ANSI and the mojibake swallowed a code line"
    old_regex        = '^\S+\s+(\S+)'
    new_regex        = '\b([0-9a-f]{14})\b'
    old_result       = @($oldStopped)
    old_reproduces_false_negative = (@($oldStopped).Count -eq 0)
    new_result       = @($newStopped)
    new_detects_stopped_machine   = (@($newStopped) -contains $machineId)
    new_result_legacy_format      = @($newStoppedLegacy)
    new_detects_legacy_format     = (@($newStoppedLegacy) -contains $machineId)
    new_false_positive_on_started = (@($newAllStarted).Count -gt 0)
}

$pass = $result.old_reproduces_false_negative -and
        $result.new_detects_stopped_machine -and
        $result.new_detects_legacy_format -and
        (-not $result.new_false_positive_on_started)
$result.verdict = if ($pass) { "PASS" } else { "FAIL" }

$outPath = Join-Path $PSScriptRoot "parse_stopped_probe_result.json"
$result | ConvertTo-Json -Depth 4 | Out-File -FilePath $outPath -Encoding utf8
Write-Host ("verdict: {0}  (old={1} rows, new={2})" -f $result.verdict, @($oldStopped).Count, (@($newStopped) -join ","))
if (-not $pass) { exit 1 }
