# -*- coding: utf-8 -*-
"""Baton fact-check — verify a handoff document against the repo before acting on it.

WHY THIS EXISTS: over ~10 batons in one session, EVERY baton contained at least one
error and some were load-bearing (a ratification claim pointing at a blank line; a
workaround citing a file renamed four days earlier). See README.md for the taxonomy.

🔴 THE DESIGN CONSTRAINT IS A MEASUREMENT, NOT A PREFERENCE. The first version of the
citation scanner written for this raised 193 flags on the ledger, 174 of them FALSE —
bare basenames like `server.py:450` read as missing files. 10% precision. Resolving
basenames through `git ls-files` drops it to 40 flags at ~85% precision. A checker that
cries wolf trains the reader to ignore it, which is worse than no checker.

  => EVERY BLOCKING CHECK IS ZERO- OR NEAR-ZERO-FALSE-POSITIVE.
  => EVERYTHING NOISY IS ADVISORY AND SAYS SO.

CHECKS (see README for the drift category and instance count behind each):
  BLOCKING   C1 citation resolve · C2 anchor uniqueness · C3 SHA state · C5 ratification
  ADVISORY   A6 population-not-stated · A7 figure-from-a-mirror
  SUGGEST    C1b new FILE:LINE citations in unstaged/staged ledger edits (2.2c)

WHAT IT DOES NOT CATCH: a number that is right but means something else; a conclusion
overturned by later evidence; whether a cited line still says what the prose claims.
Roughly two-thirds of observed baton errors are mechanical; none of the expensive ones
were. README §"What this does NOT catch" is the honest list — read it.

NO NETWORK. NO LLM. Pure grep/git. Runs in seconds.
Usage:  python tests/probes/baton_check/check_baton.py <baton.md>
        python tests/probes/baton_check/check_baton.py --self-test
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LEDGER = ["STATE.md", "TECH_DEBT.md", "BACKLOG.md", "CLAUDE.md"]


def archive_files() -> list[str]:
    """docs/archive/ holds ledger text relocated VERBATIM (C1-30d / C3, founder ruling
    2026-08-27). Anchor phrases quoted from relocated entry BODIES resolve only there,
    so C2 greps the archives as a fallback — see c2_anchors for the exact semantics."""
    d = ROOT / "docs" / "archive"
    return sorted("docs/archive/" + p.name for p in d.glob("*.md")) if d.exists() else []

CITE = re.compile(r'\b([A-Za-z0-9_][A-Za-z0-9_/.\-]*\.(?:md|py|tsx|ts|json|mjs))[:`]*:(\d+)(?:-(\d+))?\b')
ANCHOR = re.compile(r'`([^`\n]{12,120})`')
SHA = re.compile(r'\b([0-9a-f]{7,40})\b')
RATIFY = re.compile(r'\bratifi\w+|\bsigned[- ]off|\bapproved\b', re.I)
FIGURE = re.compile(r'(?<![\w.])(\d+(?:\.\d+)?%|\d{2,}/\d{2,}|\b\d{3,}\b)')
POP_HINT = re.compile(r'golden|synthetic|canary|corpus|queries|cases|runs|N=|×\s*\d|x\s*\d', re.I)


def sh(*args: str) -> str:
    """UTF-8 forced: commit subjects in this repo contain em-dashes and CJK, and the
    Windows default (cp950) raises UnicodeDecodeError mid-read."""
    r = subprocess.run(args, cwd=ROOT, capture_output=True,
                       encoding="utf-8", errors="replace")
    return r.stdout or ""


def load_suppressions() -> list[dict]:
    p = HERE / "suppressions.json"
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    for s in data["suppressions"]:
        if not s.get("reason"):
            raise SystemExit(f"suppression {s!r} has no reason — every suppression must carry one")
    return data["suppressions"]


class Repo:
    def __init__(self) -> None:
        self.tracked = [t for t in sh("git", "ls-files").split("\n") if t.strip()]
        self.by_base: dict[str, list[str]] = defaultdict(list)
        for t in self.tracked:
            self.by_base[t.rsplit("/", 1)[-1]].append(t)
        self._lines: dict[str, list[str] | None] = {}

    def lines(self, rel: str):
        if rel not in self._lines:
            f = ROOT / rel
            self._lines[rel] = (f.read_text(encoding="utf-8", errors="replace").split("\n")
                                if f.exists() else None)
        return self._lines[rel]

    def resolve(self, target: str):
        """-> (path, how). how: exact | basename-unique | AMBIGUOUS | MISSING"""
        if (ROOT / target).exists():
            return target, "exact"
        cands = self.by_base.get(target.rsplit("/", 1)[-1], [])
        if len(cands) == 1:
            return cands[0], "basename-unique"
        if len(cands) > 1:
            return None, "AMBIGUOUS"
        return None, "MISSING"


class Finding:
    __slots__ = ("level", "check", "claim", "detail")

    def __init__(self, level, check, claim, detail):
        self.level, self.check, self.claim, self.detail = level, check, claim, detail


def suppressed(target: str, sups: list[dict]) -> str | None:
    for s in sups:
        if re.search(s["pattern"], target):
            return s["reason"]
    return None


# ─────────────────────────── the checks ───────────────────────────

def c1_citations(text: str, repo: Repo, sups) -> tuple[list[Finding], int]:
    out, ok = [], 0
    for m in CITE.finditer(text):
        target, n = m.group(1), int(m.group(2))
        raw = m.group(0)
        if suppressed(target, sups):
            continue
        path, how = repo.resolve(target)
        if how == "AMBIGUOUS":
            continue                                    # conservative: never flag ambiguity
        if path is None:
            out.append(Finding("WRONG", "C1", raw, "NOT IN REPO"))
            continue
        L = repo.lines(path)
        end = int(m.group(3)) if m.group(3) else n
        if n > len(L):
            out.append(Finding("WRONG", "C1", raw, f"out of range — {path} has {len(L)} lines"))
        elif not any(x.strip() for x in L[n - 1: max(end, n)]):
            # A RANGE is stale only if EVERY line in it is blank. `retriever.py:395-413`
            # legitimately starts on a blank line; flagging that was a false positive in
            # the first live run.
            label = "BLANK LINE" if end == n else f"ALL {end - n + 1} LINES BLANK"
            out.append(Finding("DRIFT", "C1", raw, f"{label} in {path}"))
        else:
            ok += 1
    return out, ok


BARE_PATH = re.compile(r'\b((?:[A-Za-z0-9_.\-]+/)+[A-Za-z0-9_.\-]+\.(?:md|py|tsx|ts|json|mjs))\b')


def c1_bare_paths(text: str, repo: Repo, sups) -> tuple[list[Finding], int]:
    """A baton can name a file that no longer exists WITHOUT a line number — that is how
    `tests/test_webhook_cancel.py` (renamed by ca4bb7d) slipped through for a whole car.

    CONSERVATIVE: only paths CONTAINING A SLASH are checked, and only flagged when neither
    the full path NOR its basename exists anywhere in the repo. A bare `server.py` in prose
    is never flagged — that ambiguity is what took the first scanner to 10% precision."""
    out, ok, seen = [], 0, set()
    for m in BARE_PATH.finditer(text):
        p = m.group(1)
        if p in seen or suppressed(p, sups):
            continue
        seen.add(p)
        if (ROOT / p).exists():
            ok += 1
            continue
        base = p.rsplit("/", 1)[-1]
        cands = repo.by_base.get(base, [])
        # A relative link (`retrieval_attrition/README.md`) is NOT a broken path — if any
        # tracked file ends with the cited suffix, the citation resolves. Missing this was
        # a false positive in the first live run.
        if any(t == p or t.endswith("/" + p) for t in repo.tracked):
            ok += 1
            continue
        if len(cands) == 1:
            out.append(Finding("WRONG", "C1", p, f"NOT AT THAT PATH — exists as {cands[0]}"))
        elif cands:
            continue                                    # ambiguous basename: stay silent
        else:
            out.append(Finding("WRONG", "C1", p, "NOT IN REPO (no file of that name anywhere)"))
    return out, ok


def c2_anchors(text: str, repo: Repo, self_file: str | None = None) -> tuple[list[Finding], int]:
    """Anchor uniqueness — the convention this repo adopted after line numbers rotted.

    CONSERVATIVE, and deliberately narrow after the first live run flooded:
      · an "anchor" must be >=20 chars AND >=3 words — shorter backticks are symbols/paths
      · a phrase found in ZERO ledger files is prose, not an anchor: stay silent
      · when the input IS a ledger file, that file is EXCLUDED from the count — otherwise
        every phrase trivially matches itself and the check reports pure noise (113 hits
        for "` rather than `" in the first live run)
    """
    out, ok = [], 0
    targets = [f for f in LEDGER if f != self_file]
    # ARCHIVE FALLBACK (2026-08-27, ledger slimming): relocated entry BODIES live only in
    # docs/archive/*.md. Ledger hits keep their exact pre-slimming semantics — archives are
    # consulted ONLY when a phrase matches ZERO ledger lines, so the tombstone+archive
    # duplication of a relocated HEADING can never create a new multi-match false positive.
    arch = [f for f in archive_files() if f != self_file]
    seen = set()
    for m in ANCHOR.finditer(text):
        phrase = m.group(1).strip()
        if phrase in seen:
            continue
        seen.add(phrase)
        if len(phrase) < 20 or phrase.count(" ") < 2 or CITE.search(phrase):
            continue
        hits = sum(1 for f in targets for ln in (repo.lines(f) or []) if phrase in ln)
        if hits == 1:
            ok += 1
        elif hits > 1:
            out.append(Finding("DRIFT", "C2", f"`{phrase[:48]}`",
                               f"matches {hits} ledger lines — not a unique anchor"))
        else:
            ahits = sum(1 for f in arch for ln in (repo.lines(f) or []) if phrase in ln)
            if ahits == 1:
                ok += 1
            elif ahits > 1:
                out.append(Finding("DRIFT", "C2", f"`{phrase[:48]}`",
                                   f"matches {ahits} archive lines — not a unique anchor"))
            # ahits == 0: prose, stay silent — unchanged behaviour
    return out, ok


def c3_shas(text: str, repo: Repo) -> tuple[list[Finding], int]:
    out, ok = [], 0
    seen = set()
    for m in SHA.finditer(text):
        s = m.group(1)
        if s in seen or not re.search(r"\d", s) or len(s) < 7:
            continue
        seen.add(s)
        subj = sh("git", "log", "-1", "--format=%s", s).strip()
        if not subj:
            continue                                    # not a SHA in this repo — say nothing
        on_origin = "origin/main" in sh("git", "branch", "-r", "--contains", s)
        if on_origin:
            ok += 1
        else:
            out.append(Finding("DRIFT", "C3", s, f"LOCAL ONLY — not on origin/main ({subj[:44]})"))
    return out, ok


def c5_ratification(text: str, repo: Repo, sups) -> list[Finding]:
    out = []
    for line in text.split("\n"):
        if not RATIFY.search(line):
            continue
        for m in CITE.finditer(line):
            target, n = m.group(1), int(m.group(2))
            if suppressed(target, sups):
                continue
            path, how = repo.resolve(target)
            if path is None:
                continue                                # C1 already owns that
            L = repo.lines(path)
            if n > len(L):
                continue
            window = "\n".join(L[max(0, n - 3): n + 3]).lower()
            if not window.strip():
                continue
            if "ratified" not in window and ("to ratify" in window or "proposed" in window):
                out.append(Finding("WRONG", "C5", m.group(0),
                                   'target says "proposed"/"to ratify", NOT ratified'))
    return out


def a6_population(text: str) -> list[Finding]:
    out = []
    for line in text.split("\n"):
        figs = FIGURE.findall(line)
        if not figs or POP_HINT.search(line):
            continue
        if re.search(r'\.(md|py|json|tsx|ts):', line) or re.match(r'^\s*[-|#]', line) is None:
            continue
        out.append(Finding("ADVISORY", "A6", ", ".join(figs[:3]), "no population/query-set stated on this line"))
    return out[:6]


def a7_mirror(text: str, repo: Repo) -> list[Finding]:
    out = []
    for m in re.finditer(r'`?([A-Za-z0-9_]+\.json)`?', text):
        name = m.group(1)
        path, how = repo.resolve(name)
        if not path:
            continue
        body = (ROOT / path).read_text(encoding="utf-8", errors="replace")[:400000]
        if "mirror_caveat" in body or "MIRROR of" in body:
            out.append(Finding("ADVISORY", "A7", name,
                               "artifact self-declares a MIRROR of retrieve(), not retrieve()"))
    return out


def c1b_new_citations(repo: Repo) -> list[Finding]:
    """2.2(c) — SUGGEST anchors for NEW FILE:LINE citations in ledger edits. Never blocks.
    Scope chosen: the working-tree diff (staged + unstaged) of the four ledger files against
    HEAD. That is 'about to be written' in the only sense a script can see — it needs no
    session state and no hooks, and it catches the citation before the commit that freezes it."""
    out = []
    diff = sh("git", "diff", "HEAD", "--unified=0", "--", *LEDGER)
    for line in diff.split("\n"):
        if not line.startswith("+") or line.startswith("+++"):
            continue
        for m in CITE.finditer(line[1:]):
            has_anchor = bool(ANCHOR.search(line[1:].replace(m.group(0), "")))
            if not has_anchor:
                out.append(Finding("SUGGEST", "C1b", m.group(0),
                                   "new line-number citation with no anchor phrase beside it"))
    ded, seen = [], set()
    for f in out:
        if f.claim not in seen:
            seen.add(f.claim)
            ded.append(f)
    return ded[:8]


# ─────────────────────────── report ───────────────────────────

def render(findings: list[Finding], ok_counts: dict, n_claims: int, label: str) -> str:
    wrong = [f for f in findings if f.level == "WRONG"]
    drift = [f for f in findings if f.level == "DRIFT"]
    adv = [f for f in findings if f.level == "ADVISORY"]
    sug = [f for f in findings if f.level == "SUGGEST"]
    L = [f"BATON FACT-CHECK · {label} · {n_claims} claims · no LLM", ""]
    if wrong:
        L.append(f"❌ WRONG ({len(wrong)}) — load-bearing")
        for f in wrong:
            L.append(f"  {f.claim[:38]:<38} → {f.detail}")
        L.append("")
    if drift:
        L.append(f"⚠️  DRIFTED ({len(drift)})")
        for f in drift:
            L.append(f"  {f.claim[:38]:<38} → {f.detail}")
        L.append("")
    if adv:
        L.append(f"·  ADVISORY ({len(adv)}) — not errors; check the reasoning")
        for f in adv:
            L.append(f"  [{f.check}] {f.claim[:32]:<32} → {f.detail}")
        L.append("")
    if sug:
        L.append(f"✎  NEW CITATIONS IN YOUR LEDGER EDITS ({len(sug)}) — suggestion only")
        for f in sug:
            L.append(f"  {f.claim[:38]:<38} → carry an anchor phrase alongside the number")
        L.append("")
    tot_ok = sum(ok_counts.values())
    if tot_ok:
        L.append(f"✅ VERIFIED ({tot_ok})  "
                 + " · ".join(f"{k}:{v}" for k, v in ok_counts.items() if v))
    if not (wrong or drift):
        L.append("")
        L.append("No blocking drift. ⚠️ This checks whether numbers match files — NOT whether a")
        L.append("   conclusion still holds. See README §What this does NOT catch.")
    return "\n".join(L)


def check_text(text: str, label: str) -> tuple[str, int]:
    repo, sups = Repo(), load_suppressions()
    f1, ok1 = c1_citations(text, repo, sups)
    f1b, ok1b = c1_bare_paths(text, repo, sups)
    f2, ok2 = c2_anchors(text, repo, self_file=label if label in LEDGER else None)
    f3, ok3 = c3_shas(text, repo)
    findings = f1 + f1b + f2 + f3 + c5_ratification(text, repo, sups) \
        + a6_population(text) + a7_mirror(text, repo) + c1b_new_citations(repo)
    n = len(CITE.findall(text)) + len(set(SHA.findall(text))) + ok1b + len(f1b)
    ok = {"cites": ok1, "paths": ok1b, "anchors": ok2, "shas": ok3}
    blocking = sum(1 for f in findings if f.level in ("WRONG", "DRIFT"))
    return render(findings, ok, n, label), blocking


def self_test() -> int:
    """NEGATIVE CONTROL (the canary gate's lesson): a checker with no proof it can fail
    is not a checker. Two layers since 2026-08-27:

    1. The committed 2026-08-21 baton fixture — content untouched, per README ("do not
       fix the fixture's errors"). Only its PATH-based error is asserted here:
       `tests/test_webhook_cancel.py` was renamed away and cannot resolve. Its original
       second error — `TECH_DEBT.md:784`, a blank line when pinned — ROTTED non-blank as
       the ledger grew past the pin (found by the 2026-08-27 slimming recon): the tool's
       own drift class ate its own negative control. No expectation may line-pin a LIVE
       file again.

    2. DYNAMIC pins located against the live ledger at run time: an out-of-range
       citation (line count + 1000 — out of range however the file grows, shrinks, or
       is relocated) and the first blank line found at run time (fires BLANK LINE
       wherever a blank happens to be today). Survive growth and relocation by
       construction; nothing here encodes today's line numbers.
    """
    fx = HERE / "fixtures" / "baton_20260821_ratification.md"
    if not fx.exists():
        print("BROKEN: fixture missing"); return 1
    report, blocking = check_text(fx.read_text(encoding="utf-8"), "SELF-TEST fixture")
    print(report)
    print()
    if "test_webhook_cancel.py" not in report:
        print("❌ SELF-TEST BROKEN — fixture's path-based known error did NOT fire: test_webhook_cancel.py")
        return 1

    td_lines = (ROOT / "TECH_DEBT.md").read_text(encoding="utf-8", errors="replace").split("\n")
    oor = len(td_lines) + 1000
    blank = next((i + 1 for i, ln in enumerate(td_lines) if not ln.strip()), None)
    dyn = [f"dynamic control: TECH_DEBT.md:{oor} must fire WRONG (out of range)"]
    if blank is not None:
        dyn.append(f"dynamic control: TECH_DEBT.md:{blank} must fire DRIFT (blank line)")
    dyn_report, dyn_blocking = check_text("\n".join(dyn), "SELF-TEST dynamic pins")
    print(dyn_report)
    print()
    missed = []
    if f"TECH_DEBT.md:{oor}" not in dyn_report or "out of range" not in dyn_report:
        missed.append(f"TECH_DEBT.md:{oor} (expected: out of range)")
    if blank is not None and "BLANK LINE" not in dyn_report:
        missed.append(f"TECH_DEBT.md:{blank} (expected: blank line)")
    if missed:
        print(f"❌ SELF-TEST BROKEN — dynamic pins did NOT fire: {missed}")
        return 1
    total = blocking + dyn_blocking
    if total < 2:
        print(f"❌ SELF-TEST BROKEN — expected ≥2 blocking findings across both layers, got {total}")
        return 1
    print(f"✅ SELF-TEST PASS — {total} blocking findings; fixture path error + dynamic pins all fired.")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if args[0] == "--self-test":
        return self_test()
    p = Path(args[0])
    if not p.exists():
        print(f"no such file: {p}")
        return 2
    report, _ = check_text(p.read_text(encoding="utf-8"), p.name)
    print(report)
    return 0            # ADVISORY BY DESIGN: never blocks a session on its own opinion


if __name__ == "__main__":
    sys.exit(main())
