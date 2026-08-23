# Answer-layer wrong-drug review pack — FOUNDER FILLS THIS IN

**Generated** 2026-08-23 17:03:48 · **24 units** · N=1 per case · in-process, **no server, NO LLM JUDGE**.
**Config:** `max_results=5` · `source_weight_active=True` · `_annotate_research_question` applied · bare HybridRetriever() — matches production post-c1.

Column set follows [`docs/human_eye_gate_checklist.md`](../../../docs/human_eye_gate_checklist.md) — the form already used for the fly-215 and fly-206 gates. **VERDICT vocabulary is that file's:** `PASS` · `FAIL` · `n/a` · `UNSCORED` (pair queries) · `BLOCKED`. Leave nothing blank at the end — `—` means *checked, nothing to report*; an **empty cell means not checked**.

---

## 🔴 READ THIS BEFORE SCORING — what the MECHANICAL flag is and is not

Each DailyMed citation carries a flag comparing its **moiety** against the **question text** (exact whole-token, plus the salt-base form). It exists **only to order your reading**.

| flag | means | does NOT mean |
|---|---|---|
| `MATCH` | the cited drug's name appears in the question | **NOT evidence the citation is correct.** A question can name drug X and still be answered from the wrong section, or from X's label where another drug's was needed |
| `NO-MATCH` | the cited drug's name does not appear in the question | **NOT evidence of an error.** A class question (*"NSAIDs"*, *"statins"*) legitimately cites specific member drugs; a pair question is legitimately answered from a counterpart's label |
| `NO-DRUG-IN-QUESTION` | no corpus drug name resolves from the question at all | the wrong-object axis does not apply — per the gate form, write `n/a — class query` |

**Ownership itself is resolved ONLY by the corpus join** `source_id → setid → moiety` (`owner_assertion.py`, Constraint 1). The flag above is question-side text matching used for sort order and nothing else. **It never decides ownership, and it is not a verdict.**

**From the gate form, carried over verbatim:**
- **EXPECTED OWNER is PLURAL BY CONSTRUCTION** — one substance can occupy two corpus keys with different labels and different safety coverage (`ASPIRIN` → VAZALORE, **no** safety sections; `ACETYLSALICYLIC ACID` → DURLAZA, three). A single-key expectation reproduces the bug the field exists to catch.
- **Class queries:** write `n/a — class query`, never a guess. A class member cited on a class query is **legitimately owned**; if unhelpful, that is *answer-relevance*, a different axis.
- **Pair / interaction queries:** mark `pair query — not scored for wrong-object (v1)`. Record what was cited; do not score it.
- **Check the citation TITLE, not the chip** — the chip reads "DailyMed", which is always true.
- ⚠️ **Do not derive keys by substring** — a `STATIN` search returns **NYSTATIN**, an antifungal.

**Sort order is MECHANICAL:** units with the most `NO-MATCH` DailyMed citations first, then most DailyMed citations. That is a reading-order heuristic, **not a suspicion ranking you should trust**.

### 🔴 KNOWN BLIND SPOTS IN THE FLAG — disclosed, not silently carried

The flag uses `resolver.resolve_key_set`, whose limits are measured and recorded. **Two of them affect units in this pack, so check these by eye rather than trusting the flag:**

1. **A question can name a drug the resolver cannot see, and the flag will say `NO-DRUG-IN-QUESTION` anyway.** Concrete case in this pack: **`R09`** asks about *lithium therapy*, and both its citations are `LITHIUM CARBONATE` — which is almost certainly the right label. But the corpus key is `LITHIUM CARBONATE` and `CARBONATE` is **not** in the 17-suffix salt list, so base→salt expansion cannot bridge *lithium* → `LITHIUM CARBONATE`. **The flag is wrong on R09 in the conservative direction** — it under-claims, it does not over-claim.
2. **`exact` and `base` matching are mutually exclusive** (`resolver.py:102-108` returns before `:110`), so on a two-drug question where one drug matches exactly, the other is dropped from the key set entirely. Any pair question in this pack inherits that.

Neither blind spot can create a **false `NO-MATCH`** — they only produce false `NO-DRUG-IN-QUESTION`. So the sort can bury a unit; it cannot invent a suspicious one.

---

## Summary table — fill VERDICT and NOTES

| # | id | question | DailyMed cites | NO-MATCH | EXPECTED OWNER (all corpus keys — you fill) | VERDICT | NOTES |
|---|---|---|---|---|---|---|---|
| 1 | `R07` | `What are the contraindications for using beta-blockers?` | 4 | **0** | | | |
| 2 | `R11` | `metformin 腎臟不好的病人可以用嗎` | 4 | **0** | | | |
| 3 | `R16` | `Which NSAIDs are safest for elderly patients with cardiovascular disease?` | 4 | **0** | | | |
| 4 | `R12` | `is it ok to give both blood thinners at the same time` | 3 | **0** | | | |
| 5 | `R01` | `What are the side effects of Metformin in patients with renal impairment?` | 2 | **0** | | | |
| 6 | `R09` | `What monitoring is required for patients on lithium therapy?` | 2 | **0** | | | |
| 7 | `R10` | `What are the clinical features of digoxin toxicity?` | 1 | **0** | | | |
| 8 | `R18` | `我的病人在用 statin，最近說肌肉痛，我該怎麼辦` | 1 | **0** | | | |
| 9 | `R20` | `Can I use ACE inhibitors during pregnancy?` | 1 | **0** | | | |
| 10 | `MF01` | `calcium channel blocker mechanism` | 0 | **0** | | | |
| 11 | `MF02` | `atorvastatin calcium side effects` | 0 | **0** | | | |
| 12 | `MF03` | `low sodium diet and blood pressure` | 0 | **0** | | | |
| 13 | `MF04` | `potassium supplements in CKD` | 0 | **0** | | | |
| 14 | `R02` | `What is the first-line treatment for hypertension in diabetic patients?` | 0 | **0** | | | |
| 15 | `R03` | `What are the indications for prophylactic anticoagulation in atrial fibrillation?` | 0 | **0** | | | |
| 16 | `R04` | `What is the mechanism of action of statins?` | 0 | **0** | | | |
| 17 | `R05` | `What are the signs of serotonin syndrome?` | 0 | **0** | | | |
| 18 | `R06` | `How should heparin-induced thrombocytopenia (HIT) be managed?` | 0 | **0** | | | |
| 19 | `R08` | `What is the recommended dose of aspirin for cardiovascular prevention?` | 0 | **0** | | | |
| 20 | `R13` | `warfarin 和 aspirin 一起用 safe 嗎` | 0 | **0** | | | |
| 21 | `R14` | `When can beta blockers actually be used in heart failure? I thought they were contraindicated.` | 0 | **0** | | | |
| 22 | `R15` | `What is the difference between Type 1 and Type 2 heparin-induced thrombocytopenia?` | 0 | **0** | | | |
| 23 | `R17` | `How long should dual antiplatelet therapy be continued after coronary stent placement?` | 0 | **0** | | | |
| 24 | `R19` | `What are the renal dosing adjustments required for common antibiotics?` | 0 | **0** | | | |

---

## The units

### 1. `R07` — 0 NO-MATCH of 4 DailyMed citations

**Question as asked:**

> What are the contraindications for using beta-blockers?

`status=ok` · `23.2s` · resolver keys: **none — no corpus drug resolves from this question**

**Citations as returned:**

| # | source | source_id | title | MOIETY (corpus join) | MECHANICAL flag |
|---|---|---|---|---|---|
| 1 | `dailymed` | `DailyMed:0283bc9d-6998-493a-824a-d4c85f704111#43685-7` | Lopressor (metoprolol tartrate) — Warnings and Precautions | `METOPROLOL TARTRATE` | `NO-DRUG-IN-QUESTION` |
| 2 | `dailymed` | `DailyMed:595cc3d5-1306-4828-aefa-5595219ffd62#43685-7` | Brevibloc (Esmolol Hydrochloride) — Warnings and Precautions | `ESMOLOL HYDROCHLORIDE` | `NO-DRUG-IN-QUESTION` |
| 3 | `dailymed` | `DailyMed:8b8ad213-1dc8-454e-a524-075685c0e1a8#43685-7` | Bystolic (nebivolol hydrochloride) — Warnings and Precautions | `NEBIVOLOL` | `NO-DRUG-IN-QUESTION` |
| 4 | `dailymed` | `DailyMed:746db603-a6e1-4dc3-c2d8-92314419098c#34073-7` | TENORMIN (Atenolol) — Drug Interactions | `ATENOLOL` | `NO-DRUG-IN-QUESTION` |

**Answer as generated:**

> ## Summary
>
> Beta-blockers are contraindicated in patients with bronchospastic disease, certain cardiac conduction disorders, untreated pheochromocytoma, and in situations where severe bradycardia or hypotension is present. These contraindications are due to the risk of exacerbating underlying conditions or precipitating life-threatening events through beta-blockade mechanisms that affect cardiac, respiratory, and metabolic systems[1][2][3][4].
>
> ---
>
> ## Clinical Notes
>
> - **Bronchospastic Disease:** Beta-blockers should generally not be used in patients with bronchospastic diseases (e.g., asthma, severe COPD) due to the risk of exacerbating bronchospasm[1][3].
> - **Cardiac Contraindications:**
>   - **Severe Bradycardia:** Beta-blockers can worsen bradycardia and are contraindicated in patients with marked bradycardia[2][4].
>   - **Heart Block/Conduction Disorders:** Patients with significant conduction disorders (e.g., second- or third-degree AV block, sinus node dysfunction) are at increased risk of severe bradycardia or asystole and should not receive beta-blockers unless a functioning pacemaker is present[2][4].
>   - **Acute Cardiac Failure/Cardiogenic Shock:** Beta-blockers can depress myocardial contractility and may precipitate or worsen heart failure or cardiogenic shock; they are contraindicated in these settings[1][2].
> - **Untreated Pheochromocytoma:** Beta-blockers are contraindicated unless alpha-blockade has been established, as unopposed alpha-adrenergic stimulation can cause severe hypertension[1][2].
> - **Severe Hypotension:** Beta-blockers can further lower blood pressure and are contraindicated in patients with significant hypotension[2].
> - **Drug Interactions:** Concomitant use with certain drugs (e.g., catecholamine depleting agents, disopyramide, amiodarone, some calcium channel blockers) can increase the risk of severe bradycardia, hypotension, or heart failure and may be contraindicated depending on the clinical scenario[4].
> - **Other Considerations:** Beta-blockers may mask symptoms of hypoglycemia in diabetic patients and should be used with caution, but this is not a strict contraindication[1][2][3].
>
> **Monitoring Parameters:**
> - Monitor heart rate and rhythm continuously in patients at risk for conduction disorders or bradycardia.
> - Monitor blood pressure closely, especially in patients with low baseline blood pressure or those on interacting medications.
> - In patients with heart failure, monitor for signs of worsening heart failure during dose titration.
> - Screen for pheochromocytoma before initiating beta-blockers in patients with suggestive symptoms.
>
> If the context above does not address a specific patient population or comorbidity, further information would be needed to provide a comprehensive list of contraindications.

| EXPECTED OWNER (all corpus keys) | OBSERVED OWNER(S) | VERDICT | NOTES |
|---|---|---|---|
| | | | |

---

### 2. `R11` — 0 NO-MATCH of 4 DailyMed citations

**Question as asked:**

> metformin 腎臟不好的病人可以用嗎

`status=ok` · `26.7s` · resolver keys: `METFORMIN`, `METFORMIN HCL`

**Citations as returned:**

| # | source | source_id | title | MOIETY (corpus join) | MECHANICAL flag |
|---|---|---|---|---|---|
| 1 | `dailymed` | `DailyMed:1f8833f9-1232-4aa7-a0d4-04a9f87dc2f0#34070-3` | Metformin HCl (Metformin HCl) — Contraindications | `METFORMIN HCL` | `MATCH` |
| 2 | `dailymed` | `DailyMed:fb832474-88d9-4e29-95cd-fbc446944cc4#34070-3` | Glumetza (metformin hydrochloride) — Contraindications | `METFORMIN` | `MATCH` |
| 3 | `dailymed` | `DailyMed:fb832474-88d9-4e29-95cd-fbc446944cc4#43685-7` | Glumetza (metformin hydrochloride) — Warnings and Precautions | `METFORMIN` | `MATCH` |
| 4 | `dailymed` | `DailyMed:1f8833f9-1232-4aa7-a0d4-04a9f87dc2f0#34073-7` | Metformin HCl (Metformin HCl) — Drug Interactions | `METFORMIN HCL` | `MATCH` |
| 5 | `pubmed` | `PMID:31187887` | Metformin: time to review its role and safety in chronic kidney disease. | — | — |

**Answer as generated:**

> ## 摘要
> 腎臟功能不全的病人是否可以使用 metformin 取決於腎功能的嚴重程度。根據現有證據，嚴重腎功能不全（eGFR < 30 mL/min/1.73 m²）時禁用 metformin，但在輕度至中度腎功能不全（eGFR 30–60 mL/min/1.73 m²）時，現代大型世代研究顯示 metformin 可安全使用[2][5]。主要機轉是腎功能不全會增加 metformin 累積及乳酸中毒風險，因此需嚴格依腎功能調整用藥。
>
> ---
>
> ## 臨床注意事項
> - 嚴重腎功能不全（eGFR < 30 mL/min/1.73 m²）為 metformin 絕對禁忌症，應避免使用[2]。
> - 輕度至中度腎功能不全（eGFR 30–60 mL/min/1.73 m²）可考慮使用 metformin，但需減量並密切監測腎功能[5]。
> - 使用 metformin 前應先評估基礎腎功能，建議定期（如每 3–6 個月）追蹤 eGFR，若 eGFR 降至 30 mL/min/1.73 m² 以下應立即停藥[2][5]。
> - 進行含碘顯影劑的放射線檢查時，應暫停 metformin，因急性腎損傷風險增加[1]。
> - 乳酸中毒為嚴重但罕見的副作用，出現非特異性症狀（如倦怠、肌肉痛、腹痛、呼吸困難、嗜睡）時應立即停藥並就醫[3]。
> - 其他禁忌症包括已知對 metformin 過敏、急性或慢性代謝性酸中毒（如糖尿病酮酸中毒）[1][2]。
> - 若合併使用胰島素或胰島素促泌劑，低血糖風險增加，需調整劑量[3]。
> - 建議每年監測血液學參數，並每 2–3 年檢查維生素 B12 水準[3]。
>
> 目前證據主要來自歐美及澳洲等地區，亞洲地區的直接證據有限[5]。

| EXPECTED OWNER (all corpus keys) | OBSERVED OWNER(S) | VERDICT | NOTES |
|---|---|---|---|
| | | | |

---

### 3. `R16` — 0 NO-MATCH of 4 DailyMed citations

**Question as asked:**

> Which NSAIDs are safest for elderly patients with cardiovascular disease?

`status=ok` · `25.1s` · resolver keys: **none — no corpus drug resolves from this question**

**Citations as returned:**

| # | source | source_id | title | MOIETY (corpus join) | MECHANICAL flag |
|---|---|---|---|---|---|
| 1 | `pubmed` | `PMID:27959716` | Cardiovascular Safety of Celecoxib, Naproxen, or Ibuprofen for Arthritis. | — | — |
| 2 | `dailymed` | `DailyMed:213f0930-4a4a-4894-90b9-70c12daaa093#34066-1` | Salsalate (Salsalate) — Boxed Warning | `SALSALATE` | `NO-DRUG-IN-QUESTION` |
| 3 | `dailymed` | `DailyMed:198a4140-f4c0-4478-9157-ee1d68d0bb96#34066-1` | Ketoprofen (ketoprofen) — Boxed Warning | `KETOPROFEN` | `NO-DRUG-IN-QUESTION` |
| 4 | `dailymed` | `DailyMed:419c597f-6a6f-4420-b240-7dc4c223387e#34066-1` | Nabumetone (Nabumetone) — Boxed Warning | `NABUMETONE` | `NO-DRUG-IN-QUESTION` |
| 5 | `dailymed` | `DailyMed:7a78bb38-14d8-4a90-b883-482d4cebf716#34066-1` | Diflunisal (Diflunisal) — Boxed Warning | `DIFLUNISAL` | `NO-DRUG-IN-QUESTION` |

**Answer as generated:**

> ## Summary
>
> Among celecoxib, naproxen, and ibuprofen, celecoxib demonstrated noninferior cardiovascular safety compared to naproxen and ibuprofen in patients with arthritis at increased cardiovascular risk, including the elderly (HR for celecoxib vs. naproxen 0.93; HR for celecoxib vs. ibuprofen 0.85) [1]. All NSAIDs, including salsalate, ketoprofen, nabumetone, and diflunisal, carry boxed warnings for increased risk of serious cardiovascular thrombotic events and are contraindicated in the perioperative setting of coronary artery bypass graft (CABG) surgery [2][3][4][5].
>
> ---
>
> ## Clinical Notes
>
> - Celecoxib, naproxen, and ibuprofen were directly compared in a large randomized trial of patients with arthritis and increased cardiovascular risk; celecoxib was noninferior to naproxen and ibuprofen for the composite outcome of cardiovascular death, nonfatal myocardial infarction, or nonfatal stroke [1].
> - All NSAIDs, including salsalate, ketoprofen, nabumetone, and diflunisal, are associated with increased risk of serious cardiovascular thrombotic events (myocardial infarction, stroke), which can be fatal. This risk may increase with duration of use and may occur early in treatment [2][3][4][5].
> - NSAIDs are contraindicated for the treatment of perioperative pain in the setting of CABG surgery [2][3][4][5].
> - Elderly patients are at greater risk for serious gastrointestinal adverse events (bleeding, ulceration, perforation), which can occur at any time and without warning symptoms [2][3][4][5].
> - Monitoring: Assess cardiovascular risk at baseline and periodically during NSAID therapy. Monitor for signs of gastrointestinal bleeding, especially in elderly patients. Renal function should be checked at baseline and periodically, as NSAIDs can worsen renal function, particularly in those with pre-existing renal impairment [1].
> - The provided evidence does not address other NSAIDs beyond those listed, nor does it provide direct comparative data for salsalate, ketoprofen, nabumetone, or diflunisal in elderly patients with cardiovascular disease. No NSAID is free of cardiovascular risk in this population [2][3][4][5].

| EXPECTED OWNER (all corpus keys) | OBSERVED OWNER(S) | VERDICT | NOTES |
|---|---|---|---|
| | | | |

---

### 4. `R12` — 0 NO-MATCH of 3 DailyMed citations

**Question as asked:**

> is it ok to give both blood thinners at the same time

`status=ok` · `26.2s` · resolver keys: **none — no corpus drug resolves from this question**

**Citations as returned:**

| # | source | source_id | title | MOIETY (corpus join) | MECHANICAL flag |
|---|---|---|---|---|---|
| 1 | `dailymed` | `DailyMed:f1d77dba-9dae-4f30-b3e3-b4898993f865#34073-7` | Plavix (clopidogrel bisulfate) — Drug Interactions | `CLOPIDOGREL BISULFATE` | `NO-DRUG-IN-QUESTION` |
| 2 | `dailymed` | `DailyMed:fe0ced75-ccbf-4d2e-bd0d-b57e60ab913f#34073-7` | AGGRASTAT (TIROFIBAN) — Drug Interactions | `TIROFIBAN HYDROCHLORIDE MONOHYDRATE` | `NO-DRUG-IN-QUESTION` |
| 3 | `dailymed` | `DailyMed:bfe5cfb9-591d-4df8-12a3-6555cde3185d#34073-7` | UROKINASE (UROKINASE) — Drug Interactions | `UROKINASE` | `NO-DRUG-IN-QUESTION` |
| 4 | `pubmed` | `PMID:30691551` | Concomitant Use of Direct Oral Anticoagulants with Antiplatelet Agents and the Risk of Major Bleeding in Patients with Nonvalvular Atrial Fibrillation. | — | — |
| 5 | `pubmed` | `PMID:19276776` | Management of prehospital antiplatelet and anticoagulant therapy in traumatic head injury: a review. | — | — |

**Answer as generated:**

> ## Summary
>
> Concomitant use of multiple blood thinners (anticoagulants and/or antiplatelet agents) is associated with a significantly increased risk of bleeding, including gastrointestinal and intracranial hemorrhage, and should only be considered when the clinical benefit outweighs the risk [1][2][3][4][5]. In some clinical scenarios, such as patients with nonvalvular atrial fibrillation and comorbidities, dual therapy may be necessary, but careful risk assessment and monitoring are essential [4].
>
> ---
>
> ## Clinical Notes
>
> - **Increased Bleeding Risk:** Combining antiplatelet agents (e.g., clopidogrel, aspirin) with anticoagulants (e.g., warfarin, DOACs) or with other antiplatelet agents increases the risk of major bleeding events, including gastrointestinal and intracranial hemorrhage [1][2][3][4][5].
>     - For example, clopidogrel plus NSAIDs or warfarin increases gastrointestinal and overall bleeding risk [1].
>     - Tirofiban (a GP IIb/IIIa inhibitor) with other antiplatelet or anticoagulant drugs increases bleeding risk [2].
>     - Urokinase with anticoagulants or antiplatelet agents increases the risk of serious bleeding; careful monitoring is recommended [3].
>     - In patients with nonvalvular atrial fibrillation, DOAC-antiplatelet combinations had a similar risk of gastrointestinal bleeding (HR 1.08) but a lower risk of intracranial hemorrhage (HR 0.46) and other major bleeding (HR 0.68) compared to VKA-antiplatelet combinations [4].
>     - Prehospital use of antithrombotics (NSAIDs, aspirin, clopidogrel, warfarin, heparinoids) increases the risk of life-threatening intracranial hemorrhage after traumatic head injury [5].
>
> - **When NOT to Use:**
>     - Avoid routine combination therapy unless there is a clear, evidence-based indication (e.g., recent coronary stenting, mechanical heart valve, or specific high-risk atrial fibrillation scenarios) [1][4].
>     - Do not combine clopidogrel with omeprazole or esomeprazole, as these reduce clopidogrel's antiplatelet effect [1].
>     - Avoid in patients with active bleeding, recent hemorrhagic stroke, or severe bleeding diatheses [1][2][3].
>
> - **Key Contraindications:**
>     - Active pathological bleeding (e.g., peptic ulcer, intracranial hemorrhage) [1][2][3].
>     - Severe hepatic impairment or coagulopathy [1][2][3].
>     - Hypersensitivity to any component of the drugs [1][2][3].
>
> - **Monitoring Parameters:**
>     - **Bleeding:** Monitor for signs of bleeding (e.g., hemoglobin, hematocrit, overt bleeding) at baseline and regularly during therapy [1][2][3][4].
>     - **Renal and Hepatic Function:** Assess at baseline and periodically, especially for drugs with renal or hepatic clearance [1][2].
>     - **INR:** For warfarin combinations, monitor INR frequently to maintain therapeutic range and minimize bleeding risk [1].
>     - **Neurological Status:** In trauma or high-risk patients, monitor for signs of intracranial hemorrhage [5].
>     - **Drug Interactions:** Review all medications for potential interactions, especially with CYP2C19 inhibitors (e.g., omeprazole, esomeprazole) when using clopidogrel [1].
>
> - **Clinical Decision:** Use the lowest effective dose and shortest duration possible when combination therapy is indicated. Consider alternative agents with lower interaction potential (e.g., pantoprazole instead of omeprazole with clopidogrel) [1].
>
> - **Summary of Evidence Scope:** Most evidence is from North American and European cohorts; applicability to other populations may vary [4][5]. Some sources predate 2020 and may not reflect the latest practice standards [5].

| EXPECTED OWNER (all corpus keys) | OBSERVED OWNER(S) | VERDICT | NOTES |
|---|---|---|---|
| | | | |

---

### 5. `R01` — 0 NO-MATCH of 2 DailyMed citations

**Question as asked:**

> What are the side effects of Metformin in patients with renal impairment?

`status=ok` · `30.0s` · resolver keys: `METFORMIN`, `METFORMIN HCL`

**Citations as returned:**

| # | source | source_id | title | MOIETY (corpus join) | MECHANICAL flag |
|---|---|---|---|---|---|
| 1 | `dailymed` | `DailyMed:1f8833f9-1232-4aa7-a0d4-04a9f87dc2f0#34070-3` | Metformin HCl (Metformin HCl) — Contraindications | `METFORMIN HCL` | `MATCH` |
| 2 | `dailymed` | `DailyMed:fb832474-88d9-4e29-95cd-fbc446944cc4#43685-7` | Glumetza (metformin hydrochloride) — Warnings and Precautions | `METFORMIN` | `MATCH` |
| 3 | `pubmed` | `PMID:18095950` | Metformin-associated lactic acidosis in patients with renal impairment solely due to drug accumulation? | — | — |
| 4 | `pubmed` | `PMID:26773926` | Metformin-associated lactic acidosis: Current perspectives on causes and risk. | — | — |
| 5 | `pubmed` | `PMID:21241070` | Clinical pharmacokinetics of metformin. | — | — |

**Answer as generated:**

> ## Summary
>
> Metformin use in patients with renal impairment significantly increases the risk of metformin-associated lactic acidosis, which can be fatal, and may also lead to drug accumulation and multiorgan failure [1][2][3][4]. Other side effects include increased risk of vitamin B12 deficiency and, when used with insulin or insulin secretagogues, a higher risk of hypoglycemia [2].
>
> ---
>
> ## Clinical Notes
>
> - **Lactic Acidosis:** Metformin is contraindicated in patients with renal disease or dysfunction (e.g., serum creatinine ≥1.5 mg/dL in males, ≥1.4 mg/dL in females, or abnormal creatinine clearance) due to the increased risk of lactic acidosis, which can present with nonspecific symptoms (malaise, myalgias, abdominal pain, respiratory distress, somnolence) and progress to circulatory shock and multiorgan failure [1][2][3][4]. Mortality for metformin-associated lactic acidosis (MALA) can approach 50% [4].
> - **Drug Accumulation:** Renal impairment leads to reduced clearance of metformin, resulting in drug accumulation and a higher risk of lactic acidosis even in the absence of other predisposing factors [3][5].
> - **Vitamin B12 Deficiency:** Metformin may lower vitamin B12 levels; annual monitoring of hematological parameters and vitamin B12 every 2–3 years is recommended [2].
> - **Hypoglycemia:** The risk of hypoglycemia increases when metformin is used with insulin or insulin secretagogues; dose adjustments of these agents may be necessary [2].
> - **Temporary Discontinuation:** Metformin should be temporarily discontinued in patients undergoing radiologic studies with intravascular iodinated contrast due to risk of acute renal function alteration [1].
> - **Monitoring:** Assess renal function before starting metformin and periodically thereafter. Discontinue metformin if evidence of renal dysfunction develops [1][2]. Monitor for symptoms of lactic acidosis and educate patients and families about early signs [2].
> - **Contraindications:** Do not use metformin in patients with acute or chronic metabolic acidosis, including diabetic ketoacidosis, or known hypersensitivity to metformin [1].
>
> The evidence base includes data from ICU cohorts and pharmacokinetic studies; most findings are consistent across sources, but some recommendations may be conservative to maximize patient safety [3][4][5].

| EXPECTED OWNER (all corpus keys) | OBSERVED OWNER(S) | VERDICT | NOTES |
|---|---|---|---|
| | | | |

---

### 6. `R09` — 0 NO-MATCH of 2 DailyMed citations

**Question as asked:**

> What monitoring is required for patients on lithium therapy?

`status=ok` · `24.6s` · resolver keys: **none — no corpus drug resolves from this question**

**Citations as returned:**

| # | source | source_id | title | MOIETY (corpus join) | MECHANICAL flag |
|---|---|---|---|---|---|
| 1 | `dailymed` | `DailyMed:16ebe1f9-501d-468b-a37d-f6a46f8f32d1#34066-1` | Lithium Carbonate (Lithium Carbonate) — Boxed Warning | `LITHIUM CARBONATE` | `NO-DRUG-IN-QUESTION` |
| 2 | `dailymed` | `DailyMed:16ebe1f9-501d-468b-a37d-f6a46f8f32d1#43685-7` | Lithium Carbonate (Lithium Carbonate) — Warnings and Precautions | `LITHIUM CARBONATE` | `NO-DRUG-IN-QUESTION` |
| 3 | `pubmed` | `PMID:31837914` | Systematic review and practical guideline for the prevention and management of the renal side effects of lithium therapy. | — | — |
| 4 | `pubmed` | `PMID:3308295` | Lithium monitoring. | — | — |
| 5 | `pubmed` | `PMID:28953792` | Lithium therapeutic dose monitoring in human saliva. | — | — |

**Answer as generated:**

> ## Summary
>
> Patients on lithium therapy require regular monitoring of serum lithium concentrations, renal function, thyroid function, and serum calcium. Lithium has a narrow therapeutic range, and toxicity can occur at levels close to therapeutic concentrations, making prompt and accurate serum lithium determinations essential. Monitoring helps prevent and detect lithium toxicity, renal impairment, thyroid dysfunction, and hypercalcemia, all of which are associated with lithium use [1][2][3][4].
>
> ---
>
> ## Clinical Notes
>
> - **Serum Lithium Monitoring**: 
>   - Measure serum lithium concentrations regularly, as toxicity is closely related to serum levels and can occur at doses near the therapeutic range (therapeutic: 0.8–1.2 mEq/L; toxic: ≥1.5 mEq/L) [1][2].
>   - Blood samples should be drawn 12 hours after the last dose for accurate trough levels [4].
>   - Facilities for prompt and accurate serum lithium determinations must be available before starting therapy [1].
>   - Saliva monitoring is not currently reliable or recommended due to inconsistent evidence and lack of standardization [5].
>
> - **Renal Function Monitoring**:
>   - Assess kidney function at baseline and periodically during therapy, as lithium can cause nephrogenic diabetes insipidus and chronic kidney disease [2][3][4].
>   - Early diagnosis and management of renal side effects are critical to prevent permanent damage [3].
>
> - **Thyroid Function Monitoring**:
>   - Monitor thyroid function regularly, as both hypothyroidism and hyperthyroidism can occur with lithium therapy [2][4].
>
> - **Serum Calcium Monitoring**:
>   - Check serum calcium periodically due to the risk of hypercalcemia and hyperparathyroidism with long-term lithium use [2].
>
> - **Additional Monitoring and Safety**:
>   - Monitor for signs of lithium toxicity: neurological symptoms (tremor, ataxia, confusion), gastrointestinal symptoms, and cardiac arrhythmias [2].
>   - Educate patients to maintain hydration and a consistent salt intake to reduce risk of toxicity and hyponatremia [2].
>   - Monitor for lithium-induced polyuria and metabolic acidosis; consider amiloride for polyuria if needed [2][3].
>   - Increased risk of encephalopathic syndrome if combined with antipsychotics—monitor cognitive function closely [2].
>   - Collaboration between psychiatry and nephrology is recommended for patients with renal complications [3].
>
> - **When to Adjust or Discontinue Lithium**:
>   - Reduce dose or discontinue if significant renal impairment, severe toxicity, or persistent adverse effects develop [2][3].
>   - Consider switching to another mood stabilizer if lithium-induced nephropathy or nephrogenic diabetes insipidus occurs [3].
>
> - **Frequency of Monitoring**:
>   - The context does not specify exact intervals, but regular (often every 3–6 months) monitoring is standard in clinical practice for serum lithium, renal, thyroid, and calcium parameters [2][3][4]. 
>
> If more detailed protocols or frequency recommendations are needed, additional context or guidelines would be required.

| EXPECTED OWNER (all corpus keys) | OBSERVED OWNER(S) | VERDICT | NOTES |
|---|---|---|---|
| | | | |

---

### 7. `R10` — 0 NO-MATCH of 1 DailyMed citations

**Question as asked:**

> What are the clinical features of digoxin toxicity?

`status=ok` · `25.2s` · resolver keys: `DIGOXIN`

**Citations as returned:**

| # | source | source_id | title | MOIETY (corpus join) | MECHANICAL flag |
|---|---|---|---|---|---|
| 1 | `pubmed` | `PMID:39265879` | Expert Consensus on the Diagnosis and Management of Digoxin Toxicity. | — | — |
| 2 | `dailymed` | `DailyMed:1b7e5c6e-e052-41b0-a4ce-05dfe62faaaf#43685-7` | Digoxin (Digoxin) — Warnings and Precautions | `DIGOXIN` | `MATCH` |
| 3 | `pubmed` | `PMID:2979993` | Digitalis toxicity: mechanisms, diagnosis, and management. | — | — |
| 4 | `pubmed` | `PMID:31951334` | Clinical signs and symptoms of toxic serum digoxin levels in neonates. | — | — |
| 5 | `pubmed` | `PMID:3886755` | Digitalis cardiotoxicity. | — | — |

**Answer as generated:**

> ## Summary
>
> The clinical features of digoxin toxicity are highly variable and often nonspecific, including gastrointestinal, neurological, and cardiac manifestations. Common symptoms include nausea, vomiting, abdominal pain, confusion, visual disturbances, and a range of cardiac arrhythmias, with bradyarrhythmias and conduction blocks being particularly notable. The risk and presentation of toxicity are influenced by serum digoxin levels, renal function, and electrolyte imbalances[1][2][4][5].
>
> ---
>
> ## Clinical Notes
>
> - **Gastrointestinal Symptoms:** Nausea, vomiting, and abdominal pain are frequent early signs of digoxin toxicity[1][4].
> - **Neurological Symptoms:** Confusion, weakness, and visual disturbances (such as blurred or yellow vision) may occur[1][4].
> - **Cardiac Manifestations:** 
>   - Arrhythmias are the most serious complications. These include:
>     - Sinus bradycardia and sinoatrial block, especially in patients with pre-existing sinus node disease[2][5].
>     - Advanced or complete atrioventricular (AV) block, particularly in those with pre-existing conduction abnormalities[2][5].
>     - Ventricular arrhythmias, including ventricular fibrillation, especially in patients with accessory AV pathways (e.g., Wolff-Parkinson-White syndrome)[2][5].
>     - In neonates, sinus bradycardia was observed, but no other digoxin-related arrhythmias were reported in one study[4].
> - **Electrolyte Abnormalities:** Hypokalemia, hypomagnesemia, and hypercalcemia increase the risk and severity of toxicity[2][4].
> - **Serum Digoxin Levels:** Symptoms are more likely at higher serum digoxin concentrations. In neonates, symptomatic toxicity was observed with levels >5 ng/mL, while asymptomatic patients had lower levels[4].
> - **Other Features:** In patients with heart failure with preserved ejection fraction, susceptibility to toxicity is increased[2].
> - **Misdiagnosis Risk:** Signs and symptoms of digoxin toxicity may be mistaken for worsening heart failure[2].
> - **Special Populations:** Neonates and patients with renal impairment are at higher risk due to reduced clearance and should be monitored closely[2][4].
> - **Monitoring Parameters:**
>   - Regularly monitor serum digoxin levels, especially if symptoms develop or if there are changes in renal function or electrolyte status[1][2][4].
>   - Monitor for new or worsening arrhythmias via ECG.
>   - Check serum potassium, magnesium, and calcium levels frequently, particularly if toxicity is suspected or if the patient is on diuretics[2].
> - **Thresholds for Concern:**
>   - In neonates, symptoms were observed at serum digoxin levels >5 ng/mL[4].
>   - In adults, the therapeutic range is generally considered 0.5–2.0 ng/mL, but toxicity can occur at lower levels, especially with comorbidities or drug interactions[1][2].
> - **When to Use Antidote:** Digoxin-specific antibody fragments (digoxin immune Fab) are recommended for life-threatening toxicity, such as severe arrhythmias or hemodynamic instability[1][4].
>
> If further detail on specific arrhythmias or rare manifestations is needed, the context does not provide a comprehensive list.

| EXPECTED OWNER (all corpus keys) | OBSERVED OWNER(S) | VERDICT | NOTES |
|---|---|---|---|
| | | | |

---

### 8. `R18` — 0 NO-MATCH of 1 DailyMed citations

**Question as asked:**

> 我的病人在用 statin，最近說肌肉痛，我該怎麼辦

`status=ok` · `26.9s` · resolver keys: **none — no corpus drug resolves from this question**

**Citations as returned:**

| # | source | source_id | title | MOIETY (corpus join) | MECHANICAL flag |
|---|---|---|---|---|---|
| 1 | `dailymed` | `DailyMed:a60cc18b-0631-4cf0-b021-9f52224ece65#43685-7` | Lipitor (atorvastatin calcium) — Warnings and Precautions | `ATORVASTATIN` | `NO-DRUG-IN-QUESTION` |
| 2 | `pubmed` | `PMID:19217515` | Managing statin myopathy. | — | — |
| 3 | `pubmed` | `PMID:25694464` | Statin-associated muscle symptoms: impact on statin therapy-European Atherosclerosis Society Consensus Panel Statement on Assessment, Aetiology and Management. | — | — |
| 4 | `pubmed` | `PMID:18367041` | Statin myopathy. | — | — |
| 5 | `pubmed` | `PMID:36958647` | Statin Intolerance: A Review and Update. | — | — |

**Answer as generated:**

> ## 摘要
> 當病人在使用 statin（如 atorvastatin）時出現肌肉痛，應立即評估其症狀嚴重度並檢查肌酸激酶（CK）水平。若肌肉痛伴隨明顯CK升高、虛弱、發燒或全身不適，應考慮暫停 statin，並進一步評估是否為肌病或橫紋肌溶解症[1][3][5]。statin相關肌肉症狀（SAMS）是停藥的主要原因之一，及早辨識與處理可減少不必要的停藥並維持心血管保護效果[3][5]。
>
> ---
>
> ## 臨床注意事項
> - **安全警示與停藥時機**：若病人出現不明原因的肌肉疼痛、壓痛或無力，特別是伴隨全身不適或發燒時，應立即檢查CK。若CK顯著升高（如超過正常上限10倍），或懷疑橫紋肌溶解症，應立即停用 statin[1][3]。
> - **高風險族群**：65歲以上、腎功能不全、未控制的甲狀腺功能低下、合併使用其他藥物（如其他降脂藥）、高劑量 statin 使用者，發生肌病的風險較高[1][2][4]。
> - **監測建議**：
>   - 初次出現肌肉症狀時，應檢查CK並評估肝功能（AST/ALT）[1][3]。
>   - 若CK正常或僅輕微升高，可考慮減量、換用不同 statin 或調整劑型，並密切追蹤症狀[3][5]。
>   - 若CK顯著升高或有橫紋肌溶解症表現（如肌紅蛋白尿、腎功能惡化），應立即停藥並處理相關併發症[1][3]。
> - **其他處置**：
>   - 可考慮補充維生素D或輔酶Q10以減輕肌肉症狀，但證據有限[5]。
>   - 若需繼續降脂治療，可嘗試不同 statin 或間歇性劑量，並合併非statin類降脂藥物[3][5]。
> - **特殊情境**：規律運動者使用 statin 時，需更密切監測肌肉症狀與CK，但運動本身不構成停藥指標[5]。
> - **免疫介導壞死性肌病（IMNM）**：極罕見，若懷疑此症（如持續性肌無力與高CK），應立即停藥並考慮轉介風濕免疫專科[1][4]。
>
> 如臨床症狀與 statin 使用有明顯時序關聯，建議依上述步驟處理，並根據個案風險評估後決定是否重新挑戰 statin 或改用其他降脂方案[3][5]。

| EXPECTED OWNER (all corpus keys) | OBSERVED OWNER(S) | VERDICT | NOTES |
|---|---|---|---|
| | | | |

---

### 9. `R20` — 0 NO-MATCH of 1 DailyMed citations

**Question as asked:**

> Can I use ACE inhibitors during pregnancy?

`status=ok` · `24.7s` · resolver keys: **none — no corpus drug resolves from this question**

**Citations as returned:**

| # | source | source_id | title | MOIETY (corpus join) | MECHANICAL flag |
|---|---|---|---|---|---|
| 1 | `dailymed` | `DailyMed:97a9e8bf-91ed-4256-97d4-f9504bb01373#34066-1` | Aceon (perindopril erbumine) — Boxed Warning | `PERINDOPRIL ERBUMINE` | `NO-DRUG-IN-QUESTION` |
| 2 | `pubmed` | `PMID:33779043` | Increased risk of major congenital malformations in early pregnancy use of angiotensin-converting-enzyme inhibitors and angiotensin-receptor-blockers: a meta-analysis. | — | — |
| 3 | `pubmed` | `PMID:32815286` | Adverse pregnancy outcomes associated with first-trimester exposure to angiotensin-converting enzyme inhibitors or angiotensin II receptor blockers: A systematic review and meta-analysis. | — | — |
| 4 | `pubmed` | `PMID:9201818` | Angiotensin converting enzyme inhibitors in pregnancy. | — | — |
| 5 | `pubmed` | `PMID:9761159` | Assessing the teratogenic potential of angiotensin-converting enzyme inhibitors in pregnancy. | — | — |

**Answer as generated:**

> ## Summary
>
> ACE inhibitors should not be used during pregnancy due to a higher risk of major congenital malformations, cardiovascular malformations, and stillbirths, especially when exposure occurs in the first trimester or later stages of pregnancy [1][2][3]. The mechanism involves disruption of the renin-angiotensin system, which is critical for fetal development, leading to fetal injury and death [1].
>
> ---
>
> ## Clinical Notes
>
> - **Boxed Warning:** ACE inhibitors, including perindopril (Aceon), carry a boxed warning for fetal toxicity. They must be discontinued as soon as pregnancy is detected because drugs acting on the renin-angiotensin system can cause injury and death to the developing fetus [1].
> - **Risks:** Meta-analyses show increased risk of major congenital malformations (OR 1.82–1.94), cardiovascular malformations (OR 2.50), and stillbirth (OR 1.75) with first-trimester exposure to ACE inhibitors compared to non-exposed pregnancies [2][3].
> - **Timing:** Adverse fetal effects are reported with both first-trimester and later pregnancy exposure, but skull hypoplasia and renal dysfunction are more associated with prolonged or late exposure [5].
> - **Contraindications:** ACE inhibitors are contraindicated in pregnancy at any stage. They should not be initiated in women who are pregnant, and current users should discontinue the drug immediately upon detection of pregnancy [1][4].
> - **Monitoring:** For women of reproductive age on ACE inhibitors, regular pregnancy testing and counseling on effective contraception are recommended. If pregnancy occurs, stop the ACE inhibitor immediately and consider alternative antihypertensive therapy [1].
> - **Alternative Antihypertensives:** Other oral antihypertensives do not show an increased risk of congenital malformations compared to non-exposed controls (OR 0.96) [2].
> - **Evidence Limitations:** Some older sources (pre-2000) suggest the teratogenic risk may be lower with first-trimester exposure, but recent meta-analyses consistently show increased risk [2][3][5]. The most robust and current evidence supports avoiding ACE inhibitors throughout pregnancy.
>
> In summary, ACE inhibitors are contraindicated in pregnancy due to clear evidence of harm to the fetus. Immediate discontinuation and alternative management are required if pregnancy is detected.

| EXPECTED OWNER (all corpus keys) | OBSERVED OWNER(S) | VERDICT | NOTES |
|---|---|---|---|
| | | | |

---

### 10. `MF01` — 0 NO-MATCH of 0 DailyMed citations

**Question as asked:**

> calcium channel blocker mechanism

`status=ok` · `25.3s` · resolver keys: `CALCIUM`, `CALCIUM ACETATE`

**Citations as returned:**

| # | source | source_id | title | MOIETY (corpus join) | MECHANICAL flag |
|---|---|---|---|---|---|
| 1 | `pubmed` | `PMID:36604796` | High-dose insulin should be used before vasopressors/inotropes in calcium-channel blocker toxicity. | — | — |
| 2 | `pubmed` | `PMID:15898828` | Pharmacology, pathophysiology and management of calcium channel blocker and beta-blocker toxicity. | — | — |
| 3 | `pubmed` | `PMID:7889444` | Comparative pharmacology of calcium antagonists. | — | — |
| 4 | `pubmed` | `PMID:21563902` | High-dose insulin therapy in beta-blocker and calcium channel-blocker poisoning. | — | — |
| 5 | `pubmed` | `PMID:37599112` | Exploring calcium channel blocker as a candidate drug for Pseudomonas aeruginosa through network pharmacology and experimental validation. | — | — |

**Answer as generated:**

> ## Summary
>
> Calcium channel blockers (CCBs) act by directly blocking calcium flow through L-type calcium channels found in the heart, vasculature, and pancreas, leading to decreased intracellular calcium and resulting in reduced cardiac automaticity, conduction, contraction, and vascular tone [2], [3]. This mechanism underlies their clinical effects in cardiovascular disorders and their toxicity profile in overdose situations [2], [3].
>
> ---
>
> ## Clinical Notes
>
> - **Mechanism of Action:** CCBs inhibit the influx of calcium ions through L-type calcium channels in cardiac and vascular smooth muscle cells, which decreases intracellular calcium levels. This leads to reduced myocardial contractility (negative inotropy), slowed conduction through the atrioventricular node (negative dromotropy), and vasodilation due to relaxation of vascular smooth muscle [2], [3].
> - **Toxicity:** In overdose, CCBs can cause profound bradycardia, hypotension, conduction disturbances, and cardiovascular collapse due to excessive suppression of cardiac and vascular calcium-dependent processes [2].
> - **Drug Class Differences:** Non-dihydropyridine CCBs (e.g., verapamil, diltiazem) are more likely to cause bradycardia, conduction disturbances, and severe hypotension, while dihydropyridines (e.g., nifedipine) tend to cause vasodilation and reflex tachycardia with fewer conduction issues [2], [3].
> - **Management of Toxicity:** High-dose insulin therapy is recommended as first-line treatment in CCB poisoning with cardiovascular compromise, especially if cardiac dysfunction is present, and should be initiated before vasopressors/inotropes, though not delaying their use if needed [1], [4]. Conventional therapies (atropine, glucagon, calcium) often fail in severe cases [4].
> - **Monitoring:** In toxicity, monitor heart rate, blood pressure, cardiac rhythm, and signs of end-organ perfusion continuously. Blood glucose and potassium should be checked frequently (every 30–60 minutes) during high-dose insulin therapy to prevent hypoglycemia and hypokalemia [4].
> - **Contraindications and Cautions:** CCBs should be used cautiously or avoided in patients with severe hypotension, advanced heart block (unless a pacemaker is present), or severe heart failure due to their negative inotropic and chronotropic effects [2], [3]. Drug interactions with other negative chronotropes (e.g., beta-blockers) can increase risk of bradycardia and heart block [2].
> - **Other Effects:** CCBs may also have effects on pancreatic beta cells, reducing insulin secretion and contributing to hyperglycemia in overdose [2].
>
> No information on non-cardiovascular mechanisms or non-human effects is provided in the supplied context.

| EXPECTED OWNER (all corpus keys) | OBSERVED OWNER(S) | VERDICT | NOTES |
|---|---|---|---|
| | | | |

---

### 11. `MF02` — 0 NO-MATCH of 0 DailyMed citations

**Question as asked:**

> atorvastatin calcium side effects

`status=ok` · `24.8s` · resolver keys: `ATORVASTATIN`, `CALCIUM`, `CALCIUM ACETATE`

**Citations as returned:**

| # | source | source_id | title | MOIETY (corpus join) | MECHANICAL flag |
|---|---|---|---|---|---|
| 1 | `pubmed` | `PMID:41655587` | Assessment of adverse effects attributed to statin therapy in product labels: a meta-analysis of double-blind randomised controlled trials. | — | — |
| 2 | `pubmed` | `PMID:40281622` | Pharmacogenomic insights into atorvastatin and rosuvastatin adverse effects: a prospective observational study in the UAE's multiethnic population. | — | — |
| 3 | `pubmed` | `PMID:41060387` | Association between atorvastatin and sarcopenia: a study based on NHANES and FAERS databases. | — | — |
| 4 | `pubmed` | `PMID:10582478` | [Atorvastatin (Lipitor)]. | — | — |

**Answer as generated:**

> ## Summary
>
> Atorvastatin calcium is associated with increased risks of abnormal liver transaminases (RR 1.41), other liver function test abnormalities (RR 1.32), and diabetes (RR 1.10) compared to placebo, as well as a higher risk of sarcopenia (OR 2.21) and statin-associated muscle symptoms (SAMS) in certain genetic subgroups [1], [2], [3]. The most common side effects are gastrointestinal and transient, but musculoskeletal and hepatic adverse effects require particular attention [1], [2], [3], [4].
>
> ---
>
> ## Clinical Notes
>
> - **Key Adverse Effects:**
>   - Abnormal liver transaminases (RR 1.41) and other liver function test abnormalities (RR 1.32) occur more frequently with atorvastatin than placebo [1].
>   - Increased risk of diabetes (RR 1.10) has been observed [1].
>   - Atorvastatin use is associated with a higher risk of sarcopenia (OR 2.21; 95% CI: 1.07-4.55) based on population-based and pharmacovigilance data [3].
>   - Statin-associated muscle symptoms (SAMS) are more likely in individuals with the SLCO1B1 rs4149056 variant, especially females and Arabs (twofold increased risk, P < 0.05) [2].
>   - Gastrointestinal side effects are common but usually transient [4].
>
> - **Safety Warnings and Contraindications:**
>   - Avoid use in patients with active liver disease or unexplained persistent elevations of serum transaminases [1], [4].
>   - Use with caution in patients with a history of muscle disorders or those at increased risk for myopathy (e.g., elderly, frail, or those with renal impairment) [1], [3].
>   - Genetic variants (SLCO1B1, ABCG2) may increase risk of adverse effects; consider pharmacogenomic testing in high-risk populations [2].
>
> - **Drug Interactions:**
>   - Combination with ezetimibe increases risk of SAMS and liver enzyme elevation [2].
>   - Caution with other drugs that increase risk of myopathy or hepatotoxicity [1], [2].
>
> - **Monitoring Parameters:**
>   - Liver function tests: Check at baseline, then periodically (e.g., every 3–6 months during the first year, then annually or as clinically indicated). Discontinue if transaminases rise to >3× upper limit of normal [1].
>   - Blood glucose: Monitor for new-onset diabetes, especially in patients with risk factors [1].
>   - Musculoskeletal assessment: Regularly assess for muscle pain, weakness, or signs of sarcopenia, particularly in older adults or those with risk alleles [2], [3].
>   - Consider periodic creatine kinase (CK) measurement if muscle symptoms develop [1].
>
> - **Special Populations:**
>   - East Asian patients and those with specific genetic variants (ABCG2 rs2231142 for rosuvastatin, SLCO1B1 rs4149056 for atorvastatin) are at higher risk for adverse effects [2].
>   - Females and Arabs may have higher rates of SAMS with atorvastatin [2].
>
> - **Evidence Limitations:**
>   - Most safety data are from large double-blind RCTs and pharmacovigilance databases; some findings (e.g., sarcopenia risk) require further confirmation in prospective studies [3].
>   - Some older sources (e.g., [4], 1999) may not reflect current clinical practice or genetic insights.

| EXPECTED OWNER (all corpus keys) | OBSERVED OWNER(S) | VERDICT | NOTES |
|---|---|---|---|
| | | | |

---

### 12. `MF03` — 0 NO-MATCH of 0 DailyMed citations

**Question as asked:**

> low sodium diet and blood pressure

`status=ok` · `24.6s` · resolver keys: `SODIUM ACETATE`

**Citations as returned:**

| # | source | source_id | title | MOIETY (corpus join) | MECHANICAL flag |
|---|---|---|---|---|---|
| 1 | `pubmed` | `PMID:32332617` | Effectiveness of a multifactorial intervention, consisting of self-management of antihypertensive medication, self-measurement of blood pressure, hypocaloric and low sodium diet, and physical exercise, in patients with uncontrolled hypertension taking 2 or more antihypertensive drugs: The MEDICHY study. | — | — |
| 2 | `pubmed` | `PMID:37534516` | Effect of low-sodium salt applied to Chinese modified DASH diet on arterial stiffness in older patients with hypertension and type 2 diabetes. | — | — |
| 3 | `pubmed` | `PMID:32057379` | Salt Reduction to Prevent Hypertension and Cardiovascular Disease: JACC State-of-the-Art Review. | — | — |
| 4 | `pubmed` | `PMID:27757935` | Impact of Salt Intake on the Pathogenesis and Treatment of Hypertension. | — | — |
| 5 | `pubmed` | `PMID:40086509` | Sodium. | — | — |

**Answer as generated:**

> ## Summary
>
> A low sodium diet lowers blood pressure in both hypertensive and normotensive individuals, with a more pronounced effect in those with hypertension [3], [4]. The mechanism involves reducing extracellular fluid volume and modifying hormonal and inflammatory pathways that regulate blood pressure [3], [5].
>
> ---
>
> ## Clinical Notes
>
> - Safety Warnings and Contraindications:
>   - Sodium deficiency is rare but can occur in certain medical conditions; excessive sodium restriction may risk hyponatremia, especially in older adults, those with renal impairment, or patients on diuretics [5].
>   - Monitor for symptoms of hyponatremia (e.g., confusion, weakness, seizures) in high-risk populations.
>
> - Key Contraindications:
>   - Use caution in patients with conditions predisposing to sodium loss (e.g., chronic diarrhea, vomiting, adrenal insufficiency).
>   - Patients with advanced heart failure or chronic kidney disease may require individualized sodium targets.
>
> - Monitoring Parameters:
>   - Assess blood pressure at baseline and regularly (e.g., every 4–12 weeks) after dietary sodium reduction [1], [3].
>   - Monitor serum sodium and renal function, especially in older adults, those with comorbidities, or those on diuretics; check at baseline and within 2–4 weeks of dietary change, then periodically.
>   - Target sodium intake: Most guidelines recommend <2.3 g sodium/day (equivalent to <5 g salt/day) for adults [5].
>   - In patients with hypertension and comorbidities (e.g., diabetes), a low sodium diet combined with other interventions (e.g., DASH diet, physical activity) further improves blood pressure and arterial stiffness [2].
>
> - Additional Notes:
>   - Not all individuals are equally salt-sensitive; about 50–60% of hypertensive patients show significant blood pressure reduction with sodium restriction [4].
>   - Salt reduction is cost-effective and recommended at the population level to reduce cardiovascular risk [3].
>   - Further research is needed to refine sodium targets for specific subgroups and to assess long-term outcomes in diverse populations [2], [3].

| EXPECTED OWNER (all corpus keys) | OBSERVED OWNER(S) | VERDICT | NOTES |
|---|---|---|---|
| | | | |

---

### 13. `MF04` — 0 NO-MATCH of 0 DailyMed citations

**Question as asked:**

> potassium supplements in CKD

`status=ok` · `24.6s` · resolver keys: `POTASSIUM ACETATE`

**Citations as returned:**

| # | source | source_id | title | MOIETY (corpus join) | MECHANICAL flag |
|---|---|---|---|---|---|
| 1 | `pubmed` | `PMID:33804015` | Current Management of Hyperkalemia in Non-Dialysis CKD: Longitudinal Study of Patients Receiving Stable Nephrology Care. | — | — |
| 2 | `pubmed` | `PMID:31706619` | Potassium homeostasis and management of dyskalemia in kidney diseases: conclusions from a Kidney Disease: Improving Global Outcomes (KDIGO) Controversies Conference. | — | — |
| 3 | `pubmed` | `PMID:37545002` | Hyperkalemia in chronic kidney disease: a focus on potassium lowering pharmacotherapy. | — | — |
| 4 | `pubmed` | `PMID:33247727` | Does dietary potassium intake associate with hyperkalemia in patients with chronic kidney disease? | — | — |
| 5 | `pubmed` | `PMID:35372861` | Potassium Homeostasis, Chronic Kidney Disease, and the Plant-Enriched Diets. | — | — |

**Answer as generated:**

> ## Summary
>
> Potassium supplements are generally not recommended in chronic kidney disease (CKD) due to the high risk of hyperkalemia, which is associated with serious adverse outcomes in this population [3]. Evidence shows that hyperkalemia in CKD is more strongly associated with comorbidities such as diabetes and metabolic acidosis, rather than dietary potassium intake, but there is no support for routine potassium supplementation in CKD patients [4]. The current literature emphasizes caution, as even plant-based diets—while beneficial for cardiovascular health—are approached carefully in CKD due to potassium concerns, and there is little direct evidence supporting liberal potassium intake in this group [5].
>
> ---
>
> ## Clinical Notes
>
> - Potassium supplementation is contraindicated in CKD patients, especially those with reduced glomerular filtration rate (GFR), due to impaired renal potassium excretion and the resulting risk of hyperkalemia [3].
> - Hyperkalemia (serum potassium >5.0 mEq/L) is common in CKD and is associated with increased risk in patients with diabetes or metabolic acidosis, regardless of dietary potassium intake [4].
> - Routine monitoring of serum potassium is essential in CKD, particularly when using medications that can increase potassium (e.g., renin-angiotensin-aldosterone system blockers, mineralocorticoid receptor antagonists) [3], [4].
>   - Suggested monitoring: check serum potassium at baseline and at regular intervals (e.g., every 1–3 months or more frequently if at risk or after medication changes).
>   - Immediate action is required if serum potassium exceeds 5.5 mEq/L; consider stopping potassium supplements, adjusting medications, and initiating potassium-lowering therapies as needed [3].
> - There is no evidence in the provided context supporting the use of potassium supplements for CKD patients; instead, the focus is on avoiding excess potassium and managing hyperkalemia [3], [4], [5].
> - New potassium-binding agents are available and effective for lowering serum potassium, but their use is for treating hyperkalemia, not for supplementing potassium [5].
> - If hypokalemia occurs (rare in CKD), investigate and address underlying causes rather than routine supplementation [2].
> - The evidence base does not support routine potassium supplementation in CKD, and current guidelines and expert opinion recommend against it due to safety concerns [2], [3], [4], [5].

| EXPECTED OWNER (all corpus keys) | OBSERVED OWNER(S) | VERDICT | NOTES |
|---|---|---|---|
| | | | |

---

### 14. `R02` — 0 NO-MATCH of 0 DailyMed citations

**Question as asked:**

> What is the first-line treatment for hypertension in diabetic patients?

`status=ok` · `23.2s` · resolver keys: **none — no corpus drug resolves from this question**

**Citations as returned:**

| # | source | source_id | title | MOIETY (corpus join) | MECHANICAL flag |
|---|---|---|---|---|---|
| 1 | `pubmed` | `PMID:37831122` | Hypertension in diabetes. | — | — |

**Answer as generated:**

> ## Summary
>
> The first-line treatment for hypertension in diabetic patients is the use of renin-angiotensin-aldosterone system (RAAS) blockers, such as ACE inhibitors or angiotensin receptor blockers (ARBs), as highlighted by many international guidelines. However, current evidence from several meta-analyses and systematic reviews does not demonstrate clear superiority of RAAS blockers over other antihypertensive medications in this population [1].
>
> ---
>
> ## Clinical Notes
>
> - RAAS blockers (ACE inhibitors or ARBs) are commonly recommended as first-line agents for hypertension in diabetes by multiple international guidelines, due to their potential renal and cardiovascular protective effects [1].
> - Despite guideline preference, meta-analyses and systematic reviews have not shown RAAS blockers to be superior to other antihypertensive classes (such as calcium channel blockers, thiazide diuretics, or beta-blockers) in reducing morbidity or mortality in diabetic patients with hypertension [1].
> - Safety considerations:
>   - RAAS blockers are contraindicated in patients with a history of angioedema related to previous ACE inhibitor or ARB use, bilateral renal artery stenosis, or pregnancy.
>   - Monitor for hyperkalemia and worsening renal function; check serum potassium and creatinine at baseline, within 1–2 weeks after initiation or dose adjustment, and periodically thereafter.
>   - Dose reduction or discontinuation is recommended if serum potassium exceeds 5.5 mmol/L or if there is a significant rise in serum creatinine (e.g., >30% from baseline).
> - Blood pressure targets and monitoring frequency should follow specific guideline recommendations, with more frequent monitoring during medication titration and in patients with advanced kidney disease or other comorbidities [1].
> - The choice of antihypertensive agent should be individualized, considering patient-specific factors, comorbidities, and potential drug interactions.
> - The evidence base referenced is international and includes both adult and pediatric populations, but specific regional or ethnic subgroup data are not detailed in the provided context [1].

| EXPECTED OWNER (all corpus keys) | OBSERVED OWNER(S) | VERDICT | NOTES |
|---|---|---|---|
| | | | |

---

### 15. `R03` — 0 NO-MATCH of 0 DailyMed citations

**Question as asked:**

> What are the indications for prophylactic anticoagulation in atrial fibrillation?

`status=ok` · `25.4s` · resolver keys: **none — no corpus drug resolves from this question**

**Citations as returned:**

| # | source | source_id | title | MOIETY (corpus join) | MECHANICAL flag |
|---|---|---|---|---|---|
| 1 | `pubmed` | `PMID:30144419` | Antithrombotic Therapy for Atrial Fibrillation: CHEST Guideline and Expert Panel Report. | — | — |
| 2 | `pubmed` | `PMID:39716733` | Spotlight on the 2024 ESC/EACTS management of atrial fibrillation guidelines: 10 novel key aspects. | — | — |
| 3 | `pubmed` | `PMID:39374908` | The 2024 European Society of Cardiology Guidelines for Diagnosis and Management of Atrial Fibrillation: A Viewpoint from a Practicing Clinician's Perspective. | — | — |

**Answer as generated:**

> ## Summary
>
> Prophylactic anticoagulation is indicated in patients with atrial fibrillation (AF) who have at least one non-sex-related stroke risk factor, as assessed by the CHA₂DS₂-VASc score, to prevent thromboembolism and stroke[1][2]. The 2024 ESC/EACTS guidelines emphasize individualized risk assessment and recommend oral anticoagulation for most patients with non-valvular AF and ≥1 non-sex CHA₂DS₂-VASc risk factor[2]. The decision to initiate anticoagulation should be based on a careful evaluation of stroke risk versus bleeding risk[1][2].
>
> ---
>
> ## Clinical Notes
>
> - **Indications:**
>   - Oral anticoagulation is recommended for patients with non-valvular AF and at least one non-sex-related CHA₂DS₂-VASc risk factor (e.g., age ≥65, hypertension, diabetes, heart failure, prior stroke/TIA, vascular disease)[1][2].
>   - The 2024 ESC/EACTS guidelines reinforce individualized assessment and recommend anticoagulation for most patients with ≥1 non-sex CHA₂DS₂-VASc risk factor[2].
>   - For patients with AF at low risk (CHA₂DS₂-VASc score 0 in men, 1 in women), anticoagulation is generally not recommended[1].
>   - The guidelines also address anticoagulation in special scenarios, such as device-detected subclinical AF and AF with ischemic stroke despite anticoagulation, but detailed criteria are not provided in the supplied context[2].
>
> - **Contraindications and Safety Warnings:**
>   - Do not use anticoagulation in patients with active major bleeding or severe bleeding diathesis.
>   - Contraindicated in patients with recent hemorrhagic stroke or severe thrombocytopenia.
>   - Caution in patients with high bleeding risk; use validated bleeding risk scores (e.g., HAS-BLED) to guide monitoring and mitigation strategies[1].
>
> - **Monitoring Parameters:**
>   - Assess renal and hepatic function at baseline and periodically, especially for direct oral anticoagulants (DOACs).
>   - Monitor for signs of bleeding at each visit.
>   - Reassess stroke and bleeding risk at least annually, or more frequently if clinical status changes[2].
>   - For warfarin, maintain INR in the therapeutic range (typically 2.0–3.0) and check INR at least monthly.
>
> - **Other Considerations:**
>   - The 2024 ESC/EACTS guidelines highlight the importance of dynamic reassessment and comorbidity management as part of the AF-CARE framework[2].
>   - The evidence base is primarily from European and North American populations; applicability to other regions is not specified in the provided context.
>
> References: [1] CHEST Guideline and Expert Panel Report (2018); [2] ESC/EACTS 2024 Guidelines; [3] ESC 2024 Viewpoint.

| EXPECTED OWNER (all corpus keys) | OBSERVED OWNER(S) | VERDICT | NOTES |
|---|---|---|---|
| | | | |

---

### 16. `R04` — 0 NO-MATCH of 0 DailyMed citations

**Question as asked:**

> What is the mechanism of action of statins?

`status=ok` · `25.3s` · resolver keys: **none — no corpus drug resolves from this question**

**Citations as returned:**

| # | source | source_id | title | MOIETY (corpus join) | MECHANICAL flag |
|---|---|---|---|---|---|
| 1 | `pubmed` | `PMID:12067471` | Statins: mechanism of action and effects. | — | — |
| 2 | `pubmed` | `PMID:24657242` | The pharmacology of statins. | — | — |
| 3 | `pubmed` | `PMID:28057795` | Pleiotropic Effects of Statins on the Cardiovascular System. | — | — |
| 4 | `pubmed` | `PMID:15559032` | HMG CoA reductase inhibitors. | — | — |

**Answer as generated:**

> ## Summary
>
> Statins lower serum cholesterol primarily by inhibiting hepatic HMG-CoA reductase, the rate-limiting enzyme in cholesterol biosynthesis, which leads to upregulation of hepatic LDL receptors and increased clearance of LDL-cholesterol from the bloodstream [1], [2], [3]. Additionally, statins have pleiotropic effects—such as modulating endothelial function, stabilizing atherosclerotic plaques, and reducing inflammation—due to inhibition of isoprenoid intermediates, though the clinical relevance of these effects is still debated [1], [3].
>
> ---
>
> ## Clinical Notes
>
> - Statins act by competitively inhibiting HMG-CoA reductase, reducing cholesterol synthesis in the liver and increasing hepatic LDL receptor expression, thereby enhancing LDL-cholesterol clearance [1], [2], [3].
> - Pleiotropic effects include inhibition of post-translational prenylation of small GTP-binding proteins (e.g., Rho, Rac), which may affect endothelial nitric oxide synthase expression, plaque stability, inflammatory cytokine production, platelet reactivity, and cardiac remodeling [3]. The clinical impact of these effects is not fully quantified [3].
> - Statins are indicated for primary and secondary prevention of coronary artery disease and stroke, and for various forms of dyslipidemia [1], [4].
> - Safety considerations: Statins are generally well tolerated, but adverse effects can include myopathy, increased risk of diabetes, and, less commonly, liver enzyme elevations and cataracts [2], [4]. 
> - Contraindications: Active liver disease and unexplained persistent elevations of hepatic transaminases are key contraindications [2].
> - Monitoring: 
>   - Baseline and periodic liver function tests are recommended; discontinue if transaminases rise to >3 times the upper limit of normal [2].
>   - Monitor for muscle symptoms; check creatine kinase if myopathy is suspected [2].
>   - Consider monitoring blood glucose in patients at risk for diabetes [2].
> - Drug interactions: Statins metabolized by cytochrome P450 enzymes (especially CYP3A4) may interact with other drugs affecting these pathways, increasing the risk of adverse effects [2].
> - The evidence base for these mechanisms and safety considerations is drawn from studies spanning 1994–2017 and may not reflect the most current data.

| EXPECTED OWNER (all corpus keys) | OBSERVED OWNER(S) | VERDICT | NOTES |
|---|---|---|---|
| | | | |

---

### 17. `R05` — 0 NO-MATCH of 0 DailyMed citations

**Question as asked:**

> What are the signs of serotonin syndrome?

`status=ok` · `24.6s` · resolver keys: **none — no corpus drug resolves from this question**

**Citations as returned:**

| # | source | source_id | title | MOIETY (corpus join) | MECHANICAL flag |
|---|---|---|---|---|---|
| 1 | `pubmed` | `PMID:37309284` | Serotonin syndrome-A focused review. | — | — |
| 2 | `pubmed` | `PMID:35551099` | Serotonin syndrome. | — | — |
| 3 | `pubmed` | `PMID:31523132` | Serotonin Syndrome: Pathophysiology, Clinical Features, Management, and Potential Future Directions. | — | — |

**Answer as generated:**

> ## Summary
>
> The key signs of serotonin syndrome are neuromuscular excitation (such as tremor, hyperreflexia, and clonus), autonomic dysfunction (including hyperthermia, tachycardia, and diaphoresis), and altered mental status (such as agitation or confusion), typically occurring in the context of recent initiation or dose change of serotonergic drugs[1], [2]. Not all features are present in every patient, but the presence of this triad in someone exposed to serotonergic agents should raise strong suspicion[1], [2].
>
> ---
>
> ## Clinical Notes
>
> - The central clinical features of serotonin syndrome include:
>   - Neuromuscular excitation: tremor, hyperreflexia, clonus (especially inducible or spontaneous), myoclonus, and muscle rigidity[1], [2].
>   - Autonomic dysfunction: hyperthermia (temperature >38.5°C), tachycardia, diaphoresis, mydriasis, hypertension, and sometimes diarrhea[1], [2].
>   - Altered mental status: agitation, confusion, anxiety, and sometimes delirium[1], [2].
> - The syndrome can develop rapidly, often within hours of a change in serotonergic therapy or overdose[1].
> - Severe cases may present with marked hyperthermia (>38.5°C), which requires urgent cooling and sedation; if these measures fail, rapid sequence intubation and paralysis may be necessary[2].
> - Not all patients will display the full triad of symptoms; clinical suspicion should remain high in any patient with new serotonergic drug exposure and compatible symptoms[1], [2].
> - Differential diagnosis includes neuroleptic malignant syndrome, anticholinergic toxicity, and malignant hyperthermia[1].
> - Early recognition and withdrawal of serotonergic agents are crucial to prevent morbidity and mortality[1], [2].
> - Monitoring should include frequent assessment of vital signs, temperature, and mental status; severe cases require high-dependency or intensive care monitoring, especially if hyperthermia or severe autonomic instability is present[2].
> - The provided context does not detail specific laboratory findings or diagnostic criteria thresholds.

| EXPECTED OWNER (all corpus keys) | OBSERVED OWNER(S) | VERDICT | NOTES |
|---|---|---|---|
| | | | |

---

### 18. `R06` — 0 NO-MATCH of 0 DailyMed citations

**Question as asked:**

> How should heparin-induced thrombocytopenia (HIT) be managed?

`status=ok` · `27.3s` · resolver keys: `HEPARIN SODIUM`

**Citations as returned:**

| # | source | source_id | title | MOIETY (corpus join) | MECHANICAL flag |
|---|---|---|---|---|---|
| 1 | `pubmed` | `PMID:30482768` | American Society of Hematology 2018 guidelines for management of venous thromboembolism: heparin-induced thrombocytopenia. | — | — |
| 2 | `pubmed` | `PMID:22315270` | Treatment and prevention of heparin-induced thrombocytopenia: Antithrombotic Therapy and Prevention of Thrombosis, 9th ed: American College of Chest Physicians Evidence-Based Clinical Practice Guidelines. | — | — |
| 3 | `pubmed` | `PMID:33095876` | Management of heparin-induced thrombocytopenia: systematic reviews and meta-analyses. | — | — |
| 4 | `pubmed` | `PMID:32337112` | Heparin-induced Thrombocytopenia: Pathophysiology, Diagnosis and Management. | — | — |
| 5 | `pubmed` | `PMID:38236118` | HEPARIN-INDUCED THROMBOCYTOPENIA SYNDROME AMONG HEMODIALYSIS PATIENTS AND DISEASE MANAGEMENT STRATEGY. | — | — |

**Answer as generated:**

> ## Summary
>
> Management of heparin-induced thrombocytopenia (HIT) requires immediate discontinuation of all heparin products and initiation of a non-heparin anticoagulant, preferably a direct thrombin inhibitor such as argatroban or bivalirudin, or danaparoid where available [1][2][3][5]. Early recognition and treatment are critical to prevent life-threatening thrombotic complications, as HIT is a highly prothrombotic condition [1][4][5].
>
> ---
>
> ## Clinical Notes
>
> - **Immediate Actions:**
>   - Stop all forms of heparin, including flushes and catheter locks, as soon as HIT is suspected [1][5].
>   - Do not wait for laboratory confirmation if clinical suspicion is high; prompt action is essential [1][4][5].
>
> - **Alternative Anticoagulation:**
>   - Start a non-heparin anticoagulant. Preferred agents include:
>     - Argatroban (especially in renal insufficiency) [2]
>     - Bivalirudin (especially if urgent cardiac surgery is needed) [2]
>     - Danaparoid (where available) [2]
>     - Direct oral anticoagulants (DOACs) may be considered, but evidence is low-certainty and primarily noncomparative [3].
>   - Avoid vitamin K antagonists (e.g., warfarin) until platelet count has recovered to at least 150 × 10^9/L due to risk of venous limb gangrene [1][2].
>
> - **Platelet Transfusion:**
>   - Avoid platelet transfusions unless there is life-threatening bleeding, as transfusion may increase thrombotic risk [1][3].
>
> - **Monitoring:**
>   - Monitor platelet counts daily until recovery [1].
>   - Monitor for new or progressive thrombosis clinically and with imaging as indicated [1][2].
>   - For patients at >1% risk of HIT (e.g., post-surgical, unfractionated heparin), monitor platelet counts every 2–3 days from day 4 to 14 of heparin exposure [2].
>   - In hemodialysis patients, ensure all heparin sources are discontinued and use alternative anticoagulation for dialysis sessions [5].
>
> - **Special Populations:**
>   - In patients requiring urgent cardiac surgery, bivalirudin is preferred over other non-heparin anticoagulants or heparin plus antiplatelet agents [2].
>   - For renal replacement therapy, use non-heparin anticoagulants; direct thrombin inhibitors are preferred [5].
>
> - **Contraindications and Cautions:**
>   - Do not use low molecular weight heparin (LMWH) as cross-reactivity with HIT antibodies is common [1][2].
>   - Avoid vitamin K antagonists until platelet recovery [1][2].
>   - Inferior vena cava filters and platelet transfusions may result in greater harm and should generally be avoided [3].
>
> - **Diagnosis:**
>   - Use the 4Ts score to estimate pretest probability of HIT; avoid laboratory testing and empiric treatment in patients with low-probability scores [1].
>   - Laboratory confirmation is required, but treatment should not be delayed for results if clinical suspicion is high [1][4][5].
>
> - **Evidence Limitations:**
>   - Most evidence is low to very low certainty, based on noncomparative studies and case series [3].
>   - Recommendations are primarily based on expert consensus and guideline panels [1][2][3].
>
> If further details on dosing, duration, or specific agent selection are needed, the provided context does not supply this information.

| EXPECTED OWNER (all corpus keys) | OBSERVED OWNER(S) | VERDICT | NOTES |
|---|---|---|---|
| | | | |

---

### 19. `R08` — 0 NO-MATCH of 0 DailyMed citations

**Question as asked:**

> What is the recommended dose of aspirin for cardiovascular prevention?

`status=ok` · `24.9s` · resolver keys: `ASPIRIN`

**Citations as returned:**

| # | source | source_id | title | MOIETY (corpus join) | MECHANICAL flag |
|---|---|---|---|---|---|
| 1 | `pubmed` | `PMID:41294093` | Aspirin Dosing for Secondary Prevention of Atherosclerotic Cardiovascular Disease in Chronic Obstructive Pulmonary Disease and Asthma: Insights From ADAPTABLE. | — | — |
| 2 | `pubmed` | `PMID:19482214` | Aspirin in the primary and secondary prevention of vascular disease: collaborative meta-analysis of individual participant data from randomised trials. | — | — |
| 3 | `pubmed` | `PMID:41876873` | Aspirin Dosing in Secondary Prevention of Atherosclerotic Cardiovascular Disease. | — | — |
| 4 | `pubmed` | `PMID:37132104` | Redefining the Roles of Aspirin across the Spectrum of Cardiovascular Disease Prevention. | — | — |
| 5 | `pubmed` | `PMID:26323750` | Aspirin dosing in cardiovascular disease prevention and management: an update. | — | — |

**Answer as generated:**

> ## Summary
>
> The recommended dose of aspirin for secondary prevention of atherosclerotic cardiovascular disease (ASCVD) is low-dose aspirin, typically 75–100 mg daily, as higher doses do not improve efficacy and may increase bleeding risk [1], [3]. This recommendation is supported by recent randomized controlled trial data and current guideline summaries [1], [3], [4].
>
> ---
>
> ## Clinical Notes
>
> - Low-dose aspirin (75–100 mg daily) is preferred for secondary prevention of ASCVD, including in patients with comorbidities such as chronic obstructive pulmonary disease (COPD) or asthma, as higher doses (e.g., 325 mg) do not provide additional cardiovascular benefit and may increase bleeding risk [1], [3].
> - In the ADAPTABLE trial, no significant difference in ASCVD outcomes was observed between 81 mg and 325 mg aspirin doses, except for a possible difference in stroke prevention among patients with COPD/asthma, which requires further study [1].
> - High-dose aspirin (325 mg) is associated with a higher risk of major bleeding and is not recommended for routine secondary prevention [3].
> - Contraindications to aspirin include active gastrointestinal bleeding, known hypersensitivity to aspirin or other NSAIDs, and certain bleeding disorders [5].
> - Caution is advised in patients with a history of peptic ulcer disease, uncontrolled hypertension, or concomitant use of anticoagulants or other antiplatelet agents due to increased bleeding risk [5].
> - Monitoring parameters:
>   - Assess for signs of gastrointestinal bleeding (e.g., melena, hematemesis) and unexplained anemia at baseline and periodically during therapy.
>   - Monitor for new or worsening respiratory symptoms in patients with asthma or COPD, as aspirin can rarely trigger bronchospasm in sensitive individuals [1].
>   - Reassess bleeding risk regularly, especially in elderly patients or those with additional risk factors [4].
> - There is no evidence in the provided context to support routine use of aspirin for primary prevention except in select high-risk patients with low bleeding risk, and this should be individualized [2], [4].

| EXPECTED OWNER (all corpus keys) | OBSERVED OWNER(S) | VERDICT | NOTES |
|---|---|---|---|
| | | | |

---

### 20. `R13` — 0 NO-MATCH of 0 DailyMed citations

**Question as asked:**

> warfarin 和 aspirin 一起用 safe 嗎

`status=ok` · `26.0s` · resolver keys: `ASPIRIN`

**Citations as returned:**

| # | source | source_id | title | MOIETY (corpus join) | MECHANICAL flag |
|---|---|---|---|---|---|
| 1 | `pubmed` | `PMID:38263263` | Risk of bleeding with concomitant use of oral anticoagulants and aspirin: A systematic review and meta-analysis. | — | — |
| 2 | `pubmed` | `PMID:27785526` | Efficacy and safety of aspirin combined with warfarin after acute coronary syndrome : A meta-analysis. | — | — |
| 3 | `pubmed` | `PMID:21813162` | Anticoagulation therapy with combined low dose aspirin and warfarin following mechanical heart valve replacement. | — | — |
| 4 | `pubmed` | `PMID:17267456` | Safety and efficacy of combined antiplatelet-warfarin therapy after coronary stenting. | — | — |
| 5 | `pubmed` | `PMID:27595682` | Use of concomitant aspirin in patients with atrial fibrillation: Findings from the ROCKET AF trial. | — | — |

**Answer as generated:**

> ## 摘要
> Warfarin 與 aspirin 合併使用會顯著增加出血風險（RCTs: OR 1.36；觀察性研究: OR 1.42），而且在多數臨床情境下，並未帶來明顯的總體死亡率或心血管事件風險降低[1][2][5]。僅在特定族群（如機械瓣膜置換術後患者）低劑量合併治療可降低血栓栓塞事件，且不增加重大出血[3]。
>
> ---
>
> ## 臨床注意事項
> - 安全警示：Warfarin 與 aspirin 合併使用時，出血風險顯著上升，包含重大及輕微出血（重大出血 RR 1.738，輕微出血 RR 2.767）[2]。ROCKET AF 研究顯示合併使用者全因死亡率（HR 1.27）及出血（HR 1.32）均顯著上升，特別是在無冠心病史者[5]。
> - 禁忌症與適應症：除非有明確適應症（如機械瓣膜置換、近期急性冠心症、特定高風險血栓狀況），一般不建議常規合併使用[1][2][3][5]。冠狀動脈支架術後僅用 warfarin+aspirin 預防支架血栓效果不佳[4]。
> - 監測參數：
>   - 定期監測 INR，建議維持於2.0-3.0（機械瓣膜患者可依指引調整）[2][3]。
>   - 監測血紅素、血小板、腎功能及肝功能，出血徵象需即時評估。
>   - 若出現不明原因出血、黑便、血尿、皮下出血或顱內出血症狀，應立即停藥並處理。
> - 劑量建議：如需合併，aspirin 劑量應控制於低劑量（≤100 mg/天），並嚴格控制 warfarin 劑量與INR[2][3]。
> - 追蹤頻率：初始治療期每週監測INR，穩定後每月一次，遇有出血風險因子變化時需加密追蹤。
> - 藥物交互作用：避免與其他抗血小板、NSAIDs、部分抗生素等合併使用，以免進一步提升出血風險[1][2]。
>
> 總結：Warfarin 與 aspirin 合併治療僅限於特定高風險族群，需嚴格監控出血風險與INR，並避免無適應症下長期合併使用。

| EXPECTED OWNER (all corpus keys) | OBSERVED OWNER(S) | VERDICT | NOTES |
|---|---|---|---|
| | | | |

---

### 21. `R14` — 0 NO-MATCH of 0 DailyMed citations

**Question as asked:**

> When can beta blockers actually be used in heart failure? I thought they were contraindicated.

`status=ok` · `25.9s` · resolver keys: **none — no corpus drug resolves from this question**

**Citations as returned:**

| # | source | source_id | title | MOIETY (corpus join) | MECHANICAL flag |
|---|---|---|---|---|---|
| 1 | `pubmed` | `PMID:10568667` | Beta-adrenergic blocker mortality trials in congestive heart failure. | — | — |
| 2 | `pubmed` | `PMID:32981932` | Treatment optimization of beta-blockers in chronic heart failure therapy. | — | — |
| 3 | `pubmed` | `PMID:32700759` | Beta-blockers for congestive heart failure in children. | — | — |
| 4 | `pubmed` | `PMID:36086982` | Use of beta-blockers in patients with heart failure - unresolved issues. | — | — |
| 5 | `pubmed` | `PMID:9046949` | Beta-adrenergic blocking agents in the treatment of congestive heart failure: mechanisms and clinical results. | — | — |

**Answer as generated:**

> ## Summary
>
> Beta blockers are now a standard therapy for patients with mild-to-moderate chronic heart failure and are not universally contraindicated; they improve survival and limit disease progression when used appropriately in adults with reduced ejection fraction heart failure (HFrEF) [1], [2]. Their use requires careful initiation and titration, and they should be avoided or used with caution in certain acute or unstable settings [1], [2].
>
> ---
>
> ## Clinical Notes
>
> - **Indications:** Beta blockers are recommended for adults with chronic heart failure with reduced ejection fraction (LVEF <40%) unless contraindicated [2]. They are not universally contraindicated and have become standard of care for this population [1], [2].
> - **Efficacy:** Major mortality trials have shown that beta blockers (specifically metoprolol, bisoprolol, carvedilol, or bucindolol) reduce mortality and slow progression of heart failure in adults with mild-to-moderate symptoms [1]. The estimated number needed to treat is 35 to save one life [1].
> - **Pediatric Use:** Evidence in children is less robust; studies show mixed results with no significant difference in mortality or heart transplantation rates, and the benefit in pediatric heart failure remains uncertain [3].
> - **Contraindications:** Beta blockers should not be initiated in patients with acute decompensated heart failure, severe bradycardia, second- or third-degree heart block (without a pacemaker), or severe asthma [1], [2]. Caution is advised in patients with comorbidities such as thyroid disease or significant hypotension [4].
> - **Drug Selection:** Only certain beta blockers (metoprolol, bisoprolol, carvedilol, bucindolol) are guideline-recommended for heart failure; atenolol is not recommended [2].
> - **Initiation and Titration:** Start at a low dose and titrate slowly ("start low and go slow") [1]. Monitor for worsening heart failure symptoms, bradycardia, and hypotension during titration [1], [2].
> - **Monitoring:** 
>   - Assess heart rate and blood pressure at each visit.
>   - Monitor for signs of fluid overload or worsening heart failure, especially during dose increases.
>   - Consider ECG monitoring for patients at risk of conduction abnormalities.
> - **Unresolved Issues:** Optimal titration targets (dose vs. heart rate), effects in heart failure with preserved ejection fraction (HFpEF), and efficacy in patients with certain comorbidities (e.g., thyroid disease) remain areas of uncertainty [4].
> - **Summary of Evidence Base:** Most evidence is from adult populations in Western countries; pediatric and non-Western data are limited or inconclusive [1], [2], [3], [5]. 
>
> In summary, beta blockers are indicated and beneficial in stable, chronic HFrEF in adults, but require careful patient selection, initiation, and monitoring. They remain contraindicated in acute decompensated states and certain conduction or respiratory disorders.

| EXPECTED OWNER (all corpus keys) | OBSERVED OWNER(S) | VERDICT | NOTES |
|---|---|---|---|
| | | | |

---

### 22. `R15` — 0 NO-MATCH of 0 DailyMed citations

**Question as asked:**

> What is the difference between Type 1 and Type 2 heparin-induced thrombocytopenia?

`status=ok` · `21.7s` · resolver keys: `HEPARIN SODIUM`

**Citations as returned:**

| # | source | source_id | title | MOIETY (corpus join) | MECHANICAL flag |
|---|---|---|---|---|---|
| 1 | `pubmed` | `PMID:8975463` | [Heparin-induced thrombocytopenia]. | — | — |

**Answer as generated:**

> ## Summary
>
> Type 1 heparin-induced thrombocytopenia (HIT) is nonimmunologically mediated, while Type 2 HIT is immunologically mediated. Type 2 HIT is associated with a risk of serious thromboembolic complications, whereas Type 1 is not[1].
>
> ---
>
> ## Clinical Notes
>
> - Type 1 HIT results from direct platelet activation by heparin and is not immune-mediated; it typically does not lead to significant clinical complications[1].
> - Type 2 HIT is immune-mediated, involving antibodies that activate platelets, and is the most frequent drug-induced immune thrombocytopenia[1].
> - Type 2 HIT is distinct from other forms of immune thrombocytopenia because it can be accompanied by serious thromboembolic complications, necessitating prompt and intensive management[1].
> - The provided context does not specify detailed clinical management, diagnostic criteria, or monitoring parameters for either type.

| EXPECTED OWNER (all corpus keys) | OBSERVED OWNER(S) | VERDICT | NOTES |
|---|---|---|---|
| | | | |

---

### 23. `R17` — 0 NO-MATCH of 0 DailyMed citations

**Question as asked:**

> How long should dual antiplatelet therapy be continued after coronary stent placement?

`status=ok` · `27.3s` · resolver keys: **none — no corpus drug resolves from this question**

**Citations as returned:**

| # | source | source_id | title | MOIETY (corpus join) | MECHANICAL flag |
|---|---|---|---|---|---|
| 1 | `pubmed` | `PMID:38599220` | Ticagrelor alone versus ticagrelor plus aspirin from month 1 to month 12 after percutaneous coronary intervention in patients with acute coronary syndromes (ULTIMATE-DAPT): a randomised, placebo-controlled, double-blind clinical trial. | — | — |
| 2 | `pubmed` | `PMID:32247565` | Outcomes of Left Main Bifurcation Stenting Depends on Both Length of Dual Antiplatelet Therapy and Stenting Strategy. | — | — |
| 3 | `pubmed` | `PMID:39038086` | Demystifying the Contemporary Role of 12-Month Dual Antiplatelet Therapy After Acute Coronary Syndrome. | — | — |
| 4 | `pubmed` | `PMID:30522654` | ACC/AHA Versus ESC Guidelines on Dual Antiplatelet Therapy: JACC Guideline Comparison. | — | — |
| 5 | `pubmed` | `PMID:18319394` | Indications for dual antiplatelet therapy with aspirin and clopidogrel: evidence-based recommendations for use. | — | — |

**Answer as generated:**

> ## Summary
>
> The optimal duration of dual antiplatelet therapy (DAPT) after coronary stent placement is not fixed for all patients, but 12 months has historically been the standard, especially after acute coronary syndrome (ACS) and percutaneous coronary intervention (PCI) with drug-eluting stents [3], [4]. However, recent evidence supports individualizing DAPT duration: shorter DAPT (<12 months) is favored in patients at high bleeding risk, while longer DAPT (>12 months) may be considered in those at high ischemic risk who tolerate therapy well [3]. The ULTIMATE-DAPT trial showed that after 1 month of DAPT post-PCI for ACS, switching to ticagrelor monotherapy (discontinuing aspirin) reduced clinically relevant bleeding without increasing major adverse cardiovascular and cerebrovascular events (MACCE) compared to continuing DAPT for 12 months [1].
>
> ---
>
> ## Clinical Notes
>
> - **Safety Warnings and Contraindications:**
>   - DAPT increases bleeding risk; careful assessment of bleeding versus ischemic risk is essential [3].
>   - Contraindications include active pathological bleeding, history of intracranial hemorrhage, or hypersensitivity to either agent [1], [3].
>   - Ticagrelor is contraindicated in patients with severe hepatic impairment and should be used cautiously in those with a history of bradyarrhythmias [1].
>
> - **Key Recommendations by Population:**
>   - **General ACS/PCI Population:** 12 months of DAPT (aspirin plus a P2Y12 inhibitor) remains a class I guideline recommendation, but this is based on older studies with median DAPT durations of 9–15 months [3], [4].
>   - **High Bleeding Risk:** Consider DAPT for less than 12 months, with early transition to P2Y12 inhibitor monotherapy (e.g., ticagrelor alone after 1 month) as supported by ULTIMATE-DAPT, which showed lower bleeding (BARC 2/3/5) and non-inferior ischemic outcomes (MACCE) compared to continued DAPT [1], [3].
>   - **High Ischemic Risk:** Prolonged DAPT (>12 months) may be considered if bleeding risk is low and ischemic risk is high [3].
>   - **Left Main Bifurcation Stenting:** Short DAPT is associated with lower major adverse cardiovascular events (MACEs) in single-stent strategies (OR 0.49), while prolonged DAPT (>12 months) is associated with higher MACEs (OR 7.39) in this group; longer DAPT may be more appropriate after double stenting [2].
>
> - **Monitoring Parameters:**
>   - **Bleeding:** Monitor for signs of bleeding at every follow-up, especially in the first month and after any therapy change [1], [3].
>   - **Platelet Count and Hemoglobin:** Check at baseline and periodically, especially if clinical suspicion for bleeding arises [1].
>   - **Renal and Hepatic Function:** Assess at baseline; ticagrelor should be avoided in severe hepatic impairment [1].
>   - **Adherence:** Reinforce medication adherence at each visit, as premature discontinuation increases stent thrombosis risk [3].
>
> - **Transition and De-escalation:**
>   - After 1 month of DAPT post-PCI for ACS, switching to ticagrelor monotherapy is supported by recent RCT evidence for patients without major events in the first month [1].
>   - De-escalation strategies (dose reduction or switch to clopidogrel) may be considered in selected patients, but specific protocols should be individualized [3].
>
> - **Uncertainties and Gaps:**
>   - Most recent RCT evidence (ULTIMATE-DAPT) included patients from China, Italy, Pakistan, and the UK; applicability to other populations should be interpreted with caution [1].
>   - Guidelines and evidence for DAPT duration in stable CAD or non-ACS PCI are not detailed in the provided context.
>
> In summary, 12 months of DAPT remains standard after ACS and PCI, but shorter durations with early switch to monotherapy are increasingly supported for patients at higher bleeding risk, while longer durations may benefit those at higher ischemic risk [1], [2], [3]. Individualized risk assessment and close monitoring are essential.

| EXPECTED OWNER (all corpus keys) | OBSERVED OWNER(S) | VERDICT | NOTES |
|---|---|---|---|
| | | | |

---

### 24. `R19` — 0 NO-MATCH of 0 DailyMed citations

**Question as asked:**

> What are the renal dosing adjustments required for common antibiotics?

`status=ok` · `23.0s` · resolver keys: **none — no corpus drug resolves from this question**

**Citations as returned:**

| # | source | source_id | title | MOIETY (corpus join) | MECHANICAL flag |
|---|---|---|---|---|---|
| 1 | `pubmed` | `PMID:30862698` | Clinical Pharmacology of Antibiotics. | — | — |
| 2 | `pubmed` | `PMID:20736235` | Determination of antibiotic dosage adjustments in patients with renal impairment: elements for success. | — | — |

**Answer as generated:**

> ## Summary
>
> Renal dosing adjustments for common antibiotics are necessary because patients with chronic kidney disease (CKD) often have altered drug clearance, protein binding, and volume of distribution, which can increase the risk of toxicity if standard doses are used. The optimal approach is to adjust antibiotic dosing based on both pharmacokinetic changes (such as reduced kidney clearance) and pharmacodynamic targets (such as maintaining drug concentrations above the minimum inhibitory concentration for time-dependent antibiotics) to maximize efficacy and minimize toxicity and resistance [1], [2].
>
> ---
>
> ## Clinical Notes
>
> - **When to Adjust Doses:** Antibiotic dosing should be adjusted in patients with renal impairment, especially those with CKD, due to reduced kidney clearance and possible changes in protein binding and volume of distribution [1].
> - **Key Antibiotic Classes Requiring Adjustment:**
>   - **Beta-lactams (e.g., penicillins, cephalosporins, carbapenems):** Most require dose reduction or interval extension in renal impairment to avoid accumulation and toxicity [1].
>   - **Aminoglycosides:** Require both dose and interval adjustments; monitor for nephrotoxicity and ototoxicity [1].
>   - **Vancomycin:** Requires close monitoring of serum trough levels and dose adjustment based on kidney function [1].
>   - **Fluoroquinolones:** Many require dose reduction in renal impairment, except moxifloxacin [1].
> - **Pharmacodynamic Considerations:** For time-dependent antibiotics (e.g., beta-lactams), the goal is to maximize the time that free drug concentrations remain above the MIC. For concentration-dependent antibiotics (e.g., aminoglycosides), achieving a high peak concentration relative to MIC is important [1], [2].
> - **Monitoring Parameters:**
>   - **Renal Function:** Check estimated glomerular filtration rate (eGFR) or creatinine clearance at baseline and periodically during therapy [1].
>   - **Drug Levels:** For drugs with narrow therapeutic windows (e.g., vancomycin, aminoglycosides), monitor serum drug concentrations as per institutional protocols [1].
>   - **Toxicity:** Monitor for signs of antibiotic toxicity (e.g., nephrotoxicity, neurotoxicity) and adjust doses accordingly [1].
> - **Contraindications and Cautions:**
>   - Avoid nephrotoxic antibiotics (e.g., aminoglycosides, vancomycin) in patients with severe renal impairment unless no alternatives exist [1].
>   - Be cautious with drugs that have active metabolites excreted by the kidney, as these may accumulate and cause toxicity [1].
> - **Dosing Strategies:** Extended or continuous infusions may be considered for some beta-lactams to optimize pharmacodynamic exposure in patients with renal impairment [2].
> - **Evidence Limitations:** The provided sources do not list specific dosing regimens for individual antibiotics; clinicians should consult up-to-date dosing references or institutional guidelines for exact dose adjustments [1], [2].

| EXPECTED OWNER (all corpus keys) | OBSERVED OWNER(S) | VERDICT | NOTES |
|---|---|---|---|
| | | | |

---

## What this pack cannot establish, even if every unit is scored

- **It is N=1 per query.** Retrieval churns run-to-run — the 2026-07-28 harvest measured mean turnover **0.423** on identical input minutes apart. A single run shows what happened once, not a rate.
- **24 units cannot separate *rare* from *common*.** With zero observed wrong-drug answers, the 95% upper bound on the true rate is roughly **1 − 0.05^(1/24) ≈ 12%** — i.e. a defect affecting up to ~1 in 8 answers is entirely consistent with a clean sweep of this pack.
- **The population is curated and deliberately loaded.** R01–R20 over-represents hard cases by construction, and the four `MF` units were *selected because they are already known to misfire*. This pack is a detector, not an estimator; it cannot support a traffic-rate claim.
- **It measures the answer layer only.** It says nothing about whether a better document existed and was not retrieved — a correct-looking answer from a thin pool still scores clean here.
