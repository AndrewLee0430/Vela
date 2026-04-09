# 🪸 Vela — Medical Research, Simplified.

> Evidence-based clinical answers from PubMed 36M+ literature and official FDA drug data.  
> Ask in any language — we search in English, answer in yours.

[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4.1-412991?logo=openai)](https://openai.com/)
[![License:Business Source License 1.1]]

🌐 **Live:** [https://vela.an-tho.com](https://vela.an-tho.com)

---

## ✨ Features

### 🔬 Research
Ask any clinical question in 16 languages. Vela retrieves from PubMed 36M+ articles and FDA drug data, then streams a cited, evidence-based answer back in the user's language.

### ✅ Verify
Check drug interaction safety for any combination of medications. Powered by FDA OpenFDA with structured severity ratings (Critical / Major / Moderate / Minor).

### 📋 Explain
Paste lab results, medical reports, or prescription data in any language. Vela identifies each entity, looks it up via LOINC, RxNorm, and MedlinePlus, then generates a plain-language explanation with source badges.

---

## 🏗️ Architecture

Three independent linear pipelines — not a multi-agent system:

```
Research:  User Query → Language Detect → HybridRetriever → NumPy Vector Search / PubMed / FDA → GPT-4.1 → SSE Stream
Verify:    Drug List  → FDA OpenFDA API → Structured Interaction Data → GPT-4.1-mini → Response
Explain:   Lab Report → Entity Extractor → LOINC / RxNorm / MedlinePlus → GPT-4.1 → SSE Stream
```

### Security Layers

| Layer | Protection |
|-------|-----------|
| PHI Detection | Multi-country patterns (TW/JP/US) — ID, phone, SSN, MRN |
| Prompt Injection | Regex pattern scan + Base64 decode + multilingual heuristics |
| Indirect Injection | LLM scan on retrieved content before generation |
| Intent Guard | GPT-4.1-mini classifies non-medical queries and blocks them |
| Input Length | 5,000 character hard limit |
| Auth | Clerk JWT on every API call |
| Rate Limiting | Per-IP per-endpoint throttling |
| Sensitive Files | `.env`, `.git`, `.gitignore` return 404 (blocked in catch-all route) |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Auth | Clerk (Production instance) |
| Backend | FastAPI, Python 3.11 |
| AI | OpenAI GPT-4.1 / GPT-4.1-mini |
| Vector Search | NumPy (in-memory, 690 documents) |
| Data Sources | PubMed API, FDA OpenFDA, LOINC, RxNorm, MedlinePlus |
| Database | PostgreSQL via Neon (history + user usage) |
| Payments | Dodo Payments (Free: 10 credits/day, Pro $9.99/mo) |
| Analytics | PostHog |
| Streaming | SSE (Server-Sent Events) |
| Hosting | Fly.io (Tokyo region) |

---

## 📁 Project Structure

```
Vela/
├── api/                          # FastAPI backend
│   ├── server.py                 # Main server + all endpoints
│   ├── middleware/
│   │   ├── guards.py             # Prompt injection + intent detection
│   │   └── phi_handler.py        # PHI detection (TW/JP/US)
│   ├── rag/
│   │   ├── generator.py          # Answer generation + language injection
│   │   └── retriever.py          # HybridRetriever — NumPy + PubMed + FDA
│   ├── data_sources/
│   │   ├── fda_client.py
│   │   ├── loinc_client.py
│   │   ├── rxnorm_client.py
│   │   └── medlineplus_client.py
│   ├── services/
│   │   ├── usage_service.py      # Credit system (Free: 10/day, Pro: 100/day)
│   │   ├── cost_tracker.py       # API cost monitoring
│   │   ├── entity_extractor.py   # Lab/drug entity extraction
│   │   └── explain_service.py    # 3-stage Explain pipeline
│   ├── models/
│   │   ├── sql_models.py         # UserUsage, ChatHistory, ApiCostLog, WebhookEvent
│   │   ├── schemas.py
│   │   └── explain_schemas.py
│   ├── cache/
│   │   └── simple_cache.py       # 3-layer cache (memory → local DB → live API)
│   └── utils/
│       └── language_detector.py  # Unicode CJK + keyword heuristics
├── pages/                        # Next.js pages
│   ├── index.tsx                 # Landing Page (logged-out) + Dashboard (logged-in)
│   ├── research.tsx
│   ├── verify.tsx
│   ├── explain.tsx
│   ├── history.tsx
│   ├── faq.tsx                   # Public FAQ (15 Q&A, accordion)
│   ├── terms.tsx                 # Terms of Service (incl. Fair Use Policy)
│   ├── privacy.tsx
│   └── refund.tsx
├── components/
│   ├── CitationPanel.tsx
│   ├── FeedbackBar.tsx           # 👍👎 per-response feedback (Research/Verify/Explain)
│   ├── MobileNav.tsx             # Bottom tab bar (mobile)
│   └── UpgradeModal.tsx          # Paywall modal with ToS consent
├── scripts/
│   ├── build_drug_vectordb.py
│   └── build_explain_cache.py    # Pre-warm LOINC + RxNorm + MedlinePlus
├── tests/
│   ├── golden_dataset.json       # 89 test cases (74 active, 15 deprecated)
│   └── run_golden_tests.py       # LLM-as-Judge test runner v3.0
└── data/                         # gitignored
    ├── drug_database/            # Drug JSON files
    └── vector_store/             # NumPy vector store (.npy + metadata)
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL (or Neon cloud)
- OpenAI API key
- Clerk account

### 1. Clone

```bash
git clone https://github.com/AndrewLee0430/Vela.git
cd Vela
```

### 2. Environment Variables

```bash
cp .env.example .env
```

```env
# OpenAI
OPENAI_API_KEY=sk-...

# Clerk (Production)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_...
CLERK_SECRET_KEY=sk_live_...
CLERK_JWKS_URL=https://clerk.vela.an-tho.com/.well-known/jwks.json

# Database (Neon PostgreSQL)
DATABASE_URL=postgresql://user:password@ep-xxx.ap-southeast-1.aws.neon.tech/vela?sslmode=require

# CORS
ALLOWED_ORIGINS=https://vela.an-tho.com

# Lemon Squeezy
LEMON_SQUEEZY_API_KEY=...
LEMON_SQUEEZY_SIGNING_SECRET=...
LEMON_SQUEEZY_STORE_ID=318315

# PostHog Analytics
NEXT_PUBLIC_POSTHOG_KEY=phc_...
NEXT_PUBLIC_POSTHOG_HOST=https://app.posthog.com

# PubMed / FDA
PUBMED_API_KEY=...
FDA_API_KEY=...
NCBI_EMAIL=your@email.com
```

### 3. Backend

```bash
pip install -r requirements.txt

# Pre-warm explain cache (recommended)
python scripts/build_explain_cache.py

# Start server
uvicorn api.server:app --reload
```

### 4. Frontend

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

---

## 🧪 Testing

### Prerequisites

Ensure your `.env` has `DATABASE_URL` and `OPENAI_API_KEY` set.

### Running Tests (Windows PowerShell)

**Step 1 — Start backend in TEST_MODE** (skips Clerk JWT + rate limiting, auto-resets test_user credits):

```powershell
$env:TEST_MODE="true"; $env:PYTHONIOENCODING="utf-8"; uvicorn api.server:app --port 8000
```

**Step 2 — In a new terminal, run tests:**

```powershell
# Smoke test — fast, ~20 cases, daily use
$env:PYTHONIOENCODING="utf-8"; $env:TEST_MODE="true"; uv run python tests/run_golden_tests.py --smoke

# Full regression — 74 active cases, run before every deploy
$env:PYTHONIOENCODING="utf-8"; $env:TEST_MODE="true"; uv run python tests/run_golden_tests.py
```

**bash / Linux / macOS:**

```bash
# Start backend
TEST_MODE=true PYTHONIOENCODING=utf-8 uvicorn api.server:app --port 8000

# Smoke test
PYTHONIOENCODING=utf-8 TEST_MODE=true uv run python tests/run_golden_tests.py --smoke

# Full regression
PYTHONIOENCODING=utf-8 TEST_MODE=true uv run python tests/run_golden_tests.py
```

### Common Issues & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `403` on all requests after a few tests | `test_user` hit free credit limit | TEST_MODE now auto-resets credits on start |
| `429` rate limit errors | Rate limiter firing in test mode | TEST_MODE now bypasses rate limiting |
| `Python-dotenv could not parse...` | Windows `.env` encoding issue | Safe to ignore — dotenv warning only, not an error |
| `Exit code 127: fly: command not found` | Fly CLI not in PATH | Use full path: `& "C:\Users\<you>\.fly\bin\fly.exe" deploy` |
| `PYTHONIOENCODING` emoji errors | Windows CP950 terminal encoding | Always set `PYTHONIOENCODING=utf-8` |

### Test Coverage

| Category | Active Cases | Scope |
|----------|-------------|-------|
| Research | 20 | English/Chinese/mixed clinical queries, edge cases |
| Verify | 15 | Drug interaction accuracy, severity ratings |
| Explain | 22 | Lab reports, multilingual (JA/KO/ES/FR/DE/IT/PT), edge cases |
| Guard | 17 | Injection attacks, non-medical queries, false positive check |
| Multilingual | 7 | JA/TH/KO/ES/ZH response language verification |
| ~~Document~~ | ~~15~~ | Deprecated endpoint — auto-skipped |

Pass threshold: **≥ 70%** overall. Exit code `1` if below threshold.

Results saved to `tests/results/golden_results_YYYYMMDD_HHMMSS.json` + HTML report.

---

## 🚢 Deployment

### Deploy to Fly.io

```powershell
# Windows
& "C:\Users\<you>\.fly\bin\fly.exe" deploy

# bash
fly deploy
```

### Environment Variables on Fly.io

`NEXT_PUBLIC_*` variables must go in `fly.toml` `[build.args]` (build-time):

```toml
[build.args]
  NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY = "pk_live_..."
  NEXT_PUBLIC_POSTHOG_KEY = "phc_..."
  NEXT_PUBLIC_POSTHOG_HOST = "https://app.posthog.com"
  NEXT_PUBLIC_API_URL = "https://vela.an-tho.com"
```

All other secrets via `fly secrets set`:

```bash
fly secrets set \
  DATABASE_URL="postgresql://..." \
  OPENAI_API_KEY="sk-..." \
  CLERK_SECRET_KEY="sk_live_..." \
  CLERK_JWKS_URL="https://clerk.vela.an-tho.com/.well-known/jwks.json" \
  ALLOWED_ORIGINS="https://vela.an-tho.com" \
  LEMON_SQUEEZY_API_KEY="..." \
  LEMON_SQUEEZY_SIGNING_SECRET="..." \
  LEMON_SQUEEZY_STORE_ID="318315"
```

### Recommended Deploy Flow

```
1. Make changes locally
2. npm run build  (verify no build errors)
3. Run smoke test (optional but recommended)
4. git add . && git commit -m "..." && git push origin main
5. fly deploy
6. Verify: curl https://vela.an-tho.com/health
```

---

## 💰 Pricing Model

| Plan | Price | Credits | Usage |
|------|-------|---------|-------|
| Free | $0 | 10 credits/day | Research (3 credits), Explain (2), Verify (1) |
| Pro | $9.99/mo or $89.99/yr (save 25%) | 100 credits/day | All features |

*Subject to fair use policy. Daily limit of 100 credits applies to prevent automated abuse. Credit costs: Research (3), Verify (1), Explain (2). See [Terms of Service](https://vela.an-tho.com/terms).

---

## 🔒 Security & Privacy

- **No PHI stored** — inputs are processed in memory only
- **Multi-country PHI detection** — Taiwan ID, Japan My Number, US SSN/MRN
- **Prompt injection protection** — pattern scan + Base64 decode + LLM classification
- **Sensitive file blocking** — `.env`, `.git`, `.gitignore` blocked at server level
- **For reference only** — not a substitute for professional clinical judgment

---

## 📄 License

MIT License — see [LICENSE](LICENSE)

---

## 📧 Contact

Andrew Lee · [@AndrewLee0430](https://github.com/AndrewLee0430)  
Support: support@an-tho.com  
Project: [https://github.com/AndrewLee0430/Vela](https://github.com/AndrewLee0430/Vela)

---

## 🙏 Acknowledgments

- [OpenAI](https://openai.com) — GPT-4.1
- [PubMed / NLM](https://pubmed.ncbi.nlm.nih.gov) — Medical literature (36M+ articles)
- [FDA OpenFDA](https://open.fda.gov) — Drug label data
- [LOINC®](https://loinc.org) — Lab test terminology (Regenstrief Institute, Inc.)
- [MedlinePlus](https://medlineplus.gov) — Consumer health information (NLM)
- [RxNorm](https://www.nlm.nih.gov/research/umls/rxnorm) — Drug name standardization (NLM)
- [Clerk](https://clerk.com) — Authentication
- [Neon](https://neon.tech) — Serverless PostgreSQL
- [Fly.io](https://fly.io) — Hosting (Tokyo region)
- [Dodo Payments](https://dodopayments.com) — Payments & subscriptions
- [PostHog](https://posthog.com) — Product analytics

> ⚠️ Vela is a clinical decision support tool for reference only. It does not replace professional medical judgment. All clinical decisions should be based on comprehensive clinical assessment by a qualified healthcare professional.

---

*Built with ❤️ for healthcare professionals*