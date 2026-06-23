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
