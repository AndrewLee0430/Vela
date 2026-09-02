# Recon 2026-09-01 — HISTORY car opening recon (per-entry delete + three-mode render fidelity)

**RECON ONLY — read-only. No code changes, no push, no deploy.** This document inventories facts and design options for the HISTORY car (the two `[OTHER][P2]` /history entries filed in `750d983`). The founder decides sequencing and design; §6 is the numbered decision list. Per the 2026-08-24 process entry, every derived≠cited disagreement is recorded in §7 with both readings reconciled — a disagreement is a third fact, not a tiebreak.

**Workflow Step 0 note:** no baton was fact-checked with `check_baton.py` — this recon's inputs are the TECH_DEBT entries (commit `750d983`), the BACKLOG deletion-feature scoping (2026-08-18), and the founder's recon prompt, none of which is a `docs/batons/` baton. The known cp950 crash at `check_baton.py:438` was therefore not exercised.

---

## §0. Repo + prod assertion (Rule 24)

| Check | Expected | Derived | Verdict |
|---|---|---|---|
| `git rev-parse --show-toplevel` | C:/Users/andre/projects/Vela | `C:/Users/andre/projects/Vela` | ✅ |
| `git rev-parse HEAD` | `4a99eec742647fc56e61828214359c2fc222bfb2` | `4a99eec742647fc56e61828214359c2fc222bfb2` | ✅ exact |
| `git ls-remote origin main` | same | `4a99eec742647fc56e61828214359c2fc222bfb2` (full 40-char) | ✅ local main = origin/main |
| `GET https://vela-ai-medical.fly.dev/health` | revision `8b8886d0c57ae9627552bcbc91742202040a9f76` | `{"status":"healthy","version":"2.2.0","revision":"8b8886d0c57ae9627552bcbc91742202040a9f76"}` | ✅ prod = fly 241, full-string match |
| `git log --oneline 8b8886d..HEAD -- api/ pages/ components/ utils/` | EMPTY | EMPTY — the 3 commits since deploy (`750d983` / `443dbef` / `4a99eec`) are docs-only | ✅ |
| Baseline `python -m pytest -q` | 400 passed / 28 skipped | **400 passed, 28 skipped in 220.31s** | ✅ exact |

---

## §1. Finding 1 re-verification at HEAD — per-entry delete NEVER BUILT

Every count below: command → derived vs cited → unit. All re-derived at HEAD `4a99eec`.

### 1a. DELETE capability absence

| Command | Cited | Derived | Unit | Verdict |
|---|---|---|---|---|
| `grep -rn "@app.delete" api/` | 0 | 0 | decorator occurrences | ✅ |
| `grep -rn "router.delete" api/` | 0 | 0 | occurrences | ✅ |
| `grep -rn 'methods=' api/ \| grep -i delete` | 0 | 0 | occurrences | ✅ |
| `grep -rn "APIRouter\|include_router" api/` | 0 | 0 | occurrences — no sub-router can hide a route | ✅ |
| `grep -rn "method: 'DELETE'\|method: \"DELETE\"" --include="*.ts*" .` | 0 | 0 | fetch-option occurrences | ✅ |
| Route-decorator census of `api/` (`@app.get\|post\|put\|patch\|delete\|head\|options\|api_route`) | 38 = 20 GET + 18 POST | **38 = 20 `@app.get` + 18 `@app.post`**, all in `api/server.py`, zero of any other verb | route decorators | ✅ exact |

**New fact surfaced by the `methods=` grep** (its only hit): CORS is verb-restricted —
> `api/server.py:310`: `allow_methods=["GET", "POST"],`

so a browser-issued cross-origin `DELETE` would be blocked even if the endpoint existed. The delete build must either extend `allow_methods` or use a POST route. See decision **D5**.

### 1b. History surface

- `@app.get("/api/history")` (`api/server.py:1818`) is the **only** history endpoint — the route census above has no other history path, and a repo grep for `/api/history` under `api/` matches only this decorator. Signature verbatim:
  ```python
  @app.get("/api/history")
  async def get_user_history(
      creds: Optional[HTTPAuthorizationCredentials] = Depends(require_auth),
      db: Session = Depends(get_db)
  ):
      user_id = get_user_id(creds)
  ```
  Ownership: `require_auth` (`server.py:362`) requires a valid Clerk JWT (403 otherwise); `get_user_id` (`server.py:439`) returns `creds.decoded["sub"]` (TEST_MODE: `TEST_USER_ID` env or `"test_user"`). The query is owner-scoped: `db.query(ChatHistory).filter(ChatHistory.user_id == user_id)` (`:1830`), windowed by plan (Pro 365d / Free 7d), `.limit(200)`.
- `grep -in "delete\|clear\|remove\|刪除" pages/history.tsx` → **0** (cited 0, unit: matching lines). ✅
- An expanded entry renders only: the expand toggle (`<button onClick={() => handleToggle(item)}` — `pages/history.tsx:168`) and `ShareButton` (`:274-281`, expanded only, all three session types). No other control. ✅ matches the TECH_DEBT observation.

### 1c. Never-built adjudication legs

| Command | Cited | Derived | Unit |
|---|---|---|---|
| `git log --all -S "delete" -- pages/history.tsx` | 0 | 0 | commits (pickaxe) ✅ |
| `git log --all -S "handleDelete" -- pages/ api/` | 0 | 0 | commits (pickaxe) ✅ |

Branch coverage of `--all` (`git branch -a`): `main`, `c2-phase1b-EA-measurement`, `locale-b1-fix`, `locale-waterfall-b1`, `remotes/origin/main` (+`origin/HEAD`). Verdict (a) NEVER BUILT stands at HEAD.

### 1d. Schema facts (2026-08-18 BACKLOG scoping, re-verified)

`ChatHistory` (`api/models/sql_models.py:17-25`), verbatim — **6 columns** (cited 6 ✅, unit: ORM columns):
```python
class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, index=True)
    session_type = Column(String)
    question = Column(Text)
    answer = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
```
- `grep -rn "ForeignKey\|relationship(" --include="*.py"` (repo-wide) → **0 of each** (cited 0/0 ✅, unit: occurrences).
- `grep -rln "FOREIGN KEY\|REFERENCES" migrations/` → **0 files** (cited 0 ✅).
- **GET response serialization — DISCREPANCY, see §7-D1.** The endpoint `return query.order_by(desc(ChatHistory.created_at)).limit(200).all()` (`:1843`) returns raw ORM rows with **no response_model**. Empirically reproduced (in-memory sqlite + real model + FastAPI `jsonable_encoder`, the exact path the endpoint uses — script in session scratchpad): the encoded row is
  `{"user_id": ..., "session_type": ..., "answer": ..., "question": ..., "id": 1, "created_at": ...}` — **all 6 columns, `id` INCLUDED** (and `user_id` included). The frontend already types and consumes it: `interface HistoryItem { id: number; user_id: string; ... }` (`pages/history.tsx:30-37`), React key + `expandedId` toggle (`:99-103,164`), and `ShareButton queryId={String(item.id)}` (`:276`) — which is how `shared_query.query_id` came to hold stringified chat_history PKs (TECH_DEBT `:537`). The cited claim "the PK … is never sent to the client / GET would need to expose it" is **false at HEAD**.

### 1e. Anonymous rows

Derived at HEAD: **no live write site can produce a ChatHistory row without a user identity.**
- Research: the history write (`:928`) sits in the `else` of `if is_anonymous:` (`:920`); the CITATIONS-event AuditLog write is likewise gated `if not is_anonymous:` (`:906`, comment: *"L0 anonymous: skip AuditLog (no history persistence for anon)"*).
- Verify: all three ChatHistory sites are guarded `if not is_anonymous:` (`:1323`, `:1365`, `:1469`).
- Explain: L0 rejected outright — `if anon_id is not None: raise FeatureNotAvailable("explain")` (`:1530-1531`).
- `require_auth_or_anonymous` (`:399-436`) returns exactly one of (user_id, anon_id) non-None; no-token production requests get 403. The only non-Clerk identity is TEST_MODE's synthetic `TEST_USER_ID`/`"test_user"` (never valid on prod; the BACKLOG near-miss entry records exactly one averted prod `test_user` write).
- Anonymity predates history writes' guards only in the sense that the anon tier itself arrived at `7a8c5a8` ("[PRD 2.8] Anonymous Trial Flow Round 1"); **before** it, these endpoints required auth, so pre-`7a8c5a8` rows also carry real user_ids.

Why such rows would be unreachable by an owner-checked delete: the check is `ChatHistory.user_id == get_user_id(creds)`; a row with `user_id` NULL or a synthetic id matches no authenticatable principal, and L0 users cannot call an authed endpoint at all. **But the population is empty-by-construction at HEAD** — see §7-D3 for the reconciliation with the TECH_DEBT sentence.

---

## §2. Finding 2 re-verification at HEAD — three-shape fidelity

### 2a. Explain (shape i — the target)

Write path (`api/server.py`, inside `explain_report`'s `event_stream()`):
```python
# :1565-1566 — Serialize structured result for ChatHistory.answer text column
if isinstance(event, dict) and event.get("type") == "explain_result":
    full_answer = json.dumps(event.get("content", {}), ensure_ascii=False)
# :1576-1581
_safe_db_write(db, ChatHistory(
        user_id=user_id,
        session_type="explain",
        question=PHIDetector.sanitize_for_log(body.report_text[:500]),
        answer=full_answer
    ), label="Explain History")
```
(Cited `:1576-1593` — the ChatHistory call is `:1576-1581`; the cited range extends over credits+cost. ✅ substance exact.)

Render path — **the reuse pattern**, `pages/history.tsx:220-269` (cited `:219-268`, 1-line rust):
```tsx
{item.session_type === 'explain' && (() => {
    let parsed: { items?: ExplainItem[]; clinical_correlations?: ClinicalCorrelation[]; disclaimer?: string } | null = null;
    try {
        parsed = JSON.parse(item.answer);
    } catch {
        parsed = null;
    }
    if (parsed && Array.isArray(parsed.items)) {
        return ( /* ExplainItemCard per item + ClinicalCorrelationCard per correlation */ );
    }
    // Fallback: legacy pre-§2.7 records or malformed JSON — render as plain text.
    return ( /* <p whitespace-pre-wrap>{item.answer}</p> in prose wrapper */ );
})()}
```
The mechanism: `JSON.parse` in try/catch → shape check (`Array.isArray(parsed.items)`) → real cards; anything else falls to plain text. This is the pattern the other two modes would copy (with their own shape checks).

Commit `fbad02c` exists: `fbad02c7064810e9dcdfe0df735329dd60478811`, 2026-05-21, "[bug] history — render Explain records as cards, not raw JSON", `pages/history.tsx | 68 ++/-- (52 insertions, 16 deletions)`. ✅

### 2b. Research (shape iii — two halves)

Write path: `full_answer += content` on every SSE ANSWER chunk (`server.py:899` ✅ exact) → stored at the DONE event:
```python
# :928-933
_safe_db_write(db, ChatHistory(
        user_id=user_id,
        session_type="research",
        question=PHIDetector.sanitize_for_log(body.question),
        answer=full_answer
    ), label="History Save")
```
(`answer=full_answer` is `:932` ✅ exact.)

Render path: `pages/history.tsx:204-218` (cited `:203-217`, 1-line rust) — `{item.session_type === 'research' && (` → `<p className="whitespace-pre-wrap ...">{item.answer}</p>` inside a `prose` div. No markdown parsing, no section split: `## Summary`, `---`, `[4]` display as raw text. ✅

**Citations — cited "CitationLog" DOES NOT EXIST; see §7-D2.** The CITATIONS SSE event is handled at `:903-915`: `citations_data = [c.model_dump() for c in event.content]`, then (non-anon) written into **`AuditLog`**:
```python
# :907-914
_safe_db_write(db, AuditLog(
        id=audit_id,
        user_id=user_id,
        action="research",
        query_content=PHIDetector.sanitize_for_log(body.question),
        resource_ids=[c.get('source_id') for c in citations_data],
        ip_address="0.0.0.0"
    ), label="Audit Log")
```
`AuditLog` columns (`sql_models.py:5-15`, 8 columns): `id` (String PK = `audit_id`), `timestamp`, `user_id`, `action`, `query_content`, `resource_ids` (JSON), `ip_address`, `extra_data`. **No column references chat_history; ChatHistory has no audit/request id — no correlation key** ✅ (the substantive claim survives the wrong table name). Two aggravations: the AuditLog copy is **lossy** (bare `source_id` strings, not the full Citation dicts — no title/snippet/url/credibility), and per the BACKLOG scoping the audit row is written on CITATIONS while the history row is written on DONE, seconds apart, with no uniqueness.

**Rule 12 consumers** (source of truth → parsers):
- `api/rag/generator.py:363-379` — the instruction: *"Structure the answer as exactly two sections with `## ` markdown headers … do NOT output square brackets"*; `## Summary — …` then `## Clinical Notes — …`. Source of truth ✅.
- `api/services/share_renderer.py::parse_research_sections` (`:138-164`) — splits on `## ` headers, strips leading `---`; docstring: *"Mirrors the JS implementation in pages/research.tsx"*.
- `pages/research.tsx::parseResearchSections` (`:69-95`, **page-local, not exported**) → `sections.map(...)` → `<ResearchSection title>` + `<ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} rehypePlugins={[rehypeRaw]}>` (`:674-688`), preceded by `stripLlmDisclaimer` (`:55`, also page-local) and `ProvenanceLine` (citations-driven), followed by `DISCLAIMERS[detectedLang]`.

**Can history reuse the research renderer as-is?** Partially:
- `components/ResearchSection.tsx` — trivially reusable: props are `{ title: string; children: ReactNode }`, zero data dependencies.
- `ReactMarkdown` + `remark-gfm`/`remark-breaks`/`rehype-raw` — already project dependencies (imported by research.tsx); history.tsx does not import them today.
- `parseResearchSections` + `stripLlmDisclaimer` — **page-local functions in research.tsx; reuse requires extracting them to a shared util (or duplicating)**.
- Citation display is `CitationPanel` (`components/CitationPanel.tsx`, props `{ citations: Citation[]; isLoading? }`; `Citation` = `{id, source_type, source_id, title, snippet, url, credibility, year?, authors?}`) — **needs the citations array history rows do not have** (half B). Note the `[N]` markers are plain text even on /research — ReactMarkdown has no marker→link mapping; resolution is the adjacent panel. So half A alone reaches full prose parity with /research.

### 2c. Verify (shape ii — summary-only at all three INSERT sites)

**Site 1 — main path** (`:1469-1475`; cited `:1473 answer=summary` — the `ChatHistory(` is `:1473`, `answer=summary` is `:1474`):
```python
if not is_anonymous:
    _safe_db_write(db,
        AuditLog(id=audit_id, user_id=user_id,
            action="verify", query_content=f"Checked: {body.drugs}", ip_address="0.0.0.0"),
        ChatHistory(user_id=user_id, session_type="verify",
            question=f"Drugs: {', '.join(body.drugs)}", answer=summary),
        label="Verify")
```
In scope at the INSERT: `interactions` (full `list[DrugInteraction]` — Pydantic: `drug_pair` tuple, `severity`, `severity_label`, `description`, `clinical_recommendation`, `source`, `source_url`, `attribution_kind`), mutated `summary` (spelling-correction + TFDA-note prefixes applied at `:1458-1461`), `risk_level`, `risk_level_label`, `tfda_groundings`, `response_language`. The site constructs `VerifyResponse(...)` at `:1498-1508` from exactly these — **Explain-style `json.dumps` of the full structure is available with no new computation** (needs `.model_dump()` on the Pydantic objects; `drug_pair` tuple → JSON list).
⚠️ Load-bearing constraint at this site: the write-ordering comment (`:1463-1468`) — the write MUST stay after both summary mutations; **guarded by `tests/test_verify_write_ordering.py` (source-order assertion)**. Any restructure keeps that ordering and that test.

**Site 2 — LLM-fallback path** (`:1323-1325`):
```python
if not is_anonymous:
    _safe_db_write(db, ChatHistory(user_id=user_id, session_type="verify",
            question=f"Drugs: {', '.join(body.drugs)}", answer=fb_summary), label="Verify History")
```
In scope: `fb_interactions` (same `DrugInteraction` shape, built `:1307-1319`), `fb_summary`, `fb_data` (`risk_level`, `risk_level_label`), `tfda_groundings`. Its `VerifyResponse` is constructed at `:1349-1361`. **Same shape available, no new computation.**

**Site 3 — total-failure path** (`:1365-1367`):
```python
if not is_anonymous:
    _safe_db_write(db, ChatHistory(user_id=user_id, session_type="verify",
            question=f"Drugs: {', '.join(body.drugs)}", answer=fallback_summary), label="Verify History")
```
In scope: only `fallback_summary` ("No FDA label data found…"), `tfda_groundings`, and the implied empties — its `VerifyResponse` (`:1368-1379`) is `interactions=[]`, `risk_level="Unknown"`, `verification_status="failed_no_data"`. **One VerifyResponse-shaped JSON covers all three sites**: each site can serialize the same field set it already puts in its `VerifyResponse` (site 3's is just the degenerate instance). This is the key sizing fact: the Verify write-path fix is "serialize what the site already returns," at three sites.

**Fourth path, for completeness (writes NO ChatHistory):** `verify_defer_ambiguous` (`:1147-1163`) writes an AuditLog (with **raw un-sanitized brand names** in `query_content`) and returns `verification_status="deferred_ambiguous_brand"` without ever constructing a ChatHistory — confirms "ALL THREE INSERT sites" is the complete history-write set ✅, and re-confirms the BACKLOG's audit-asymmetry exception.

---

## §3. Design inventory — per-entry DELETE (options + interactions; NO decisions)

Authority: the 2026-08-18 BACKLOG scoping (Deletion-feature C → "History-only option" sub-bullets (a)–(f)), re-verified above.

**Core shape** (as scoped): owner-checked `DELETE /api/history/{id}` + frontend control. **The GET half of the scoped build is already done by accident**: row `id` (and `user_id`) are in the response today (§1d), and the sole consumer — `pages/history.tsx:85` fetch, the only `/api/history` reference outside api/, docs and the probe — already types and uses `id`. So "expose id in GET" requires **zero change and can break zero consumers**. (Option flagged in D5: while touching this, an explicit response model could stop over-exposing `user_id`; today it returns the requester's own id, so no cross-user leak.)

**Rule 7 classification:** `_safe_db_write` (`server.py:167-177`) is add+commit only — it **cannot express a DELETE** → the endpoint's DML is **class (a)**, direct `db.query(ChatHistory).filter(...).delete()` + `db.commit()` **with the required call-site comment naming (a)** (precedent comments: `user_context_hash_upsert`, `clerk_webhook`). Note the endpoint likely also needs (b) semantics if the founder wants failure surfaced to the user (a swallowed delete-failure reading as success violates Rule 18) — the comment should name whichever applies.

**Committed-probe interaction (mandatory, by the probe's own text):** `tests/probes/history_readonly_smoke.mjs` asserts `pages/history.tsx` contains **no mutating HTTP verb** (`MUTATING = ["POST", "PUT", "PATCH", "DELETE"]`, `:109`) and no mutating verb string anywhere in the page. Its header `:27-30`: *"THIS GUARD IS NOT HERE TO FORBID A FUTURE MUTATION. If history genuinely needs to write, whoever builds it must DELETE THIS PROBE DELIBERATELY, in the same commit, with the reasoning written down. Removing it IS the decision point."* The delete build must carry that removal (or a rewrite into a narrower guard) as an explicit, reasoned part of the ship commit.

**FLAGGED interactions (presented, NOT designed):**
1. **Design-E account deletion** — `api/services/deletion_service.py::_hard_delete_user` deletes chat_history by user_id (`:204`: `db.query(ChatHistory).filter(ChatHistory.user_id == user_id).delete(synchronize_session=False)`); still **no endpoint calls it**. A per-entry delete is a second, independent deletion path over the same table; semantic questions (shared helpers? consistent audit posture? counsel requirements — see D3) are open.
2. **6-month retention cron** — `_cleanup_old_records` (`server.py:183-201`) age-deletes ChatHistory (>180d) daily. Per-entry delete coexists trivially at the SQL level; the open interaction is **promise-level**: the adjacent `[COMPLIANCE]` entries record that `/privacy` §4 already tells users they can delete their chat history (zero delete routes exist — TECH_DEBT `:278`) and that the cron **may never have run** (sleeps 24h before first run + `auto_stop_machines`; UNDECIDABLE until the 2026-09-15 recheck — TECH_DEBT `:279`). A shipped per-entry delete partially discharges the first entry; neither is closed by it.
3. **BACKLOG scoping (c), open in EVERY option:** `user_feedback` stores its **own full copies** of query+response with no chat-history reference — verbatim from `create_feedback` (`server.py:1729-1737`): `query=feedback.query, response=feedback.response` (raw from the client body; only `feedback_text` is sanitized; `sql_models.py:35-36`). A per-entry delete keyed on chat_history **leaves a complete copy behind** whenever the user rated that answer.
4. **Option (d)(iii)** — audit_logs ruled out of per-entry scope (endpoint + owner check + single-table delete + frontend; ~1 day, no migration) — **is the recorded front-runner and explicitly NOT DECIDED** (BACKLOG: *"the founder has not ruled"*). Alternative (d)(ii): audit rows in scope but uncorrelatable → migration + changes at all 5 ChatHistory write sites + permanent two-tier semantics; not a one-day job. (d)(i) is counterfactual.
5. **Counsel's three account-deletion requirements** (double confirmation stating irreversibility / audit record without personal data / 30-day backup notice — BACKLOG, written opinion 2026-08-11) — **do they bind a per-entry delete?** Founder/counsel question; nothing in the recorded opinion answers it either way.

**Anonymous rows — handling OPTIONS (no choice made):** (i) show no control for any row the requester doesn't own (moot in practice — the GET is already owner-scoped, so users only ever see their own rows); (ii) endpoint returns 404 on a non-owned/absent id (indistinguishable-from-missing, the conventional choice for IDOR resistance); (iii) 403. Derived fact from §1e that shrinks this question: **the identity-less population is empty-by-construction at HEAD** — the real design point is only "owner mismatch → 404 vs 403," not a special anonymous-row branch.

**Rule 16 / i18n (2026-08-18 measurement re-verified at HEAD):**
- Key-name search `^(delete|clear|remove|discard|trash)…:` across all **8** `utils/i18n*.ts` files (`i18n.ts`, `-anonymous`, `-bug-report`, `-extra`, `-faq`, `-share`, `-ui`, `-verify`) → **0 key names** (cited 0 ✅; unit: key declarations; textual *values* like the FAQ's "deleted after 180 days" excluded by the key-position regex).
- Reusable: `modalCancel: 'Cancel'` (`utils/i18n-share.ts:72` — cited line exact ✅) and `closeBtn: 'Close'` (`utils/i18n-bug-report.ts:51`). **NOT reusable: `modalConfirm` = `'Create public link'`** (`i18n-share.ts:71`) ✅.
- No shared confirm-modal component; two hand-rolled dialogs verified at cited coordinates: `components/MySharesTab.tsx:274-311` (`{revokeTarget && (` … `)}`, 38 lines) and `components/Navbar.tsx:365-412` (`{showCancelConfirm && (` … `)}`, 48 lines). A delete modal makes **three** (option: extract a shared confirm-modal — see D6).
- Estimate: **4–5 new keys × 16 locales = 64–80 strings**, tsc-enforced (keys belong to a full `Record<LangCode, …>`). ⚠️ The confirm text must be **written for irreversibility**, not adapted from revoke (revoke is reversible). ⚠️ A **WRITE-failure string is required and none exists to borrow** — the revoke path today reuses a load-failure string (`mySharesError`) for write failures.
- Rule 14 side-note: a delete action would conventionally emit a PostHog event via `utils/analytics.ts` `track()` — include in the keys/UX budget if desired.

---

## §4. Design inventory — fidelity fixes (options + interactions; NO decisions)

### Verify write-path (candidate first segment — stops ongoing data loss)

- **Stored shape options:** (i) Explain-parity — `answer=json.dumps({...}, ensure_ascii=False)` of the VerifyResponse-equivalent structure into the existing Text column (no schema change, mirrors `:1566`); (ii) a new column (migration — note `migrations/` currently has zero statements about chat_history; the model + `create_all` covers only fresh DBs, so existing prod/dev DBs need migration 009); (iii) per-site shapes. Sizing fact from §2c: **one shape covers all three sites with no new computation** — each site already assembles the exact fields for its `VerifyResponse`; site 3 is the degenerate instance (`interactions=[]`, `verification_status="failed_no_data"`). Serialization detail: `DrugInteraction` is Pydantic (`.model_dump()`; `drug_pair` tuple→list).
- **Renderer reuse:** the verify page has **no extracted card component** — cards are inline in `pages/verify.tsx:589-628` (`result.interactions.map(...)`, local `getSeverityStyle`/`getSeverityBadge` at `:350-367`). Options: extract a `VerifyInteractionCard` component consumed by both pages, or duplicate the JSX in history.tsx. The i18n helpers it uses are already shared, frontend, lang-keyed: `formatInteractionSummary, getSeverityLabel, getRiskLevelLabel, getAiSeverityNote, getSourceCaptionByKind, getSourcePrefix` from `utils/i18n-verify` (`verify.tsx:18-19`) — importable by history.tsx as-is.
- **Legacy rows:** reuse the Explain safe-parse pattern (§2a) — `JSON.parse` try/catch + shape check (e.g. `Array.isArray(parsed.interactions)`) → cards; else plain text. **Old rows CANNOT be backfilled** — the detail was never written, and no correlation key exists to recover it from any other table (AuditLog rows for verify carry no answer at all).
- **Rule 19 carry-across list — what the verify PAGE does *around* this data** (each must be carried or explicitly declined in writing at build time):
  | # | Mitigation on /verify | Anchor |
  |---|---|---|
  | 1 | Severity label localized from the **canonical enum**, never the stored `severity_label` free-text (wrong-language leak documented in-page) | `verify.tsx:31-32`, `:375-377`, `getSeverityLabel(lang, interaction.severity)` `:602` |
  | 2 | Option-C AI-severity marker in the same eyeline (*"the severity is Vela's AI judgment, NOT the label's grading"*) | `:598-607`, `getAiSeverityNote(lang)` |
  | 3 | Attribution caption keyed off the **stable `attribution_kind` enum**, NOT the raw English `source` string; wrapped in `source_url` link when present | `:615-625`, `getSourceCaptionByKind` |
  | 4 | Localized summary **recomputed client-side from the interactions array** (`formatInteractionSummary(lang, interactions.length, breakdown)`), not the stored English `summary` | `:371-401` |
  | 5 | Risk-level label via `getRiskLevelLabel` (enum-keyed) | `verify.tsx:18` |
  | 6 | Disclaimer rendered from the response field (Rule 10 posture: never LLM-generated) | `:633-637` |
  | 7 | TFDA-grounding transparency block (`tfda_groundings` display) + `verification_status`/`deferred_brands` handling | interfaces `:40-60` |
  A history renderer fed the stored JSON inherits the *ability* to do 1–5 only if the enums (`severity`, `attribution_kind`, `risk_level`) and the structured fields are what gets stored — a second argument for the full-structure shape over any trimmed one.
- **Write-ordering constraint:** `tests/test_verify_write_ordering.py` asserts the main-site write stays after the summary mutations (`server.py:1463-1468`). If the stored shape embeds `summary`, the mutated string must be the one embedded — the constraint transfers to the JSON build.

### Research

- **Half A (frontend-only) IS shippable without half B.** It touches no `api/` file: extract `parseResearchSections` + `stripLlmDisclaimer` from `pages/research.tsx` (both page-local today) into a shared util, reuse `ResearchSection` (props `{title, children}` — zero deps) + `ReactMarkdown` with the same plugin set, inside history's expanded research block. Result: `## Summary` / `## Clinical Notes` render as the same cards as /research, lists and emphasis render, `---` is consumed by the parser; **bare `[N]` markers remain plain text — exactly as they are on /research itself** (no marker→link mapping exists there either; resolution is the adjacent `CitationPanel`, which needs data history doesn't have). Optional styling of `[N]` is cosmetic-only and unresolvable until half B.
- **Half B (write-path; old rows unbackfillable) options:** (i) **embed citations in the answer JSON** — Explain-parity: store `json.dumps({"answer": full_answer, "citations": citations_data})`; no schema change; history's research renderer then safe-parses (legacy plain-markdown rows fall back to half A's path); note `citations_data` (`server.py:904`) is in scope at CITATIONS time but the history write happens later at DONE — a local variable carries it, same function scope; (ii) **new column** (`citations` JSON on chat_history) — migration 009 + write change; keeps `answer` as clean markdown; (iii) **correlation key** to the audit row (which already holds lossy `source_id`s) — migration + two-tier semantics, and STILL lossy (no title/snippet/url/credibility — the full `Citation` shape in `CitationPanel.tsx:29-42` could not be reconstructed). Fact for sizing: the share flow already snapshots full citation dicts at share time (`SharedQuery.citations` JSON), so precedent for option (i)/(ii)'s payload shape exists in-repo.
- Half A alone changes the history ShareButton nothing — but note the pre-existing gap it sits next to: history's ShareButton passes `citations={[]}` (`history.tsx:279`), so research shares created from /history already lose citations; half B option (i)/(ii) would make fixing that possible (not in scope here — recorded as an adjacency).

### MANDATORY cross-ref — the `[COMPLIANCE][P2]` unsanitized-answer entry

Quoted from `TECH_DEBT.md:1552-1557`:
> `[P2 · R5 privacy] ChatHistory.answer stored unsanitized (all features)` (logged 2026-06-08) … **🔴 RE-POINTED 2026-08-11 (written legal counsel opinion) — ACCEPTED AS-IS. NOT CLOSED.** Counsel judged the current asymmetry (**`question` masked, `answer` not**) **ACCEPTABLE**, on four grounds together: **input-side blocking** at the boundary, **180-day retention** (`_cleanup_old_records`, `api/server.py:183-197`), **non-public storage**, and **operator-only access**. … ⚠️ **Kept OPEN deliberately.** "Accepted" is a risk decision on today's facts … **Do not re-tag `[DONE]`.** … **The optional hardening is a POST-PROCESSING REGEX MASK** — run `PHIDetector.sanitize_for_log` over `answer` at the five write sites … Counsel does not require it. … the share flow does **not** read from here.

Per store-more option:
- **Verify full-structure:** enlarges the surface **modestly in kind, not in class** — today's verify `answer` already holds drug names (raw; verify applies no sanitize anywhere — BACKLOG (c) note) inside an English summary; the structure adds LLM-generated `description`/`clinical_recommendation` per pair. Inputs are drug names + optional `patient_context` (PHI-gated at the boundary — ground 1 of counsel's four). Mitigation options: run `sanitize_for_log` over the serialized JSON (string-level, shape-safe since the mask is regex-on-text), or over the text fields individually; or record an explicit decline. None decided here.
- **Research half B (citations):** adds titles/snippets/urls of retrieved public literature — no user-authored text beyond what `answer` already holds. Smallest enlargement; still an enlargement in bytes retained per row.
- **Research half A / delete feature:** store nothing new — no interaction with this entry (the delete *reduces* retained data).
- Counsel's four grounds are unchanged by any option above (retention still 180d, storage still non-public, access still operator-only, input blocking untouched) — but per the entry's own terms, a write-path change is exactly when it "must be re-read." Flagged as D8.

### Sequencing facts (founder decides; facts only)

- **Per-mode daily write volume: not derivable in this recon** — it lives in the prod Neon DB (`chat_history` GROUP BY session_type) and this recon is read-only local + one prod `/health` GET. No committed artifact carries it (Rule 20: stated rather than estimated).
- **Blast radius:**
  | Fix | Files touched | Deploy | Migration |
  |---|---|---|---|
  | Verify write-path + renderer | `api/server.py` (3 sites) · `pages/history.tsx` · optional `components/VerifyInteractionCard.tsx` extraction from `verify.tsx` | full deploy car (api/ change) | none (option i) |
  | Research half A | `pages/history.tsx` · extraction from `pages/research.tsx` (+ new shared util) | frontend-only change; no api/ file | none |
  | Research half B | `api/server.py` (research DONE handler) · `pages/history.tsx` | full deploy car | none (option i) / 009 (option ii/iii) |
  | Per-entry delete (d)(iii) | `api/server.py` (endpoint + CORS `allow_methods`) · `pages/history.tsx` (control + modal) · i18n file(s) (4–5 keys × 16) · **delete/rewrite `tests/probes/history_readonly_smoke.mjs` in the same commit** · optional shared modal component | full deploy car | none |
- **Test surface over the write sites:** `tests/test_verify_write_ordering.py` (source-order assertion, main verify site) is the only dedicated pytest guard; `tests/probes/history_readonly_smoke.mjs` (node, committed evidence) guards the page. Other pytest files matching "history" (`test_floor_verdict_wiring_guard.py`, `test_ownership_eval_labels.py`, `test_theme_tokens.py`) are incidental mentions. `tests/test_deletion_coverage.py` guards the account-deletion table lists (relevant if the per-entry build touches `deletion_service.py`). Baseline: 400 passed / 28 skipped (§0).

---

## §5. Deliverable

This document: `docs/batons/recon_20260901_history_car.md`, committed locally (not pushed) as `docs(history): recon for history car — per-entry delete + fidelity design inventory`.

---

## §6. Flagged founder decisions (the section to rule from)

1. **Delete scope option:** ratify or reject the recorded front-runner **(d)(iii)** — audit_logs OUT of per-entry scope (single-table delete, ~1 day, no migration) — vs. (d)(ii) (audit rows in scope: migration + all-5-write-site changes + permanent two-tier). The ledger marks (iii) "front-runner, explicitly NOT DECIDED."
2. **`user_feedback` full copies (BACKLOG (c))** — open in EVERY option: leave the copies (and disclose where?), attempt heuristic cascade, or rule out of scope for the per-entry car.
3. **Do counsel's three account-deletion requirements bind a per-entry delete?** (double confirmation stating irreversibility / audit record without personal data / 30-day backup notice). Founder/counsel question; the modal copy and any delete-audit record depend on it.
4. **Endpoint semantics for non-owned/absent id:** 404 vs 403 (the "anonymous rows" branch is empty-by-construction at HEAD — §1e/§7-D3 — so this is the whole question).
5. **Verb + CORS:** true `DELETE /api/history/{id}` requires extending `allow_methods=["GET", "POST"]` (`server.py:310`); alternative is a POST route with no CORS change. Sub-option while in the endpoint: add an explicit response model to GET `/api/history` (stops over-exposing `user_id`; `id` stays, it is load-bearing).
6. **Third hand-rolled confirm dialog vs extracting a shared confirm-modal component** (existing two: `MySharesTab.tsx:274-311`, `Navbar.tsx:365-412`); plus the i18n budget (4–5 keys × 16, irreversibility-written confirm text, new write-failure string) and whether a `track()` delete event is wanted.
7. **Sequencing of the fidelity fixes:** is the **Verify write-path** the first segment (it stops ongoing, unbackfillable data loss on every verify query)? And within it: one VerifyResponse-shaped JSON across all three sites (the sizing facts support it) vs per-site shapes; extract a shared card component vs duplicate JSX.
8. **Research:** ship **half A alone** (frontend-only, no api/ change, `[N]` stays plain text as on /research) ahead of half B? For half B: embed-in-answer-JSON vs new `citations` column (migration 009) vs correlation key (lossy, weakest — facts in §4).
9. **COMPLIANCE re-read trigger:** storing MORE per row is the event the unsanitized-answer entry says warrants a re-read. Choose per option: apply the optional `sanitize_for_log` hardening to the stored answer/JSON, or record an explicit decline (counsel does not require it; the four acceptance grounds are otherwise unchanged).
10. **Probe retirement acknowledgment:** the delete ship-commit must deliberately delete (or narrow) `tests/probes/history_readonly_smoke.mjs` with written reasoning — the probe's own header makes removal the decision point. Acknowledge this lands inside the delete car, not as a drive-by.

---

## §7. Discrepancies (derived ≠ cited — both readings, reconciled)

**D1 — "The PK is never sent to the client" is FALSE at HEAD (and the delete build shrinks).**
- *Cited:* TECH_DEBT fix-shape (`:326`): "`ChatHistory` has an Integer autoincrement PK that is **never sent to the client** (`GET /api/history` would need to expose it)"; BACKLOG (a): "its PK is DB-assigned and never sent anywhere". The recon prompt's §3 inherits it ("expose row `id` in GET").
- *Derived:* the endpoint returns raw ORM rows with no response_model (`server.py:1843`); FastAPI's `jsonable_encoder` emits all 6 columns (empirically reproduced — `HAS_ID: True`); `pages/history.tsx:30-37` types `id`/`user_id` and the page uses `item.id` for keys, expand-toggle and `ShareButton queryId` (`:276`) — per-entry expand works on prod fly 241, which it could not if `id` were absent.
- *Reconciled:* the same BACKLOG entry's own bullet (b) records `pages/history.tsx:276` storing `String(item.id)` — **the scoping document contradicts itself internally**, and bullet (b) is the correct half. The (a) sentence reads as "no serializer deliberately exposes it," which is true of intent but false of behavior, and it was false when filed (the `HistoryItem` interface predates the scoping). Effect: the scoped build loses its GET half — only the DELETE endpoint + frontend control + i18n remain. The TECH_DEBT fix-shape sentence should be corrected when the car opens (not fixed in this read-only recon).

**D2 — "CitationLog" does not exist; the actual sink is `AuditLog.resource_ids`, and it is lossy.**
- *Cited:* TECH_DEBT (`:331`): citations stream "into `CitationLog`, not into `ChatHistory`"; the recon prompt inherits "into `CitationLog` … quote the CitationLog write and its columns."
- *Derived:* repo-wide grep for `CitationLog|citation_log` matches only the TECH_DEBT line itself. The CITATIONS handler writes `AuditLog(resource_ids=[c.get('source_id') …])` (`server.py:907-914`).
- *Reconciled:* the substantive claim **survives** — no correlation key to chat_history exists (AuditLog's 8 columns contain none; ChatHistory carries no audit id) — but the named table is wrong, and the correction strengthens the finding: even the audit-side copy holds bare `source_id` strings, not the full `Citation` dicts, so option (iii) of half B could never reconstruct what `CitationPanel` renders. Ledger wording to correct at car-open.

**D3 — "anonymous rows" describes a population current code cannot create.**
- *Cited:* TECH_DEBT fix-shape: "anonymous rows are unreachable by any per-entry delete keyed on `chat_history`."
- *Derived (§1e):* every history write site is `is_anonymous`-guarded or auth-required; `require_auth_or_anonymous` returns exactly one identity; pre-anon-tier (`7a8c5a8`) code required auth. No live path writes an identity-less row; L0 users have **no history rows at all** (and no way to call the authed endpoint).
- *Reconciled:* the sentence is true in the vacuous sense (L0 activity leaves nothing a per-entry delete could reach — by design, per the `:905` comment) but misleads as written, implying an existing orphan population needing special handling. The only conceivable identity-less/synthetic rows are TEST_MODE artifacts (`test_user`), which never legitimately reach prod (the BACKLOG near-miss entry records one averted case). Design consequence: no anonymous-row branch is needed in the endpoint; D4 (404 vs 403) is the entire question.

**D4 — line-number rust (substance unchanged, symbols verified):** verify main-site write cited `:1473 answer=summary` → at HEAD `ChatHistory(` `:1473`, `answer=summary` `:1474`; the COMPLIANCE entry and BACKLOG (d) cite the five write sites as `:928/:1324/:1366/:1462/:1570` (verified 2026-08-11/18) → at HEAD `:928/:1324/:1366/:1473/:1576`; history.tsx research block cited `:203-217` → `:204-218`; explain block cited `:219-268` → `:220-269`; explain write cited `:1576-1593` → ChatHistory call `:1576-1581` (json.dumps at `:1566`). All five sites and both render blocks confirmed by symbol + verbatim quote in §2. Counts unchanged: 3 verify sites, 5 total ChatHistory sites (unit: `ChatHistory(` construction sites in `api/server.py`).

**D5 — side-flag (Collaboration Principles: flagged, not fixed):** `api/services/deletion_service.py:88` cites its coverage guard as `tests/test_deletion_table_coverage.py`; the file on disk is `tests/test_deletion_coverage.py`. One-word comment drift, found while verifying §3 interaction 1.

---

*Recon executed 2026-09-01 at HEAD `4a99eec` against prod fly 241 (`8b8886d`). Read-only: the only repo mutation is this document.*

---

## §8 — Segment 1 eye gate (BLANK — founder fills)

> **Theme-eye style gate (fly-241 /explain precedent); authorized by founder ruling 2026-09-01 (Segment 1 build conversation); results to be entered by the founder only.**
> Prepared 2026-09-02 at HEAD `2183dd5`, local stack: backend `:8000` (TEST_MODE, dev Neon branch `ep-spring-voice-a127ye10`), frontend `http://localhost:3000/history`. Seeded rows (all `test_user`): **(a) id 2325** verify JSON (minted via a real local /api/verify, aspirin+warfarin) · **(b) id 2326** legacy verify summary · **(c) id 2327** conforming research sections · **(d) id 2328** legacy research free text · **(e) id 2324** existing full-JSON explain row (2026-08-31). Toggle theme with the app's own theme switch; run every /history row in BOTH schemes.
> ⚠️ No AI observation is a gate result. All PASS/FAIL and notes cells below are blank by construction.
>
> **PREP NOTE 2026-09-02 (post-first-pass fixes — cells still founder-only):** two founder-observed items fixed in `fix(history): single disclaimer marker + verify share button placement`: **(1) double ⚠️ on the verify disclaimer — PRE-EXISTING, NOT introduced by segment 1** (evidence: all 16 `VERIFY_DISCLAIMERS` values begin with ⚠️ at prod `8b8886d` AND at `8f3ef82`, and prod's `pages/verify.tsx:633-635` prepends a second `⚠️ {result.disclaimer}` — prod fly 241 double-renders today; segment 1 copied the same prepend into history via carry-across #9). Fix: the JSX prepend removed at both sites; i18n values untouched. **Row 11 records against a pre-existing defect, not a segment-1 regression.** **(2)** verify row's ShareButton moved to the BOTTOM of the expanded entry (matches Explain/Research; share text still `verifyParsed?.summary ?? item.answer`, guard test green). **Re-eye needed: rows 1–4 (card layout + share position + single ⚠️) and row 11 (single ⚠️ on the live page).** Rows 5–10 are untouched by these fixes.

| # | Row · scheme | What to look at | Expected observation | PASS/FAIL | Notes |
|---|---|---|---|---|---|
| 1 | (a) id 2325 — LIGHT | Expand "Drugs: aspirin, warfarin" | Structured cards, NOT raw JSON and NOT a plain box: localized summary line ("Found 1 interaction(s): 1 Major" register, colour = highest severity) + risk badge (Major, red family) · one interaction card "aspirin ↔ warfarin" with severity badge, ⓘ AI-severity note, description/recommendation, italic attribution line as a working link · disclaimer line under a top border | **PASS** | |
| 2 | (a) id 2325 — DARK | Same row, dark scheme | Same content; severity/risk colours legible on dark (danger/warning/info tokens flip); no white-on-white / black-on-black | **PASS** | |
| 3 | (b) id 2326 — LIGHT | Expand "Drugs: lisinopril, ibuprofen (GATE row b — legacy)" | EXACTLY the pre-segment-1 rendering: one plain rounded box with the text "Found 1 interaction(s): 1 Major" — no cards, no badge, no crash | **PASS** | |
| 4 | (b) id 2326 — DARK | Same row, dark scheme | Same plain box, legible | **PASS** | |
| 5 | (c) id 2327 — LIGHT | Expand "metformin renal dosing (GATE row c — conforming sections)" | TWO section cards titled "Summary" and "Clinical Notes" (left-accent card style, same as /research): bold/bullets render as markdown, the `---` separator consumed; `[1]`-style markers appear as PLAIN TEXT (no links, nothing clickable) | **PASS** | |
| 6 | (c) id 2327 — DARK | Same row, dark scheme | Same section cards, prose legible, bullet markers visible | **PASS** | |
| 7 | (d) id 2328 — LIGHT | Expand "metformin overview (GATE row d — legacy free text)" | The old pre-wrap paragraph rendering (no section cards, no crash, not blank) | **PASS** | |
| 8 | (d) id 2328 — DARK | Same row, dark scheme | Same paragraph, legible | **PASS** | |
| 9 | (e) id 2324 — LIGHT | Expand the eGFR/HbA1c explain row | ZERO REGRESSION: ExplainItemCards + Clinical Correlations exactly as before segment 1 | **PASS** | |
| 10 | (e) id 2324 — DARK | Same row, dark scheme | Same, legible | **PASS** | |
| 11 | /verify live page — extraction parity | Run one Verify query on `http://localhost:3000/verify` (e.g. aspirin + warfarin), LIGHT then DARK | The live result looks IDENTICAL to pre-segment-1 /verify: summary line + risk badge + interaction cards with severity badge, ⓘ note, attribution link — the card extraction must be invisible here | **PASS** | |

**Founder sign-off line (name · date · overall verdict):** Andrew Lee (founder) · 2026-09-02 · **11/11 PASS** — "All 11 cells founder-PASS, verdict delivered in the build conversation 2026-09-02 (first pass + post-fix re-eye of rows 1-4/11); transcribed by Claude Code under the founder's written authorization embedded in the closeout instruction — provenance per the 2026-09-01 zh-TW transcription precedent."

---

## §9 — Delete segment eye gate (BLANK — founder fills)

> **Theme-eye style gate (§8 precedent); authorized by founder ruling 2026-09-02 (delete-segment build instruction); results to be entered by the founder only.**
> Prepared 2026-09-02 at local commits `9a3dd15` (endpoint) + `74df707` (UI). Stack: the founder's own dev stack (backend `:8000` TEST_MODE + frontend `http://localhost:3000/history` — per the segment-1 environment rule, no dev server was started by the build session). Any rows work; the §8 seeded set (ids 2324–2328, `test_user` on dev Neon branch `ep-spring-voice-a127ye10`) is available if still present — **row (d) needs a LEGACY row** (e.g. id 2326 verify-summary or 2328 research free-text). Toggle theme with the app's own switch; run each check in BOTH schemes.
> ⚠️ No AI observation is a gate result. All PASS/FAIL and notes cells below are blank by construction.

| # | Check · scheme | What to look at | Expected observation | PASS/FAIL | Notes |
|---|---|---|---|---|---|
| 1 | (a) delete control — LIGHT | Expand any history row | A "Delete" control (danger-outline, localized) at the bottom of the expanded entry, right of the Share button; legible, not overlapping | **PASS** | |
| 2 | (a) delete control — DARK | Same row, dark scheme | Same control, danger colour legible on dark | **PASS** | |
| 3 | (b) confirm modal — LIGHT | Click Delete, then Cancel | Modal opens: title "Delete", body text states the deletion is PERMANENT / cannot be undone (legible, correct locale); Cancel closes the modal and **the row survives** (still in the list after cancel) | **PASS** | |
| 4 | (b) confirm modal — DARK | Same, dark scheme | Same modal, text and both buttons legible; cancel works; row survives | **PASS** | |
| 5 | (c) confirmed delete — LIGHT | Click Delete → confirm | Row disappears from the list immediately, no error, no full-page reload; a page refresh shows it still gone (DB-real, not display-only) | **PASS** | |
| 6 | (c) confirmed delete — DARK | Same on another row, dark scheme | Same behaviour | **PASS** | |
| 7 | (d) legacy row — LIGHT | Delete a LEGACY row (pre-segment-1 shape, e.g. id 2326/2328) | Deletes identically to a new-format row — the control, modal and removal do not depend on the stored answer shape | **PASS** | |
| 8 | (d) legacy row — DARK | Same class of row, dark scheme | Same behaviour | **PASS** | |
| 9 | (e) failure path — LIGHT | Simulate write failure if practicable: stop the backend (or DevTools → Network → Offline) AFTER the page has loaded, then Delete → confirm | The modal STAYS OPEN and shows the write-failure string (localized, legible); the row is STILL in the list; Cancel then dismisses. If not simulable in this pass, mark N/A with reason | **N/A** | Not simulated — no run record in the build conversation; marked per this form's own allowance rather than transcribing an unobserved PASS. The failure branch is unit-covered (write-failure string kept, dialog stays open) in `74df707`. |
| 10 | (e) failure path — DARK | Same, dark scheme | Same; failure string legible on dark. N/A with reason if not simulated | **N/A** | Not simulated — no run record in the build conversation; marked per this form's own allowance rather than transcribing an unobserved PASS. The failure branch is unit-covered (write-failure string kept, dialog stays open) in `74df707`. |

**Founder sign-off line (name · date · overall verdict):** Andrew Lee (founder) · 2026-09-02 · **8/8 PASS + 2 N/A (failure path not simulated)** — "Founder-PASS, verdict delivered in the build conversation 2026-09-02 incl. founder's own zh-TW confirm-text review; transcribed under the written authorization in the closeout instruction — provenance per the 2026-09-01 zh-TW precedent."

---

## §10 — Segment 3 eye gate: Research half B, citation persistence (BLANK — founder fills)

> **Theme-eye style gate (§8/§9 precedent); authorized by founder ruling 2026-09-02 (segment-3 build instruction: *"Research half B = embed citations in the answer JSON"* — §4 option (i); §6#8 posed the three options without a ruling, the ruling is recorded in the TECH_DEBT fidelity entry as the entry of record); results to be entered by the founder only.**
> Prepared 2026-09-02 at local commits `62682f5` (backend: `_research_history_payload` → `{"kind":"research_v1","answer":<markdown>,"citations":[…]}` at the single Research write site `api/server.py` DONE branch) + `3f3da85` (frontend: `parseResearchAnswer` → half-A sections fed the MARKDOWN + the shared `CitationPanel`). **NOT pushed, NOT deployed — prod still fly 243.** Stack: the founder's own dev stack (backend `:8000` TEST_MODE + frontend `http://localhost:3000/history` — per the segment-1 environment rule, no dev server was started by the build session; `PYTHONUTF8=1` before uvicorn, cp950 P3).
> **Rows to have on hand (all `test_user`, dev Neon branch `ep-spring-voice-a127ye10` if still in use):**
> **(n)** ONE NEW research row — run any Research query on `http://localhost:3000/research` AFTER checking out `3f3da85` and restarting the backend; the DONE write now stores research_v1 JSON automatically (pick a query that returns ≥1 reference, e.g. *metformin renal dosing*).
> **(o)** a PRE-segment-3 research row — the §8 seed **id 2327** (conforming sections, plain markdown) and **id 2328** (legacy free text) if still present; otherwise any research row created before this build.
> **(m)** a MALFORMED-JSON research row — must be hand-seeded, e.g. `INSERT INTO chat_history (user_id, session_type, question, answer, created_at) VALUES ('test_user', 'research', 'GATE row (m) — malformed JSON', '{"kind": "research_v1", "answer": ', NOW());` (the truncated payload is the shape the `.mjs` guard covers as *"truncated JSON → null"*).
> ⚠️ **Read before row 7:** history's ShareButton passes `citations={[]}` — a pre-existing adjacency recorded in §4 (*"research shares created from /history already lose citations"*), deliberately NOT changed this segment (it would change what a PUBLIC share page shows — a scope call, not a build call). Row 7 checks that the share page shows the MARKDOWN and not JSON; the absence of a references block on that share page is EXPECTED and is not a segment-3 defect.
> ⚠️ No AI observation is a gate result. All PASS/FAIL and notes cells below are blank by construction.

| # | Row · scheme | What to look at | Expected observation | PASS/FAIL | Notes |
|---|---|---|---|---|---|
| 1 | (n) new research row — LIGHT | Expand the row created after this build | TWO section cards "Summary" / "Clinical Notes" exactly as the §8 row (c) rendered, THEN a references block beneath them in the same card style as the /research right column: "References (N)" title, source-count chips, one card per citation with `[N]` + source name, title, authors/journal/year, abstract with Show more, "View source" link where the URL is absolute. `[N]` markers inside the prose stay PLAIN TEXT (no links) — as on /research | | |
| 2 | (n) new research row — DARK | Same row, dark scheme | Same content; card backgrounds, chip pills and link colour legible on dark; no white-on-white | | |
| 3 | (o) pre-segment-3 row — LIGHT | Expand id 2327 (or any pre-build research row) | EXACTLY the segment-1 half-A rendering: section cards (or the pre-wrap paragraph for 2328), literal non-resolving `[N]`, and NO references block — nothing new appears for old rows | | |
| 4 | (o) pre-segment-3 row — DARK | Same row, dark scheme | Same, legible | | |
| 5 | (m) malformed-JSON row — LIGHT | Expand "GATE row (m) — malformed JSON" | The pre-wrap paragraph showing the raw stored text `{"kind": "research_v1", "answer": ` — NOT blank, NO crash, no references block | | |
| 6 | (m) malformed-JSON row — DARK | Same row, dark scheme | Same, legible | | |
| 7 | share page of (n) | From the expanded (n) row click Share → create → open the `/q/<id>` page (LIGHT is enough) | The public page shows the answer MARKDOWN (sections/bullets rendered) — NOT a JSON blob, NOT a string beginning with `{"kind"`. (No references block on this share page is expected — see the ⚠️ above) | | |
| 8 | /research live page — parity | Run one Research query on `http://localhost:3000/research`, LIGHT then DARK | IDENTICAL to pre-segment-3 /research: answer sections + provenance line on the left, the references column on the right — this build touched neither `pages/research.tsx` nor `components/CitationPanel.tsx` (diff-empty), so any difference here is a defect | | |
| 9 | zh-TW strings | Switch the UI language to 繁體中文, expand row (n) | The references block shows the existing zh-TW strings only: the English-references caption above the panel (the same `citationLanguageNote` text /research shows), the 參考文獻 title, chips, 查看來源 / 顯示更多. No English leak, no raw key names, no NEW string anywhere (0 i18n keys were added) | | |

**Founder sign-off line (name · date · overall verdict):** _________________________
