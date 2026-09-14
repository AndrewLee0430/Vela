# `phi_mask_over_json/` — what a regex PHI mask does to a JSON `ChatHistory.answer`

**Filed 2026-09-14** by the read-only `[sec]` probe at `9b24c19`. Full context:
`docs/batons/recon_20260914_sec_probe.md` §3.

## The question

`TECH_DEBT.md` → `[COMPLIANCE] [sec][P2 · R5 privacy] ChatHistory.answer stored unsanitized`
proposes, as optional hardening, running `PHIDetector.sanitize_for_log` over `answer` at the
five write sites *"exactly as `question` already is"*.

That bullet was written **2026-06-08, when `answer` was prose.** Since the HISTORY car
(segment 1 `62682f5` / segment 3, 2026-09-01 → 09-02) every mode stores a **JSON blob**:

| mode | serializer | site(s) |
|---|---|---|
| Research | `_research_history_payload` (`api/server.py:1087-1112`) | `:964` |
| Verify | `_verify_history_payload` (`api/server.py:1114-1145`) | `:1421`, `:1472`, `:1604` |
| Explain | inline `json.dumps` (`api/server.py:1707`) | `:1717` |

A regex mask over prose and a regex mask over `json.dumps(...)` output are **not the same
operation**. Nobody had measured the difference. This probe measures it.

## Method

For each payload shape the probe serializes with `json.dumps(..., ensure_ascii=False)` — the
same call the production helpers make — runs the **real** `PHIDetector.sanitize_for_log`
(`api/middleware/phi_handler.py:349-379`) over the resulting string, and records: whether the
string changed, whether the masked string still parses as JSON, and the context around every
`***` inserted.

Why "still parses" is the load-bearing question: `pages/history.tsx` safe-parses
(`parseVerifyAnswer` `:73-78`, `parseResearchAnswer` `:101-113`), and **both end in
`catch {} return null`**. A parse failure is not an error — it silently drops the row to the
legacy pre-wrap render path, which is the rendering class the HISTORY car has been closing.

## ⚠️ The inputs are SYNTHETIC

Every payload in the script is **constructed by hand from the shape of the real helpers** —
field names and types read off `api/models/schemas.py` (`Citation` `:70-81`, `DrugInteraction`
`:214-236`, `TfdaGrounding` `:238-246`), `api/models/explain_schemas.py` (`ExplainItem` `:89-95`),
and `api/services/explain_service.py:453-457`.

**They are NOT rows read from any database. No database was read** — not prod, not the Dev
branch `ep-spring-voice-a127ye10`, not under any session. The probe makes no network call, no
API call, and spends no credit. What it demonstrates is a property of **the sanitizer applied
to these shapes**, which is exactly the question the TECH_DEBT bullet turns on; it is *not* a
claim about what any stored row contains.

The four Research citations are chosen to span the mask's boundary conditions:

| citation | why |
|---|---|
| 8-digit PMID `12345678` | at the floor of `MEDICAL_RECORD_PATTERNS[1]` = `\b\d{8,12}\b` |
| 7-digit PMID `9876543` | one digit **below** the floor |
| NCT id `NCT01234567` | matches `MEDICAL_RECORD_PATTERNS[0]` = `\b[A-Z]{2,3}\d{6,10}\b` |
| DailyMed setid (lowercase hex UUID) | matches neither |

## The negative control

`HYPOTHETICAL_bare_int` is the **negative control** and is deliberately **not** a shape any
current payload has. It adds bare integer fields (a unix timestamp, an integer PMID) which the
mask replaces with a bare `***`, producing invalid JSON.

It exists so the probe has a case it can **fail**. A probe with no failing case has
demonstrated nothing — if the control ever reports `PARSES OK`, the probe is broken and its
other three results mean nothing. The script exits non-zero in that case, and `result.json`
carries `"negative_control_valid"`.

## Run

```bash
uv run python tests/probes/phi_mask_over_json/mask_over_json_probe.py
```

Rewrites `result.json` beside the script. Unlike the DailyMed / PubMed probes in this
directory, this one hits **no live external API**, so a re-run *is* reproducible — the
committed `result.json` is retained as the artifact the TECH_DEBT annotation and the baton
cite, not because it cannot be regenerated.

## Result at `9b24c19` (2026-09-14) — 實測

```
=== research_v1 ===            bytes 1116 -> 1090 | changed=True  | PARSES OK
    ...pubmed", "source_id": "PMID:***", "title": "A tri...
    ...s://pubmed.ncbi.nlm.nih.gov/***/", "credibility":...
    ...type": "fda", "source_id": "***", "title": "Reg t...
    ...://clinicaltrials.gov/study/***", "credibility": ...
=== verify ===                 bytes  655 ->  655 | changed=False | PARSES OK
=== explain ===                bytes  273 ->  273 | changed=False | PARSES OK
=== HYPOTHETICAL_bare_int ===  bytes  103 ->   91 | changed=True
    JSON.parse WOULD FAIL: JSONDecodeError: Expecting value: line 1 column 71 (char 70)
    ...tations": [], "written_at": ***, "pmid_int": ***}...

negative control valid: True
```

## What it shows

1. **The mask does NOT structurally break today's payloads.** All three live shapes still
   parse. `***` is JSON-string-safe (no quote, no backslash) and no pattern's separator class
   (`[-\s]`) can span a `"` or `,`, so a match can never run across a structural character.

2. **But that safety is a property of TODAY'S SHAPES, not of the approach.** The only way to
   invalidate the JSON is to mask a **bare numeric literal**, and none of the three current
   payloads has an 8+-digit bare number. Add **one** integer field — a unix timestamp, an
   integer PMID, a row id — and the negative control's behaviour becomes the live behaviour.

3. **Where it parses, it silently destroys data.** In Research, the 8-digit PMID and the
   PubMed URL containing it are masked, as is the NCT id. `/history` still renders — with
   `PMID:***` and a dead `https://pubmed.ncbi.nlm.nih.gov/***/` link.

4. **And it is inconsistent.** The 7-digit PMID **survives** while the 8-digit one is
   destroyed, because the pattern floor is 8. Half a citation panel breaks and half does not,
   per row, with nothing logged.

**Therefore the TECH_DEBT bullet's fix path splits into two different operations with
different costs and different blast radius** — masking the JSON *string* (measured above) vs
masking the free-text *fields* before serialization. The 2026-06 entry could not distinguish
them because answers were prose then. Disposition is the founder's; this probe supplies the
numbers only.
