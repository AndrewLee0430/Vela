# Vela — Business Overview

## Product

**Vela is a multilingual clinical AI research tool for healthcare professionals**, delivering evidence-based answers grounded in PubMed 36M+ articles and official FDA drug data.

Three core features:
- **Research** — Ask clinical questions in any language, get cited answers; each section header carries an LLM-emitted 🟢/🟡/🔴 evidence-strength marker (self-label), shown with a source-provenance line (the standalone evidence-legend UI was retired in v176)
- **Verify** — Check drug interactions against official FDA label data with severity badges (Critical / Major / Moderate / Minor)
- **Explain** — Upload medical reports (PDF/image) or paste text, get plain-language summaries backed by LOINC (tooltip popover on hover), RxNorm (clickable links to DailyMed), and MedlinePlus
- **FAQ** — Public FAQ page (`/faq`) with 15 Q&A items in accordion format

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
- **Every answer includes citations** with clickable source links (PubMed PMID, FDA DailyMed) <!-- ⚠️ 2026-06-25: if reused as external marketing copy, change "FDA DailyMed" → "FDA drug labels (OpenFDA)" — internal doc only, not a live over-claim today (see TECH_DEBT DailyMed sweep). -->
- **Evidence strength** — a per-section 🟢🟡🔴 marker the LLM self-assigns (parsed into a colored section header), shown alongside a real source-provenance line. (The earlier standalone evidence-legend / credibility-badge UI was replaced by the provenance line in v176; the `evidenceStrong/Moderate/Limited` i18n keys were removed 2026-06-25.)
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

**Landing page**: Three product mockup cards (Research/Verify/Explain) with unified structure — query + badge + source label + CTA. "Every answer cited" social proof tagline. Footer: "© 2026 Vela. All rights reserved. · an-tho.com" (an-tho.com is the parent brand page, now live).

| Dimension | Vela | OpenEvidence | UpToDate | ChatGPT/Perplexity | Google Scholar |
|---|---|---|---|---|---|
| Multilingual | 16 languages | EN + Japanese (added 2026); withdrew EU/UK | English only | Any (no medical focus) | English-centric |
| Sources | PubMed + FDA, cited; **TFDA 仿單 local grounding planned (ADR 007)** | US-centric guideline + literature | Curated editorial | No citations / hallucination risk | Raw papers |
| Evidence grading | per-section 🟢🟡🔴 self-label (LLM-emitted, in the section header) + source-provenance line | Literature-based | Editorial assessment | None | None |
| Drug interactions | FDA-label severity (cited) | US-centric | Included | Unreliable | Not available |
| Access / Price | $9.99/mo · no credential gate · anonymous-friendly | **Free but NPI-gated — verified US physicians ONLY (blocks non-US incl. Taiwan); ad-monetized** | ~$60/mo | $20/mo | Free (no answers) |
| Clinical focus | Medical-only (guard chain); non-English + Allied-Health TA | Medical (US physicians) | Medical-only | General-purpose | General-purpose |

**Key moats (headline = deep local grounding, NOT price):**
1. **Deep local grounding — the headline differentiator** — answer with Taiwan standards + citations (TFDA 仿單 ingested as a citable RAG source; planned per ADR 007), serving the non-physician **Allied-Health TA** (pharmacists, nurses, students) that OpenEvidence does not prioritize. This is the moat OpenEvidence's **NPI-gated, US-centric** model structurally cannot replicate (it blocks non-US users, incl. Taiwan).
2. **Language + medical specialization** — 16-language medical search; dedicated language detection + medical prompt engineering.
3. **Official source attribution** — PubMed + FDA retrieval pipeline (cited), not just LLM generation.
4. **Safety by design** — 5-layer guard chain, PHI detection, fail-close, no-credential-gate / anonymous-friendly access.
5. **Price (secondary value point, NOT the moat)** — $9.99/mo vs UpToDate ~$60/mo; a value point, demoted below the local-grounding moat.

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
