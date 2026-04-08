# Vela — Business Overview

## Product

**Vela is a multilingual clinical AI research tool for healthcare professionals**, delivering evidence-based answers grounded in PubMed 36M+ articles and official FDA drug data.

Three core features:
- **Research** — Ask clinical questions in any language, get cited answers with evidence strength ratings (🟢 Strong / 🟡 Moderate / 🔴 Limited)
- **Verify** — Check drug interactions against official FDA label data with severity badges (Critical / Major / Moderate / Minor)
- **Explain** — Upload medical reports (PDF/image) or paste text, get plain-language summaries backed by LOINC, RxNorm, and MedlinePlus

---

## Problem

1. **Non-English clinicians lack efficient literature tools.** PubMed is English-only; querying it requires medical English proficiency and keyword expertise. Most clinicians outside English-speaking countries rely on Google Translate + manual search.

2. **UpToDate is expensive and English-only.** At ~$60/month, it's unaffordable for residents and clinicians in developing markets. No multilingual support.

3. **Google Scholar isn't designed for clinical questions.** No structured answers, no drug interaction checks, no evidence grading. Clinicians need answers, not a list of papers.

4. **ChatGPT/GPT wrappers hallucinate without citations.** General-purpose LLMs cannot be trusted for clinical decisions without verifiable source attribution.

---

## Solution

- **PubMed 36M+ articles + FDA official drug labels** as retrieval sources (not just LLM knowledge)
- **16 language support** — English, Traditional Chinese, Simplified Chinese, Japanese, Korean, Spanish, French, German, Italian, Portuguese, Thai, Arabic, Hindi, Bengali, Hebrew, Vietnamese
- **Every answer includes citations** with clickable source links (PubMed PMID, FDA DailyMed)
- **Evidence strength assessment** per section, judged by the LLM against retrieval quality
- **5-layer safety guard chain** — input validation, injection detection, medical intent classification, PHI detection

---

## Target Market

**Primary:** Non-English-speaking healthcare professionals
- Physicians, nurses, and residents in Taiwan, Japan, South Korea, Latin America, and Europe
- Estimated 5M+ clinicians in target regions who regularly search medical literature

**Secondary:** Medical students and researchers worldwide

**TAM/SAM/SOM (rough estimates):**

| Segment | Size | Basis |
|---|---|---|
| TAM | ~15M clinicians globally who search literature regularly | WHO workforce data |
| SAM | ~5M non-English clinicians in target language regions | Focus on 16 supported languages |
| SOM (Year 1) | ~5,000 active users | Organic + Product Hunt + community |

---

## Business Model

### Pricing
| Plan | Price | Credits | Features |
|---|---|---|---|
| Free | $0 | 10/day | Core features, 7-day history, text-only Explain |
| Pro (Monthly) | $9.99/mo | 100/day | Full history + search, PDF/image upload, Export PDF |
| Pro (Annual) | $89.99/yr | 100/day | Same as monthly, 25% discount |

### Unit Economics

| Feature | Credits | Estimated Cost | Margin at $9.99/mo |
|---|---|---|---|
| Research | 3 | ~$0.015/query | ~97% gross margin at 100 queries/day |
| Verify | 1 | ~$0.002/query | ~99% |
| Explain | 2 | ~$0.014/query | ~97% |

**Worst-case Pro user** (maxing out 100 credits/day for 30 days):
- ~$15-45/month in API costs depending on query mix
- Break-even at ~33 Research queries/day

**Target conversion rate:** Free → Pro > 5% (industry SaaS benchmark: 2-5%)

### Payment Processing
- Dodo Payments (Merchant of Record)
- Standard Webhooks for subscription lifecycle
- No self-hosted billing complexity

---

## Competitive Advantage

| Dimension | Vela | UpToDate | ChatGPT/Perplexity | Google Scholar |
|---|---|---|---|---|
| Multilingual | 16 languages | English only | Any (no medical focus) | English-centric |
| Sources | PubMed + FDA (cited) | Curated editorial | No citations / hallucination risk | Raw papers |
| Evidence grading | 🟢🟡🔴 per section | Editorial assessment | None | None |
| Drug interactions | FDA-backed severity | Included | Unreliable | Not available |
| Price | $9.99/mo | ~$60/mo | $20/mo | Free (no answers) |
| Clinical focus | Medical-only (guard chain) | Medical-only | General-purpose | General-purpose |

**Key moats:**
1. **Language + medical specialization** — hard to replicate without dedicated language detection + medical prompt engineering
2. **Official source attribution** — PubMed + FDA retrieval pipeline, not just LLM generation
3. **Safety by design** — 5-layer guard chain, PHI detection, fail-close architecture
4. **Price/value** — 6x cheaper than UpToDate with comparable clinical utility for common queries

---

## Tech Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 15 (Pages Router, static export) |
| Backend | FastAPI + uvicorn (Python async) |
| AI | OpenAI GPT-4.1 + GPT-4.1-mini |
| Auth | Clerk (JWT + JWKS) |
| Database | Neon PostgreSQL + SQLAlchemy |
| Payments | Dodo Payments (Standard Webhooks) |
| Hosting | Fly.io (2 machines, Tokyo region) |
| Monitoring | Sentry + PostHog |
| Streaming | SSE (fetch-event-source + sse-starlette) |

See `docs/architecture.mermaid` for full architecture diagram.

---

## Traction

> _To be updated with actual metrics._

| Metric | Current | Target (6 months) |
|---|---|---|
| Registered users | — | — |
| Monthly active users | — | — |
| Pro subscribers | — | — |
| MRR | — | — |
| Free → Pro conversion | — | > 5% |
| Avg queries/user/day | — | — |
| NPS | — | — |

---

## Roadmap

### Near-term (Q2 2026)
- Product Hunt launch
- GTM: Medical community outreach (Taiwan, Japan, Korea)
- SEO content (clinical question landing pages)
- User feedback loop (already collecting via FeedbackBar)

### Mid-term (Q3-Q4 2026)
- Follow-up questions (conversational research)
- Advanced filters (year range, study type, journal)
- Export format expansion (Word, BibTeX)
- Guideline integration (WHO, AHA, ESC)
- Mobile-optimized experience improvements

### Long-term (2027+)
- Team plan (shared history, admin dashboard)
- API access for institutional integration
- Additional data sources (Cochrane, ClinicalTrials.gov, regional pharmacopeias)
- On-premise deployment option for hospitals
- EHR integration (FHIR-compatible)
