# 在地差異提示 — Probe 1 dogfood / eval queries

This file is **the human-eye acceptance gate for Probe 1** (the deterministic-keyword 在地差異提示 panel)
and the **eval set for a possible future LLM trigger**. All queries are zh-TW so `lang` resolves to
`zh-TW` and the panel is eligible to render. Run each on Research (with the preview hatch on), and judge:
does the panel read as *signal* (relevant to a real Taiwan local-difference) or *wallpaper* (fires on
generic answers)? The TRICKY section is the decision input for whether to graduate from keyword matching
to an LLM classifier.

Trigger input = `userQuery + '\n' + finalAnswer` (so a category keyword in either the question or the
generated answer can fire). v0 keyword lists live in `utils/localeHint.ts` and are meant to be tuned.

## SHOULD FIRE
| Query (zh-TW) | Expected category |
|---|---|
| 「warfarin 在台灣的健保給付條件是什麼」 | reimbursement |
| 「metformin 的最大劑量是多少」 | dosing |
| 「SGLT2 抑制劑的核准適應症有哪些」 | indication |
| 「amiodarone 有哪些禁忌症」 | contraindication |
| 「台灣 statins 的健保給付規定」 | reimbursement |
| 「鋰鹽的起始劑量怎麼調整」 | dosing |
| 「PCSK9 抑制劑在台灣是自費還是健保給付」 | reimbursement |
| 「isotretinoin 的黑框警告是什麼」 | contraindication |
| 「DPP-4 inhibitor 仿單上的適應症」 | indication |
| 「老年人 benzodiazepine 的劑量調整建議」 | dosing |

## SHOULD NOT FIRE
| Query (zh-TW) | Why not |
|---|---|
| 「糖尿病的病理機轉是什麼」 | mechanism |
| 「高血壓的全球盛行率」 | epidemiology |
| 「什麼是 HbA1c」 | definition |
| 「RAAS 系統如何運作」 | mechanism |
| 「阿茲海默症最新研究進展」 | general research |
| 「心衰竭的分類標準」 | general classification |

## TRICKY / WATCH
These probe whether keyword matching is too blunt — the decision input for whether we later graduate
to an LLM classifier.

| Query (zh-TW) | Watch |
|---|---|
| 「warfarin 和 aspirin 的交互作用」 | interaction — should it count as a local-diff? `交互作用` is **intentionally excluded** in v0; expect NO fire unless dosing/etc. keywords appear in the answer |
| 「metformin 的副作用有哪些」 | general side-effects — potential over-fire if we ever add `副作用`; v0 excludes it, but the answer may contain `劑量`/`mg` and fire on dosing — eyeball whether that's correct |
| 「糖尿病患者的飲食建議」 | lifestyle — should NOT fire (no category keyword); watch for false positives from the answer text |

## BEHAVIORAL CHECKS (gate logic, not keyword-fire)

These verify the two gate mechanisms that keyword-fire rows don't exercise. Run with the preview
hatch on (`localStorage vela_locale_hint_preview = '1'`), UI language = 繁體中文.

| Check | How to run | Expected (gate PASS) |
|---|---|---|
| **isFallback suppression** | Ask a zh-TW query that returns the **no-literature fallback** banner (「未找到相關文獻」/「基於一般醫學知識」) *and* would otherwise fire a category — e.g. a reimbursement/dosing question about an obscure or hypothetical drug so no literature is retrieved. Confirm you see the fallback banner. | Panel is **SUPPRESSED** even though a category keyword (e.g. `給付`/`劑量`) is present — an ungrounded answer must not get false local-authority credibility (`!isFallback` gate, `research.tsx`). |
| **Dismiss-then-new-query re-show** | On any SHOULD-FIRE query, dismiss the panel (×). Then submit a **different** SHOULD-FIRE query. | Panel **RE-SHOWS** on the new query — dismissal is per-query via `resetKey`, NOT cross-session. Regression guard for the v187「fires once then never again」bug. |

---

## b1 — locale-detection waterfall + Tier-2 fallback + SG/MY (pinned 2026-07-24) — PROD HUMAN-EYE GATE

The everything-above section is the **fly-210 TW regression suite** (row 13). b1 rewrites the gate TW depends on,
so all 21 TW rows must still pass. Run with the preview hatch on (`localStorage vela_locale_hint_preview = '1'`).
Timezone rows: Chrome DevTools → More tools → Sensors → Location (custom, with timezone). Rows 3 / 9 / 10 go
through **Settings → My Context → Country / region** (no timezone trick needed).

| # | Class | Setup | Expected (gate PASS) |
|---|---|---|---|
| 1 | FIRE | TZ `Asia/Singapore` + EN answer + a **dosing** keyword | **SG** panel; HSA + MOH links resolve (hsa.gov.sg / moh.gov.sg) |
| 2 | FIRE | TZ `Asia/Kuala_Lumpur` + EN answer + a **reimbursement** keyword | **MY** panel; NPRA + MOH links resolve (npra.gov.my / moh.gov.my) |
| 3 | FIRE | Settings locale = **SG** + EN keyword answer | **SG** panel (via L1 settings) |
| 4 | NO-FIRE | EN answer, **no** trigger keyword | no panel |
| 5 | NO-FIRE | isFallback answer (「基於一般醫學知識」) | **suppressed** regardless of country |
| 6 | NO-FIRE | Japanese-UI answer (no `ja` keyword list in b1) | no panel, no error |
| 7 | TRICKY | TZ `America/New_York` + EN + keyword | **Tier-2** panel (WHO/NICE/EMA/Cochrane), **NO country name** in heading |
| 8 | TRICKY | TZ `Asia/Tokyo` + EN + keyword | **Tier-2** (JP has no Tier-1 data in b1), NOT a broken/empty JP panel (RULE 2) |
| 9 | TRICKY | Settings locale = **Other** | **Tier-2** |
| 10 | BEHAVIORAL | Settings locale = **SG** while TZ = `Asia/Taipei` | **SG** panel (proves L1 settings > L3 timezone) |
| 11 | BEHAVIORAL | Per-query dismiss (×) then a new query | dismiss works; **re-shows** on next query (v187 `resetKey`) |
| 12 | BEHAVIORAL | PostHog `locale_hint_displayed` on rows 1 / 3 / 7 | correct `resolution_level` (timezone / settings / timezone) + `resolved_country` + `tier` |
| 13 | REGRESSION | ALL 21 rows of the fly-210 checklist above | still pass — a TW regression fails this gate outright |

**Waterfall (frontend-only, no IP):** L1 Settings locale > L2 work_language (zh-TW→TW · ja→JP · ko→KR · th→TH)
> L3 timezone (Asia/Taipei→TW · Tokyo→JP · Seoul→KR · Singapore→SG · Kuala_Lumpur→MY · Bangkok→TH) > L4 UI-lang
(same 4 as L2). L3 must stay above L4 — SG/MY are English-speaking, so timezone is their ONLY implicit path.
RULE 1: answer language picks the keyword list (fires?); resolved country picks the authorities (what it points to).
RULE 2: a resolved country with no Tier-1 data (JP/KR/TH) → Tier-2, never an empty panel.
