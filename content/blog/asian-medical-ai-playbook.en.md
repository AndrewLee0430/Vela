---
slug: asian-medical-ai-playbook
locale: en
title: "Why Asian Medical AI Needs a Different Playbook"
summary: "Three structural factors — regulation, language, workflow — that don't translate from US medical AI."
theme: asia
status: published
published_at: 2026-05-25
tags: ["medical-ai", "asia", "positioning"]
cover_image: null
faqs:
  - q: "Why can't US medical AI tools just be translated for Asian markets?"
    a: "Three reasons: drug regulations are country-specific (a US-approved combination may be contraindicated under PMDA, MFDS, or TFDA rules), most clinicians work primarily in their local language rather than English, and clinical workflows differ — a Singapore polyclinic pharmacist and a Tokyo hospital resident have different decision points than a US PCP. Translation alone misses all three."
  - q: "How do drug regulations differ across Asian countries?"
    a: "Each major Asian market maintains its own regulator with its own approved-indication list, dose-adjustment guidance, and contraindication set: Japan (PMDA), South Korea (MFDS), Taiwan (TFDA), Singapore (HSA), Thailand (TFDA-TH). A drug interaction that's labeled 'minor' in the FDA database may carry a stricter warning under one of these regulators, or vice versa. Tools that retrieve only from FDA / DailyMed give an incomplete picture."
  - q: "What does 'multilingual' actually mean for a medical AI tool?"
    a: "Two distinct capabilities: (1) the UI and answer copy render in the user's working language, and (2) the retrieval engine pulls evidence from the global English literature (~40M+ PubMed articles) regardless of the query language. A tool that only ships English UI excludes most non-US clinicians; a tool that only retrieves local-language sources excludes the bulk of published evidence. Both are required."
---

US-built medical AI tools rarely work well in Asian clinical settings — not because the underlying language models are weaker, but because three structural assumptions baked into US tools don't hold across most of Asia: that the user works in English, that FDA-equivalent regulation applies, and that the clinical workflow looks like a US primary-care visit. Tools that don't address all three feel "almost right" to Asian clinicians but miss the decisions they actually need to make.

## Regulation: there is no single regulator

The most-cited US medical databases — FDA, DailyMed, OpenFDA — describe one country's approved indications, dose adjustments, and contraindications. A drug interaction that DailyMed flags as Major may be flagged Critical under PMDA's labeling, or absent entirely from a more recent MFDS bulletin. Clinicians in Singapore, Tokyo, Seoul, and Taipei need their own regulator's current guidance, not an American summary. Vela's Verify pipeline retrieves from the FDA mirror first, then augments with local regulator data when available — and is honest about gaps when local data is sparse.

## Language: most evidence is English, most clinicians aren't

The asymmetry that defines non-US medical practice: ~40M+ peer-reviewed articles indexed on PubMed are mostly English, while the majority of practicing clinicians worldwide work day-to-day in another language. Translating PubMed abstracts on the fly is table stakes; the harder problem is preserving citation fidelity — the source title, journal, year, and DOI must round-trip exactly so the clinician can verify against the original. Vela streams cited answers in the user's language while keeping every citation pointer in its original English form.

## Workflow: a polyclinic pharmacist is not a US PCP

US medical AI is overwhelmingly designed around the primary-care physician's office visit: a 15-minute appointment, a single patient, a differential to narrow. Most Asian clinical work doesn't look like that. A Singapore polyclinic pharmacist verifying a 6-drug prescription, a Tokyo hospital resident reading a 26-line lab panel between rounds, a Taipei community physician answering a parent's question about pediatric dosing — these are different jobs-to-be-done, with different time budgets, different evidence needs, and different "good answer" definitions. Vela's three features (Research, Verify, Explain) map to those three distinct workflows, not to a single PCP flow.

## What this means in practice

A medical AI tool that's serious about Asian markets has to be opinionated about all three: explicitly multilingual (not just translated UI), pluralistic about regulation (not FDA-only), and workflow-aware (not one-size-fits-all). Vela is built around those three constraints — that's the playbook.
