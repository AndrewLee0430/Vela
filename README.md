# 🪸 Vela — Medical Research, Simplified.

> Evidence-based clinical answers from PubMed 36M+ literature and official FDA drug data.  
> Ask in any language — we search in English, answer in yours.

[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4.1-412991?logo=openai)](https://openai.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ Features

### 🔬 Research
Ask any clinical question in any language. Vela retrieves from PubMed 36M+ articles and FDA drug data, then streams a cited, evidence-based answer back in the user's language.

### ✅ Verify
Check drug interaction safety for any combination of medications. Powered by FDA OpenFDA with structured severity ratings (Critical / Major / Moderate / Minor).

### 📋 Explain
Paste lab results, medical reports, or prescription data in any language. Vela identifies each entity, looks it up via LOINC, RxNorm, and MedlinePlus, then generates a plain-language explanation with source badges.

---

## 🏗️ Architecture

Three independent linear pipelines — not a multi-agent system:

```
Research:  User Query → Language Detect → HybridRetriever → Chroma/PubMed/FDA → GPT-4.1 → SSE Stream
Verify:    Drug List  → FDA OpenFDA API → Structured Interaction Data → Response
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

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Auth | Clerk |
| Backend | FastAPI, Python 3.11 |
| AI | OpenAI GPT-4.1 / GPT-4.1-mini |
| RAG | LangChain, Chroma Vector DB |
| Data Sources | PubMed API, FDA OpenFDA, LOINC, RxNorm, MedlinePlus |
| Database | PostgreSQL (history) |
| Streaming | SSE (Server-Sent Events) |

---

## 📁 Project Structure

```
Vela/
├── api/                          # FastAPI backend
│   ├── server.py                 # Main server + all endpoints
│   ├── middleware/
│   │   ├── guards.py             # Prompt injection + intent detection (v2.0)
│   │   └── phi_handler.py        # PHI detection (TW/JP/US)
│   ├── rag/
│   │   ├── generator.py          # Answer generation + language injection (v2.5)
│   │   └── retriever.py          # HybridRetriever — Chroma + PubMed + FDA (v2.3)
│   ├── data_sources/
│   │   ├── fda_client.py
│   │   ├── loinc_client.py
│   │   ├── rxnorm_client.py
│   │   └── medlineplus_client.py
│   ├── services/
│   │   ├── entity_extractor.py   # Lab/drug entity extraction
│   │   └── explain_service.py    # 3-stage Explain pipeline
│   ├── models/
│   │   ├── schemas.py
│   │   └── explain_schemas.py
│   ├── cache/
│   │   └── simple_cache.py       # 3-layer cache (memory → local DB → live API)
│   └── utils/
│       └── language_detector.py  # Unicode CJK + keyword heuristics
├── pages/                        # Next.js pages
│   ├── index.tsx                 # Homepage
│   ├── research.tsx
│   ├── verify.tsx
│   ├── explain.tsx
│   └── history.tsx
├── components/
│   ├── CitationPanel.tsx
│   └── FeedbackBar.tsx
├── scripts/
│   ├── build_drug_vectordb.py
│   └── build_explain_cache.py    # Pre-warm LOINC + RxNorm + MedlinePlus
├── tests/
│   ├── golden_dataset.json       # 17 golden test cases (G01–G17)
│   └── run_golden_tests.py       # --smoke flag for fast daily testing
└── data/                         # gitignored
    ├── drug_database/            # Drug JSON files
    └── drug_vectordb/            # Chroma vector store
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL
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

# Clerk
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_...
CLERK_SECRET_KEY=sk_...
CLERK_JWKS_URL=https://...clerk.accounts.dev/.well-known/jwks.json

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/vela

# CORS
ALLOWED_ORIGINS=http://localhost:3000
```

### 3. Backend

```bash
pip install -r requirements.txt

# Build vector database (first time only)
python scripts/build_drug_vectordb.py

# Pre-warm explain cache (optional, recommended)
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

```bash
# Fast daily smoke test (15 cases, ~80% less cost)
uv run python tests/run_golden_tests.py --smoke

# Full regression (17 cases, run before deploy)
uv run python tests/run_golden_tests.py
```

Test mode (skip Clerk auth):
```bash
$env:TEST_MODE="true"; uvicorn api.server:app --reload   # PowerShell
TEST_MODE=true uvicorn api.server:app --reload            # bash
```

### Golden Dataset Coverage

| Category | Cases | Scope |
|----------|-------|-------|
| Guards | G01–G17 | Injection, non-medical, false positives, multilingual |
| Research | R01, R10, R11 | RAG quality, long-tail queries |
| Verify | V01, V05 | Drug interaction accuracy |
| Multilingual | M01, M02, M04 | ZH/JA/DE response language |
| Explain | E22, E23 | Lab report parsing |

---

## 🔒 Security & Privacy

- **No PHI stored** — inputs are processed in memory only
- **Multi-country PHI detection** — Taiwan ID, Japan My Number, US SSN/MRN
- **Prompt injection protection** — pattern scan + Base64 decode + LLM classification
- **For educational purposes only** — not a substitute for professional clinical judgment

---

## 📄 License

MIT License — see [LICENSE](LICENSE)

---

## 📧 Contact

Andrew Lee · [@AndrewLee0430](https://github.com/AndrewLee0430)  
Project: [https://github.com/AndrewLee0430/Vela](https://github.com/AndrewLee0430/Vela)

---

## 🙏 Acknowledgments

- [OpenAI](https://openai.com) — GPT-4.1
- [PubMed / NLM](https://pubmed.ncbi.nlm.nih.gov) — Medical literature (36M+ articles)
- [FDA OpenFDA](https://open.fda.gov) — Drug label data
- [LOINC®](https://loinc.org) — Lab test terminology (Regenstrief Institute, Inc.)
- [MedlinePlus](https://medlineplus.gov) — Consumer health information (NLM)
- [RxNorm](https://www.nlm.nih.gov/research/umls/rxnorm) — Drug name standardization (NLM)
- [LangChain](https://langchain.com) — RAG framework

> ⚠️ Vela is an educational tool for reference only. It does not replace professional medical judgment. All clinical decisions should be based on comprehensive clinical assessment by a qualified healthcare professional.

---

*Built with ❤️ for healthcare professionals*