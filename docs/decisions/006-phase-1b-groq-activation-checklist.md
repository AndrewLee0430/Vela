# ADR 006: Phase 1B Groq Activation Checklist

**Date**: 2026-05-13 (drafted at §2.1 PHASE E completion)
**Status**: Drafted — execution deferred to Phase 1B
**References**: ADR 005, PRD §2.1 v1.4

## Context

§2.1 PHASE A-E shipped the Provider abstraction with OpenAIProvider + GroqProvider. Phase 0 ship state: 100% OpenAI defaults; Groq framework-ready but not activated.

Phase 1B will evaluate switching select tasks to Groq for cost + speed gains. This ADR documents the exact procedure so the switch is mechanical.

## Phase 1B activation order (cost reduction × risk priority)

### Step 1: GROQ_API_KEY infrastructure
- Obtain Groq API key from console.groq.com
- Add to Fly.io secrets: `fly secrets set GROQ_API_KEY=gsk_...`
- Add to local .env: `GROQ_API_KEY=gsk_...`
- Do NOT commit the actual key (.env is gitignored)

### Step 2: cost_tracker.py extension (BLOCKER)
**Required before any *_PROVIDER=groq flip.** Per PRD §2.1 v1.4 需求 5 note.

api/services/cost_tracker.py L13-16 currently hardcodes OpenAI model prices. Add Groq model entries:

```python
# Add to MODEL_COSTS dict in cost_tracker.py
"llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},  # per 1M tokens
"openai/gpt-oss-120b": {"input": 0.15, "output": 0.75},
"openai/gpt-oss-20b": {"input": 0.10, "output": 0.50},
"llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
"qwen/qwen3-32b": {"input": 0.29, "output": 0.59},
```

Verify: `python -c "from api.services.cost_tracker import MODEL_COSTS; assert 'llama-3.1-8b-instant' in MODEL_COSTS"`

### Step 3: First switch — Reranker (lowest risk)

Reranker is an internal scoring task. Output is structured JSON consumed by retriever, never user-visible.

```
fly secrets set RERANKER_PROVIDER=groq RERANKER_MODEL=llama-3.1-8b-instant
fly deploy
```

Smoke test:
- Live Research query → citations still ranked sensibly
- PostHog: rerank_latency_ms should DROP (Groq LPU faster)
- cost_tracker logs: rerank entries show llama-3.1-8b-instant

**Rollback**: `fly secrets unset RERANKER_PROVIDER RERANKER_MODEL && fly deploy`.

Run 3-5 days. Compare PostHog metrics:
- Research conversion / completion rate (should be unchanged)
- User-reported quality issues (should be 0)
- Cost per Research query (should DROP)

### Step 4: Second switch — Guard

Guard tasks (indirect injection + medical intent) are classification — yes/no outputs.

```
fly secrets set GUARD_PROVIDER=groq GUARD_MODEL=llama-3.1-8b-instant
fly deploy
```

Smoke test:
- Known-good medical query → not blocked
- Known-malicious prompt injection → blocked
- Guard latency in PostHog

Run 3-5 days.

### Step 5: Third switch — Lightweight (Retriever + Entity Extractor)

These tasks: query rewrite, translation, relevance filter, entity extraction. Higher risk because output feeds downstream answer.

```
fly secrets set LIGHTWEIGHT_PROVIDER=groq LIGHTWEIGHT_MODEL=llama-3.1-8b-instant
fly deploy
```

Smoke test:
- Multilingual queries (zh-TW → English translation must work)
- Entity extraction on medical text (drug names, lab values)
- Answer quality unchanged

**Quality bar**: If any user-facing answer regression appears, rollback immediately.

### Step 6: Anonymous L0 Trial — GPT-OSS 120B test

Anon path uses GENERATOR_FALLBACK_MODEL per PHASE D refactor. To upgrade anon experience:

Option A: change GENERATOR_FALLBACK_MODEL only (affects both anon AND Research fallback path):
```
fly secrets set GENERATOR_PROVIDER=groq GENERATOR_FALLBACK_MODEL=openai/gpt-oss-120b
```
**Risky** — touches Research primary path.

Option B: introduce dedicated ANON_PROVIDER / ANON_MODEL env vars (new task layer, requires PHASE A-like work).

Defer Option B to a future ADR if anon-specific tuning becomes valuable.

### Step 7: NEVER switch (Phase 1B)

Stay OpenAI for Phase 1B (and likely Phase 2):

- **GENERATOR_PROVIDER** (Main Research RAG) — §2.7 acceptance baseline
- **EXPLAIN_JUDGE_PROVIDER** — §2.7 Step 7 baseline is gpt-4.1
- **VISION_PROVIDER** — Groq Llama 4 Scout vision not yet dogfooded
- **EMBEDDER_PROVIDER** — Groq has no embedding model; switching would require vector store rebuild

## Decision

This ADR records the recommended Phase 1B procedure. Execution is gated on:
- Phase 1A complete with PostHog cost baseline data
- cost_tracker.py extension done
- Rollback plan validated in staging (if Vela has staging by then)

## Reference
- PRD §2.1 v1.4 (Provider abstraction spec)
- ADR 005 (Anthropic → Groq decision)
- Groq pricing: https://groq.com/pricing
- Groq model deprecation history: 6 models deprecated in 6 months (2025-2026)
