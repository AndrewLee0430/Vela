# Native-medical-review checklist — th / ar / hi / bn / he / vi

**Created 2026-06-08.** Consolidates the THREE previously-scattered review flags into ONE
gate: (1) the Stage-2/T2 hero-chip review line, (2) the PHASE-D onboarding role/workplace
terms, (3) the §3.3 role-aware example queries. Plus the W1 privacy-card rewording.

These strings shipped to prod (fly v173) **best-effort** for the six low-confidence
locales and need a **native speaker with medical-terminology competence** to verify (not
transliteration — correct clinical vocabulary, grade/seniority terms, and natural
phrasing). en + zh-TW are author-confidence; zh-CN / ja / ko / es / fr / de / it / pt are
normal-confidence and are **out of scope** for this gate.

## How to use this checklist

1. Open the source file listed for each key and locate the key's **th, ar, hi, bn, he, vi**
   cells. Source files (the only place strings live — edit there, this doc is a tracker):
   - `utils/i18n.ts` — `heroChip*`, `eg*`
   - `utils/i18n-ui.ts` — `onboardingWorkplace*`, `onboardingHospitalNudge`, `onboardingRole*`, `onboardingPrivacy*`
2. Compare each cell against the **English reference** (Table A) — fix the cell **in the
   source file** if the medical term / phrasing is wrong.
3. Check off the cell in the **status grid** (Table B): `☐` → `✓` reviewed-ok, or `✏️`
   reviewed-and-corrected. Note corrections in the "Notes" column.
4. RTL (ar, he): keep strings in logical order; proper nouns (Metformin, NOAC, ARDS,
   FDA, eGFR) stay in Latin script.

> **Format note:** the current per-locale strings are NOT transcribed into this doc (234
> non-Latin cells) — that would risk corrupting the source of truth via copy errors.
> Review + edit happen **in the `.ts` files**; this doc tracks the English reference,
> risk level, file location, and per-cell status.

**Inventory: 39 keys × 6 locales = 234 cells.**

---

## Table A — key inventory (English reference + risk)

Risk: 🔴 = specialised clinical/medical terminology (highest review priority) · 🟡 = clinical but common · ⚪ = generic / proper-noun / non-clinical (lowest).

| # | Key | File | English reference | Risk |
|---|-----|------|-------------------|------|
| 1 | `heroChip1` | i18n.ts | Metformin in CKD (eGFR ≥30) | ⚪ |
| 2 | `heroChip2` | i18n.ts | Can elderly patients take BP meds with calcium? | 🟡 |
| 3 | `heroChip3` | i18n.ts | Is it safe to use antibiotics during pregnancy? | 🟡 |
| 4 | `onboardingWorkplaceCommunity` | i18n-ui.ts | Community | ⚪ |
| 5 | `onboardingWorkplaceHospital` | i18n-ui.ts | Hospital | ⚪ |
| 6 | `onboardingWorkplaceStudent` | i18n-ui.ts | Student | ⚪ |
| 7 | `onboardingWorkplaceResearch` | i18n-ui.ts | Research | ⚪ |
| 8 | `onboardingHospitalNudge` | i18n-ui.ts | "Heads up: Vela isn't a hospital EHR or clinical decision-support system — it's a reference tool. Always confirm against your institution's protocols." | 🔴 |
| 9 | `onboardingRolePhysician` | i18n-ui.ts | Physician | 🟡 |
| 10 | `onboardingRolePharmacist` | i18n-ui.ts | Pharmacist | 🟡 |
| 11 | `onboardingRoleNurse` | i18n-ui.ts | Nurse | 🟡 |
| 12 | `onboardingRolePT` | i18n-ui.ts | Physical therapist | 🔴 |
| 13 | `onboardingRoleOT` | i18n-ui.ts | Occupational therapist | 🔴 |
| 14 | `onboardingRoleSLP` | i18n-ui.ts | Speech-language pathologist | 🔴 |
| 15 | `onboardingRoleOtherClinical` | i18n-ui.ts | Other clinical | ⚪ |
| 16 | `onboardingRoleOtherHospital` | i18n-ui.ts | Other hospital staff | ⚪ |
| 17 | `onboardingRoleMedStudent` | i18n-ui.ts | Medical student | 🔴 |
| 18 | `onboardingRolePharmStudent` | i18n-ui.ts | Pharmacy student | 🔴 |
| 19 | `onboardingRoleNursingStudent` | i18n-ui.ts | Nursing student | 🔴 |
| 20 | `onboardingRoleResident` | i18n-ui.ts | Resident | 🔴 |
| 21 | `onboardingRoleIntern` | i18n-ui.ts | Intern | 🔴 |
| 22 | `onboardingRoleOtherStudent` | i18n-ui.ts | Other student | ⚪ |
| 23 | `onboardingRoleResearcher` | i18n-ui.ts | Researcher | ⚪ |
| 24 | `onboardingRoleOtherResearch` | i18n-ui.ts | Other research | ⚪ |
| 25 | `onboardingRoleOther` | i18n-ui.ts | Other | ⚪ |
| 26 | `egPharmacist1` | i18n.ts | Adjusting Metformin dose in renal impairment | 🔴 |
| 27 | `egPharmacist2` | i18n.ts | Key differences between the NOACs | 🔴 |
| 28 | `egPharmacist3` | i18n.ts | Which antihistamines are safe in pregnancy? | 🔴 |
| 29 | `egNurse1` | i18n.ts | Home care essentials for diabetic foot ulcers | 🔴 |
| 30 | `egNurse2` | i18n.ts | Pressure injury staging and management | 🔴 |
| 31 | `egNurse3` | i18n.ts | Fall risk assessment in frail older adults | 🔴 |
| 32 | `egPhysician1` | i18n.ts | Antibiotic choice for upper respiratory infection | 🔴 |
| 33 | `egPhysician2` | i18n.ts | Latest guidelines for hypertension medication | 🔴 |
| 34 | `egPhysician3` | i18n.ts | Managing fever in children | 🔴 |
| 35 | `egStudent1` | i18n.ts | What are the Berlin criteria for ARDS? | 🔴 |
| 36 | `egStudent2` | i18n.ts | Differential diagnosis of acute chest pain | 🔴 |
| 37 | `egStudent3` | i18n.ts | Antibiotic spectrum comparison chart | 🔴 |
| 38 | `onboardingPrivacyOnDevice` | i18n-ui.ts | Your workplace, role & language stay on this device | ⚪ |
| 39 | `onboardingPrivacyNotRecorded` | i18n-ui.ts | We never use your queries to train AI | ⚪ |

⚪ generic (lowest priority): #1, 4–7, 9–11*, 15, 16, 22–25, 38, 39 (\*9–11 are 🟡 — common clinical role nouns; verify but not specialised).
🔴 specialised (review first): #8, 12–14, 17–21, 26–37.

---

## Table B — per-cell status grid (reviewer fills in)

Mark each cell: `☐` not reviewed · `✓` reviewed, OK as-is · `✏️` corrected in source file (add a Notes line).

| # | Key | th | ar | hi | bn | he | vi | Notes |
|---|-----|----|----|----|----|----|----|-------|
| 1 | heroChip1 | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 2 | heroChip2 | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 3 | heroChip3 | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 4 | onboardingWorkplaceCommunity | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 5 | onboardingWorkplaceHospital | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 6 | onboardingWorkplaceStudent | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 7 | onboardingWorkplaceResearch | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 8 | onboardingHospitalNudge | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 9 | onboardingRolePhysician | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 10 | onboardingRolePharmacist | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 11 | onboardingRoleNurse | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 12 | onboardingRolePT | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 13 | onboardingRoleOT | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 14 | onboardingRoleSLP | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 15 | onboardingRoleOtherClinical | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 16 | onboardingRoleOtherHospital | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 17 | onboardingRoleMedStudent | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 18 | onboardingRolePharmStudent | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 19 | onboardingRoleNursingStudent | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 20 | onboardingRoleResident | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 21 | onboardingRoleIntern | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 22 | onboardingRoleOtherStudent | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 23 | onboardingRoleResearcher | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 24 | onboardingRoleOtherResearch | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 25 | onboardingRoleOther | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 26 | egPharmacist1 | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 27 | egPharmacist2 | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 28 | egPharmacist3 | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 29 | egNurse1 | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 30 | egNurse2 | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 31 | egNurse3 | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 32 | egPhysician1 | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 33 | egPhysician2 | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 34 | egPhysician3 | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 35 | egStudent1 | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 36 | egStudent2 | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 37 | egStudent3 | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 38 | onboardingPrivacyOnDevice | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| 39 | onboardingPrivacyNotRecorded | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |

---

## After review

Corrections are edited directly in `utils/i18n.ts` / `utils/i18n-ui.ts`, then shipped as
an i18n-only redeploy (no logic/backend change). When all 234 cells are `✓`/`✏️`, this
checklist is done — remove the three superseded BACKLOG flags (hero-chip review,
PHASE-D onboarding, §3.3) and close this gate.
