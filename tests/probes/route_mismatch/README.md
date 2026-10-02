# tests/probes/route_mismatch — ROUTE-MISMATCH car (opened 2026-10-02)

Read-only, OFFLINE, zero LLM calls, zero network. Inputs: `data/dailymed/label_docs.json`, `data/tfda/brand_ingredient.json`,
and the saved answers / traces under `tests/probes/bp_calcium/`. Baton: `docs/batons/route_mismatch_car_20261002.md`.

| artifact | what it is | what it does NOT support |
|---|---|---|
| `step1_corpus_route_census.py` → `step1_corpus_route_census.json` | per-label route from a TEXT classifier over D&A text; safety sections by route; moieties whose every safety label is injection-like, with TFDA oral/injection mono-product counts (a KEY) | a key-based route (the corpus has none — see the baton §1); precision beyond the hand-sample |
| `step1_hand_verification.json` | Rule 21 hand-sample (sizes, FPs, misses), 8 targeted classifier errors + overrides, Rule 23 key sets per substance with rejected keys, the 67 → 49 reduction | how COMMONLY a substance is taken orally (TFDA licensing is the proxy); INN-synonym keys (first-token cross-check only) |
| `step2_answer_markers.py` | marker-sentence aid for the hand-read (route words + Calcium Chloride label content) | a grade — it only surfaces sentences |
| `step2_grades.py` → `step2_grades.json` | the HAND grades (A/B/C) for all 149 answers, the per query × arm table, family rates, DailyMed sections in FINAL of A answers | answers not saved (traced runs without an answer file); a clinician's A/B line (domain flag, baton §2) |
| `step3_exempt_door.py` → `step3_exempt_door.json` | per FINAL safety section: LLM-kept vs FilterExempt vs CutExempt, from saved traces | E6 stage attribution (E6 jsons record FINAL only); live behaviour at HEAD |

Re-run order: step1 → step2_grades (needs nothing from step1) → step3 (reads step1 JSONs).
