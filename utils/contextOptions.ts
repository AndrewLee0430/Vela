// utils/contextOptions.ts
//
// Single source of truth for the §3.2 workplace / role option sets + the G7
// role_category mapping. Shared by components/OnboardingWizard.tsx (PHASE D) and
// components/MyContextTab.tsx (PHASE E Settings) so the two surfaces never drift.
// Role VALUE strings are unchanged from PHASE D — do not edit them here without a
// §3.1/§3.2 docs reconciliation (see TECH_DEBT 2026-06-08).

import { LANGUAGES, type LangCode } from "./i18n";
import { getUI } from "./i18n-ui";

export type ContextUIKey = keyof ReturnType<typeof getUI>;

export const WORKPLACES: { value: string; icon: string; labelKey: ContextUIKey }[] = [
  { value: "community", icon: "🏥", labelKey: "onboardingWorkplaceCommunity" },
  { value: "hospital", icon: "🏩", labelKey: "onboardingWorkplaceHospital" },
  { value: "student", icon: "🎓", labelKey: "onboardingWorkplaceStudent" },
  { value: "research", icon: "🔬", labelKey: "onboardingWorkplaceResearch" },
];

export const ROLES_BY_WORKPLACE: Record<string, { value: string; labelKey: ContextUIKey }[]> = {
  community: [
    { value: "physician", labelKey: "onboardingRolePhysician" },
    { value: "pharmacist", labelKey: "onboardingRolePharmacist" },
    { value: "nurse", labelKey: "onboardingRoleNurse" },
    { value: "physical_therapist", labelKey: "onboardingRolePT" },
    { value: "occupational_therapist", labelKey: "onboardingRoleOT" },
    { value: "speech_language_pathologist", labelKey: "onboardingRoleSLP" },
    { value: "other_clinical", labelKey: "onboardingRoleOtherClinical" },
  ],
  hospital: [
    { value: "hospital_physician", labelKey: "onboardingRolePhysician" },
    { value: "hospital_pharmacist", labelKey: "onboardingRolePharmacist" },
    { value: "hospital_nurse", labelKey: "onboardingRoleNurse" },
    { value: "other_hospital", labelKey: "onboardingRoleOtherHospital" },
  ],
  student: [
    { value: "medical_student", labelKey: "onboardingRoleMedStudent" },
    { value: "pharmacy_student", labelKey: "onboardingRolePharmStudent" },
    { value: "nursing_student", labelKey: "onboardingRoleNursingStudent" },
    { value: "resident", labelKey: "onboardingRoleResident" },
    { value: "intern", labelKey: "onboardingRoleIntern" },
    { value: "other_student", labelKey: "onboardingRoleOtherStudent" },
  ],
  research: [
    { value: "researcher", labelKey: "onboardingRoleResearcher" },
    { value: "other_research", labelKey: "onboardingRoleOtherResearch" },
  ],
};

export const FALLBACK_ROLES: { value: string; labelKey: ContextUIKey }[] = [
  { value: "other", labelKey: "onboardingRoleOther" },
];

export function nearestLang(): LangCode {
  if (typeof navigator === "undefined") return "en";
  const nav = navigator.language || "en";
  if (LANGUAGES.some((l) => l.code === nav)) return nav as LangCode;
  const primary = nav.split("-")[0];
  const m = LANGUAGES.find((l) => l.code.split("-")[0] === primary);
  return (m?.code as LangCode) ?? "en";
}

// ── role_category (PRD §3.1 v1.5 G7, L1013-1024) ──────────────────────────────
// Applied to the ACTUAL §3.2/PHASE-D role values. Note: §3.2 added therapist
// roles (PT/OT/SLP → clinical) and pharmacy_student/nursing_student (→ student by
// the bucket's intent) that the G7 literal enumeration predates — see TECH_DEBT.
export type RoleCategory = "clinical" | "research" | "student" | "other";

const CLINICAL_ROLES = new Set([
  "physician", "pharmacist", "nurse",
  "physical_therapist", "occupational_therapist", "speech_language_pathologist",
  "hospital_physician", "hospital_pharmacist", "hospital_nurse",
]);
const STUDENT_ROLES = new Set([
  "medical_student", "pharmacy_student", "nursing_student", "resident", "intern",
]);

/**
 * Map a granular role → its analytics bucket. Returns null for an unset role so
 * the caller OMITS role_category from identify() (do not fabricate). A set-but-
 * unrecognized value falls to "other". All `other_*` values → "other".
 */
export function roleToCategory(role: string | null | undefined): RoleCategory | null {
  if (!role) return null;
  if (CLINICAL_ROLES.has(role)) return "clinical";
  if (STUDENT_ROLES.has(role)) return "student";
  if (role === "researcher") return "research";
  return "other";
}
