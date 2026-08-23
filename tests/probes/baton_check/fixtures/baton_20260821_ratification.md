<!-- FIXTURE — a REAL baton from 2026-08-21, verbatim excerpts, used as the negative
     control for check_baton.py. Its errors are documented and independently verified in
     the TECH_DEBT entry headed "[P1 · gate integrity — the section-aware DANGER-PATH
     criterion had NO ratification record…]" and in the STATE entry for that car.
     DO NOT "fix" the errors below — they are the point. -->

# Vela — RATIFY the danger-path criterion and fix its exit code

A6. TECH_DEBT §2.7 golden gate — THIS IS THE IMPORTANT ONE:
    Report the exact line number of the "Research floor is 18 PASS / 2 WARN / 0 FAIL"
    rule. The baton claims "ratified 2026-08-21, TECH_DEBT.md:784". Confirm or refute
    both halves.

4.3 pytest — expect 316 passed / 28 skipped, UNCHANGED. Use the known workarounds this
    repo requires for collection (tests/test_webhook_cancel.py sys.exit(1) at import).

A4. Verify these line-number claims at HEAD:
    - api/database/vector_store.py:95  — the min_score hard break inside the store
    - api/rag/retriever.py:237         — _cut_exemption
    - api/rag/retriever.py:518-529     — relevance-filter exemption
    - api/server.py:11                 — the logging config line

Push a14d8c7, 39a1b56, b1269e7 to origin/main.

The eval-harness entry is at BACKLOG.md:1844.
