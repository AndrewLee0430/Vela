<#
.SYNOPSIS
  The four-item opening probe for a strategy-chat session (CLAUDE.md Rule 26).

.DESCRIPTION
  Produces the block the founder pastes into the strategy chat alongside the UPLOADED
  ledgers (STATE.md / BACKLOG.md / TECH_DEBT.md). The uploaded files are only trustworthy
  if the chat can tell WHICH version it received, so section 3 fingerprints both the
  committed blob and the working file and states MATCH / DIFFERS per file.

  READ-ONLY. Never writes inside the working tree, never runs add/commit/push, never
  reads .env or any secret value. Output goes to stdout AND to a file under $env:TEMP\vela_extraction;
  after that file is written, only the newest -Keep extraction files in that folder are kept (founder
  ruling R3, 2026-09-24) — the only files this script ever deletes, all outside the working tree.

  Rule 26 (ii): every section prints the command that produced it on the line above its
  output. Rule 26 (iii): section 8 is a PLACEHOLDER — the adjacent observation is written
  by hand; this script never invents one.

.PARAMETER PriorSha
  Commit to diff the log against. Default e12d3f0 = the prod code SHA (fly v257).

.PARAMETER Task
  Free text: the next car's keyword. Adds a located-authority section.

.PARAMETER Keep
  How many extraction files to keep in $env:TEMP\vela_extraction, newest by the timestamp in the file
  NAME (extraction_yyyyMMdd_HHmmss.md). Default 2, minimum 1. A prune failure is a warning, never a
  failed extraction.

.PARAMETER Files
  The ledger set the founder uploads. Default STATE.md, BACKLOG.md, TECH_DEBT.md.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts/extract_session.ps1 -Task "legacy disclaimer"
#>
[CmdletBinding()]
param(
    [string]$PriorSha = "e12d3f0",
    [string]$Task = "",
    [ValidateRange(1, 2147483647)][int]$Keep = 2,
    [string[]]$Files = @("STATE.md", "BACKLOG.md", "TECH_DEBT.md")
)

$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
$OutputEncoding = [System.Text.Encoding]::UTF8

$RepoRoot = (& git rev-parse --show-toplevel)
if ([string]::IsNullOrEmpty($RepoRoot)) { throw "not a git repository" }
$RepoRoot = $RepoRoot.Replace("/", "\")
Push-Location $RepoRoot

$L = New-Object System.Collections.Generic.List[string]
function Emit([string]$s = "") { $L.Add($s) }
function Sec([string]$t) { Emit ""; Emit ("## " + $t); Emit "" }
function Run([string]$cmd, [int]$Max = 0) {
    Emit ('$ ' + $cmd)
    $out = Invoke-Expression $cmd
    if ($null -eq $out) { Emit "(no output)"; return }
    $i = 0
    foreach ($o in $out) {
        if ($Max -gt 0 -and $i -ge $Max) { Emit ("... (" + ($out.Count - $Max) + " more lines not shown)"); break }
        Emit ([string]$o); $i++
    }
}
function GrepCount([string]$pattern, [string]$file, [switch]$Ere) {
    if ($Ere) { Emit ('$ git grep -c -E "' + $pattern + '" -- ' + $file); $o = & git grep -c -E $pattern -- $file }
    else { Emit ('$ git grep -c "' + $pattern + '" -- ' + $file); $o = & git grep -c $pattern -- $file }
    if ([string]::IsNullOrEmpty($o)) { Emit ($file + ":0   (git grep prints nothing and exits 1 on zero matches)"); return 0 }
    Emit ([string]$o); return [int](([string]$o) -split ":")[-1]
}
function Get-BlobBytes([string]$rev, [string]$path) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "git"; $psi.Arguments = "show " + $rev + ":" + $path
    $psi.RedirectStandardOutput = $true; $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true; $psi.WorkingDirectory = $RepoRoot
    $p = [System.Diagnostics.Process]::Start($psi)
    $ms = New-Object System.IO.MemoryStream
    $p.StandardOutput.BaseStream.CopyTo($ms); $p.WaitForExit()
    return $ms.ToArray()
}
function Get-Fp([byte[]]$bytes) {
    $text = [System.Text.Encoding]::UTF8.GetString($bytes).Replace([string][char]13, "")
    $u = [System.Text.Encoding]::UTF8.GetBytes($text)
    $hex = -join ([System.Security.Cryptography.SHA256]::Create().ComputeHash($u) | ForEach-Object { $_.ToString("x2") })
    $high = [regex]::Matches($text, "[\uD800-\uDBFF]").Count
    return [PSCustomObject]@{ Chars = $text.Length - $high; Bytes = $u.Length; Lines = [regex]::Matches($text, "`n").Count; Sha = $hex.Substring(0, 16) }
}

Emit "# VELA — SESSION OPENING PROBE (CLAUDE.md Rule 26)"
Emit ""
Emit ("Produced by ``scripts/extract_session.ps1`` -PriorSha " + $PriorSha + " -Task """ + $Task + """. Read-only; wrote nothing inside the repo.")

Sec "1. DATE + HEAD"
Run 'Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"'
Run 'git rev-parse --show-toplevel'
Run 'git rev-parse HEAD'
Run 'git rev-parse origin/main'
Run 'git log --oneline -10'
Run ('git log --oneline ' + $PriorSha + '..HEAD')
Run 'git status -sb'

Sec "2. TREE"
Run 'git status --porcelain'
Run 'git status --short'
Run 'git stash list'

Sec "3. UPLOAD-SET FINGERPRINTS (committed blob vs working file)"
Emit "Definitions: CR bytes dropped first, then UTF-8. chars = Unicode code points · bytes = UTF-8 bytes · lines = LF count · sha = sha256(bytes)[0..15]."
Emit "Computed by: `$b = Get-BlobBytes 'HEAD' `$f  /  [System.IO.File]::ReadAllBytes(`$f), then"
Emit "  `$t = [Text.Encoding]::UTF8.GetString(`$b).Replace([string][char]13,'') ; `$u = [Text.Encoding]::UTF8.GetBytes(`$t)"
Emit "  sha = [Security.Cryptography.SHA256]::Create().ComputeHash(`$u) -> hex[0..15]"
Emit ""
Emit ("{0,-16} {1,-9} {2,-10} {3,-9} {4,-8} {5,-18} {6}" -f "file", "source", "chars", "bytes", "lines", "sha256-16", "verdict")
$anyDiff = $false
foreach ($f in $Files) {
    if (-not (Test-Path $f)) { Emit ("{0,-16} MISSING FROM THE WORKING TREE" -f $f); $anyDiff = $true; continue }
    $fpB = Get-Fp (Get-BlobBytes "HEAD" $f)
    $fpW = Get-Fp ([System.IO.File]::ReadAllBytes((Resolve-Path $f)))
    $same = ($fpB.Sha -eq $fpW.Sha)
    if (-not $same) { $anyDiff = $true }
    if ($same) { $v = "MATCH" } else { $v = "DIFFERS" }
    Emit ("{0,-16} {1,-9} {2,-10} {3,-9} {4,-8} {5,-18} {6}" -f $f, "committed", $fpB.Chars, $fpB.Bytes, $fpB.Lines, $fpB.Sha, $v)
    Emit ("{0,-16} {1,-9} {2,-10} {3,-9} {4,-8} {5,-18} {6}" -f "", "working", $fpW.Chars, $fpW.Bytes, $fpW.Lines, $fpW.Sha, "")
}
Emit ""
if ($anyDiff) {
    Emit "!! AT LEAST ONE FILE DIFFERS. The uploaded copy may NOT correspond to this HEAD — a working file carries edits that are"
    Emit "   not in the commit, or is missing. Do not pin a chat conclusion to the HEAD above for that file until it is reconciled."
} else {
    Emit "All files MATCH: each uploaded ledger is byte-identical (LF-normalized) to its blob at the HEAD in section 1, so a chat"
    Emit "conclusion drawn from the upload can be pinned to that SHA."
}

Sec "4. NAV (TECH_DEBT.md class counts, re-derived — never incremented)"
$cnt = @{}
foreach ($c in @("LAUNCH", "COMPLIANCE", "HONESTY", "DONE", "OTHER")) { $cnt[$c] = GrepCount ("^- \[" + $c + "\]") "TECH_DEBT.md" }
$bracket = GrepCount "^- \[" "TECH_DEBT.md"
$allb = GrepCount "^- " "TECH_DEBT.md"
$nonb = GrepCount "^- [^\[]" "TECH_DEBT.md"
$secLoose = GrepCount "^- \[.*\[sec\]" "TECH_DEBT.md"
$secStrict = GrepCount "^- \[[A-Z]+\] \*\*\[sec\]" "TECH_DEBT.md" -Ere
$sum = $cnt["LAUNCH"] + $cnt["COMPLIANCE"] + $cnt["HONESTY"] + $cnt["DONE"] + $cnt["OTHER"]
Emit ""
Emit ("class sum: " + $cnt["LAUNCH"] + " + " + $cnt["COMPLIANCE"] + " + " + $cnt["HONESTY"] + " + " + $cnt["DONE"] + " + " + $cnt["OTHER"] + " = " + $sum + "   vs  ^- \[ = " + $bracket)
if ($sum -eq $bracket) { Emit "  -> MATCH" } else { Emit ("  -> MISMATCH by " + ($sum - $bracket) + " — a class tag is misspelled or a bullet is double-counted") }
Emit ("bullet split: ^-  = " + $allb + "   vs  ^- \[ (" + $bracket + ") + ^- [^\[] (" + $nonb + ") = " + ($bracket + $nonb))
if ($allb -eq ($bracket + $nonb)) { Emit "  -> MATCH" } else { Emit ("  -> MISMATCH by " + ($allb - $bracket - $nonb)) }
Emit ("[sec] marker: loose " + $secLoose + " / strict " + $secStrict + "   (both commands are on record in the ledger; the strict one is what the NAV blocks quote)")

Sec "5. NEXT TASK"
Run 'git grep -n "NEXT UP after this ship" -- STATE.md'
Emit "(portable re-run of that one line: sed -n '<N>p' STATE.md, N = the number above)"
if (-not [string]::IsNullOrEmpty($Task)) {
    Emit ""
    Run ('git grep -n -i "' + $Task + '" -- BACKLOG.md STATE.md TECH_DEBT.md docs/batons/*.md') 20
    $hits = & git grep -n -i $Task -- TECH_DEBT.md
    if ([string]::IsNullOrEmpty($hits)) {
        Emit ""
        Emit ("No TECH_DEBT.md hit for """ + $Task + """ — if this car is TECH_DEBT-sourced the keyword is wrong; if it is BACKLOG-sourced that is normal (CLAUDE.md Step 0 item 2).")
    } else {
        # 🔑 ENTRY WALKER — founder ruling R2 (2026-09-24). The previous walker took the FIRST hit and walked
        #    upward to the nearest ^- \[ line; a first hit ABOVE the first entry heading (a NAV comment, a
        #    title-list row "- `[", a <!-- … [DONE] --> tombstone) found none, stopped at line 1 and printed the
        #    whole file head — lines 1–1250 at eb0db2e — with no warning. Selection is now:
        #    (1) the first hit ON a ^- \[ heading line; else (2) the first hit NOT inside an <!-- --> block whose
        #    upward walk reaches a ^- \[ line; else (3) NO ENTRY HIT + every hit classified. No fallback ever
        #    prints a range starting at line 1.
        $td = Get-Content "TECH_DEBT.md" -Encoding UTF8
        $ord = [System.StringComparison]::Ordinal
        # comment state at the START of each line, scanned across the whole file (NAV blocks span many lines)
        $open = New-Object bool[] ($td.Count + 1)
        $inC = $false
        for ($i = 0; $i -lt $td.Count; $i++) {
            $open[$i] = $inC
            $ln = [string]$td[$i]; $p = 0
            while ($true) {
                if ($inC) { $j = $ln.IndexOf('-->', $p, $ord); if ($j -lt 0) { break }; $inC = $false; $p = $j + 3 }
                else { $j = $ln.IndexOf('<!--', $p, $ord); if ($j -lt 0) { break }; $inC = $true; $p = $j + 4 }
            }
        }
        function HitCol([int]$i) {
            $ln = [string]$td[$i]
            try { $m = [regex]::Match($ln, $Task, 'IgnoreCase'); if ($m.Success) { return $m.Index } } catch { }
            $j = $ln.IndexOf($Task, [System.StringComparison]::OrdinalIgnoreCase); if ($j -ge 0) { return $j }
            return 0
        }
        function InComment([int]$i, [int]$col) {
            $st = $open[$i]; $ln = [string]$td[$i]; $p = 0
            while ($true) {
                if ($st) { $j = $ln.IndexOf('-->', $p, $ord); if ($j -lt 0 -or $col -lt ($j + 3)) { return $true }; $st = $false; $p = $j + 3 }
                else { $j = $ln.IndexOf('<!--', $p, $ord); if ($j -lt 0 -or $col -lt $j) { return $false }; $st = $true; $p = $j + 4 }
            }
        }
        function IsHeading([int]$i) { return (([string]$td[$i]) -match '^- \[') -and (-not $open[$i]) }
        function EntryStart([int]$i) { for ($k = $i; $k -ge 0; $k--) { if (IsHeading $k) { return $k } }; return -1 }
        $hitNos = @(@($hits) | ForEach-Object { [int](([string]$_ -split ":")[1]) })
        $sel = -1; $how = ""
        foreach ($h in $hitNos) { if (IsHeading ($h - 1)) { $sel = $h - 1; $how = "heading"; break } }
        if ($sel -lt 0) {
            foreach ($h in $hitNos) {
                $i = $h - 1
                $inCmt = InComment $i (HitCol $i)
                if ((-not $inCmt) -and ((EntryStart $i) -ge 0)) { $sel = $i; $how = "body"; break }
            }
        }
        Emit ""
        if ($sel -lt 0) {
            Emit ("NO ENTRY HIT for -Task '" + $Task + "' — " + $hitNos.Count + " hit(s) in TECH_DEBT.md, none on an entry heading and none in an entry body; no range is printed (founder ruling R2):")
            foreach ($h in $hitNos) {
                $i = $h - 1
                if (InComment $i (HitCol $i)) { $cls = "comment" } elseif (([string]$td[$i]) -match '^- `\[') { $cls = "title-list" } else { $cls = "body-no-heading" }
                $txt = [string]$td[$i]; if ($txt.Length -gt 120) { $txt = $txt.Substring(0, 120) }
                Emit (":" + $h + " [" + $cls + "] " + $txt)
            }
            Emit "(the phrase is matched as ONE line's substring: markdown backticks inside a heading make a plain-text phrase miss it)"
        } else {
            $s0 = EntryStart $sel
            $e0 = $s0; while (($e0 + 1) -lt $td.Count -and -not (IsHeading ($e0 + 1))) { $e0++ }
            $s = $s0 + 1; $e = $e0 + 1
            Emit ("entry walker: hit :" + ($sel + 1) + " selected by rule " + $how)
            Emit ('$ (Get-Content TECH_DEBT.md -Encoding UTF8)[' + $s0 + '..' + $e0 + ']   # entry containing hit :' + ($sel + 1) + '; portable: sed -n ' + $s + ',' + $e + 'p TECH_DEBT.md')
            foreach ($ln in $td[$s0..$e0]) { Emit ([string]$ln) }
        }
    }
}

Sec "6. LEDGER SHAPE"
Emit "(-Encoding UTF8 is REQUIRED: without it Windows PowerShell 5.1 decodes these UTF-8 files as the ANSI codepage (cp950 here)"
Emit " and UNDERCOUNTS lines — measured 2026-09-21 on this repo: TECH_DEBT.md 2493 vs the true 2517, BACKLOG.md 1929 vs 1952,"
Emit " STATE.md 1021 vs 1023. The values below agree with wc -l and with the LF counts in section 3.)"
Emit " (that pair was measured at ce6361f; TECH_DEBT.md was already 2558 lines at cb7b8df, the commit that added this script"
Emit "  — the live counts three lines below are authoritative. Kept rather than corrected: mark-never-delete.)"
foreach ($f in $Files) { Run ('(Get-Content "' + $f + '" -Encoding UTF8).Count') }
GrepCount "^- \[DONE\]" "TECH_DEBT.md" | Out-Null
Emit ""
Emit "30-day relocation check — EVALUATED. Enumeration (every dated heading sits inside the Recently Shipped section —"
Emit "verified 2026-09-21 and 2026-09-22 with 0 hits outside it — so no section-range logic is needed):"
Emit '    git grep -n "^- \*\*20[0-9][0-9]-[0-9][0-9]-[0-9][0-9]\*\*" -- STATE.md'

$stLines = Get-Content "STATE.md" -Encoding UTF8
$dateRx = '^- \*\*(20[0-9][0-9]-[0-9][0-9]-[0-9][0-9])\*\*'
$heads = New-Object System.Collections.ArrayList
for ($i = 0; $i -lt $stLines.Count; $i++) {
    if ($stLines[$i] -match $dateRx) { [void]$heads.Add(@($Matches[1], $i)) }
}
$today = (Get-Date).Date
$cutoff = $today.AddDays(-30)
$nArchived = 0; $nKept = 0
$candFirst = -1; $candLast = -1; $nCand = 0; $candLines = 0; $candBytes = 0
for ($k = 0; $k -lt $heads.Count; $k++) {
    $first = $heads[$k][1]
    if ($k + 1 -lt $heads.Count) { $last = $heads[$k + 1][1] - 1 } else { $last = $stLines.Count - 1 }
    while ($last -gt $first -and $stLines[$last].Trim() -eq "") { $last-- }
    # 🔑 EXCLUDE already-relocated entries BEFORE the date compare. Without this the count is inflated
    #    and looks perfectly plausible — measured 2026-09-21: 114 reported vs 55 true.
    # 🔴 ANCHORED TO THE POINTER SUFFIX, NOT A SUBSTRING (founder ruling 2026-09-21): the first version tested
    #    -like "*archived verbatim*" anywhere in the heading, so the 2026-09-21 ship entry — whose PROSE uses the
    #    phrase twice — read as archived; an entry that TALKS about archiving counted as one that HAD BEEN. It was
    #    harmless the day it landed (dated inside the 30-day window either way) and would have been SILENTLY skipped
    #    from 2026-10-22 onward, never offered as a candidate, with the wrong total sitting next to a right answer.
    #    Found in the slimming closeout's own dogfood run, 2026-09-21: excluded read 115 where 114 lines end with the
    #    suffix. The literal below was derived from STATE.md's real tombstones (all 114 end with it), not retyped.
    if ($stLines[$first].EndsWith(' *(→ archived verbatim: docs/archive/state_shipped_2026.md)*')) { $nArchived++; continue }
    $d = [datetime]::ParseExact($heads[$k][0], 'yyyy-MM-dd', $null)
    if ($d -lt $cutoff) {
        $nCand++
        if ($candFirst -lt 0 -or $first -lt $candFirst) { $candFirst = $first }
        if ($last -gt $candLast) { $candLast = $last }
        for ($n = $first; $n -le $last; $n++) {
            $candLines++
            $candBytes += [System.Text.Encoding]::UTF8.GetByteCount($stLines[$n]) + 1
        }
    } else { $nKept++ }
}
$pct = 0.0
if ($stLines.Count -gt 0) { $pct = [math]::Round(100.0 * $candLines / $stLines.Count, 1) }
$span = "n/a"
if ($nCand -gt 0) { $span = "lines " + ($candFirst + 1) + "-" + ($candLast + 1) }
Emit ""
Emit ("  excluded BEFORE the date compare (heading ENDS WITH the archive-pointer tombstone suffix): " + $nArchived)
Emit ("30-day relocation check — EVALUATED at " + $today.ToString('yyyy-MM-dd') + ", cutoff " + $cutoff.ToString('yyyy-MM-dd') +
      ": " + $nCand + " candidates (" + $nArchived + " already archived, " + $nKept + " within 30 days); they occupy " +
      $candLines + " of " + $stLines.Count + " lines (" + $pct + "%), " + $span + ", " + $candBytes +
      " bytes. CANDIDATE LIST, NOT AN ACTION LIST — relocation is a founder call (ledger slimming, founder ruling 2026-08-27).")

$tdLines = Get-Content "TECH_DEBT.md" -Encoding UTF8
$entryRx = '^- \[[A-Z_ -]+\]'
$eIdx = New-Object System.Collections.ArrayList
for ($i = 0; $i -lt $tdLines.Count; $i++) { if ($tdLines[$i] -match $entryRx) { [void]$eIdx.Add($i) } }
$dTot = 0; $dRelocated = 0
for ($k = 0; $k -lt $eIdx.Count; $k++) {
    $first = $eIdx[$k]
    if ($tdLines[$first] -notlike '- `[DONE`]*') { continue }
    $dTot++
    if ($k + 1 -lt $eIdx.Count) { $last = $eIdx[$k + 1] - 1 } else { $last = $tdLines.Count - 1 }
    $body = ""
    for ($n = $first + 1; $n -le $last; $n++) { $body += $tdLines[$n] }
    if ($body -like "*docs/archive/tech_debt_done.md*") { $dRelocated++ }
}
Emit ""
Emit ("TECH_DEBT [DONE] split: " + $dTot + " entries — " + $dRelocated + " bodies relocated to docs/archive/tech_debt_done.md, " +
      ($dTot - $dRelocated) + " still full in the file. (Test: the entry body cites the archive path.)")
Emit "  NO candidate count is emitted for TECH_DEBT, deliberately: [DONE] entries carry no heading-position date — they date"
Emit "  themselves inside prose, in several formats — so an age test would have to be invented, not derived. Founder ruling"
Emit "  2026-09-21 (Q1) held that the 30-day clause of CLAUDE.md:72 does NOT govern this half; C3 has no age test. Whether a"
Emit "  relocated body is ready is, as before, a founder call."

Sec "7. SCOPE NOTE"
Emit "The upload set is LEDGERS ONLY. Any question about product behaviour (api/, pages/, utils/) is NOT answerable from these files — it needs a read-only probe at this HEAD."

Sec "8. ADJACENT"
Emit "(3) ADJACENT OBSERVATION (Rule 26 iii) — NOT machine-generated. Claude Code writes at least one line here by hand before this extraction is used."

$OutDir = Join-Path $env:TEMP "vela_extraction"
if ($OutDir.ToLower().StartsWith($RepoRoot.ToLower())) { throw "refusing to write inside the working tree: $OutDir" }
if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir | Out-Null }
$OutFile = Join-Path $OutDir ("extraction_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".md")
[System.IO.File]::WriteAllText($OutFile, (($L -join "`n") + "`n"), (New-Object System.Text.UTF8Encoding($false)))
# 🔑 RETENTION — founder ruling R3 (2026-09-24): keep the newest -Keep extraction files by the timestamp in
#    their NAME; top-level files matching the script's own name pattern only, no recursion, -LiteralPath.
#    Runs only AFTER the new file is fully written, never deletes the file just written, and a prune failure
#    is a warning, never a failed extraction. Recorded, NOT handled: two runs inside the same second get the
#    same name, and the second overwrites the first.
$pruneMsgs = New-Object System.Collections.Generic.List[string]
try {
    $nameRx = '^extraction_\d{8}_\d{6}\.md$'
    $newName = [System.IO.Path]::GetFileName($OutFile)
    $ours = @(Get-ChildItem -LiteralPath $OutDir -File | Where-Object { $_.Name -match $nameRx } |
        Sort-Object -Property @{ Expression = { [datetime]::ParseExact($_.Name.Substring(11, 15), 'yyyyMMdd_HHmmss', $null) }; Descending = $true },
                              @{ Expression = { $_.Name }; Descending = $true })
    $kept = 0
    for ($k = 0; $k -lt $ours.Count; $k++) {
        $f = $ours[$k]
        if ($k -lt $Keep -or $f.Name -eq $newName) { $kept++; continue }
        try { Remove-Item -LiteralPath $f.FullName -Force; $pruneMsgs.Add("PRUNED: " + $f.Name) }
        catch { Write-Warning ("prune: could not delete " + $f.Name + " — " + $_.Exception.Message) }
    }
    $pruneMsgs.Add("KEPT: " + $kept + " extraction file(s) in " + $OutDir + " (-Keep " + $Keep + ", newest by the timestamp in the name; " + ($pruneMsgs.Count) + " pruned this run)")
} catch { Write-Warning ("prune step failed; the extraction itself was written: " + $_.Exception.Message) }
Pop-Location
foreach ($line in $L) { Write-Output $line }
Write-Output ""
Write-Output ("WRITTEN: " + $OutFile)
foreach ($m in $pruneMsgs) { Write-Output $m }
