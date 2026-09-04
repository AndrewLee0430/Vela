# research_error_path — HISTORY HONESTY car segment 2, §4 gate rows 1–4 (machine facts)

- **What:** `probe.py` boots a LOCAL backend on **:8010** (TEST_MODE, the dev DB from `.env`), runs a grounded query, a no-literature query, then restarts with `GENERATOR_MODEL` **and** `GENERATOR_FALLBACK_MODEL` = `gpt-does-not-exist` and runs an authed + an anonymous query; it reads `user_usage` / `anonymous_usage` / `chat_history` before and after each step and copies the `[Research] generator ERROR before DONE …` log lines into `result.json`.
- **Rerun (repo root):** `PYTHONUTF8=1 python tests/probes/research_error_path/probe.py` — needs `.env` (`DATABASE_URL`, `OPENAI_API_KEY`, `TEST_MODE=true`) and port 8010 free; exit 0 = every check ok, 1 = see `summary.checks_failed`.
- **Evidence:** `result.json` is the committed reading (Rule 20) — every value carries the query text, row ids and UTC timestamps; live LLM/retrieval calls make each run a NEW snapshot, not a reproduction of this one. Server logs land in `tests/results/` (gitignored).
- **Why both model env vars:** the anonymous path runs on `generator._fallback_model` (`api/server.py`, `model_override`), so a bad `GENERATOR_MODEL` alone would let row 4 succeed on gpt-4.1-mini instead of erroring.
- **Not covered here:** the VISUAL §4 rows (banner, unchanged render, console) — founder-only; this probe never fills a PASS/FAIL cell.
