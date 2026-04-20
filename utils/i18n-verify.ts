// utils/i18n-verify.ts — Verify interaction-summary translations (PRD § 2.9 follow-up).
// Coverage: 7/16 languages in full (en + zh-TW + zh-CN + ja + ko + es + de).
// Other 9 languages fall back to en; full pass deferred to Phase 1A i18n mop-up.
//
// Severity label resolution chain (both badge and breakdown):
//   1. backend `severity_label` (LLM-generated, passed in via BreakdownEntry.label
//      or directly to getSeverityLabel via caller)
//   2. this file's per-language severityLabels dict (frontend fallback)
//   3. canonical English enum ("Critical" / "Major" / "Moderate" / "Minor")
//
// Plural handling: Spanish uses +s suffix rule on resolved label; other
// languages use invariant labels (CJK) or rely on backend/dict giving the
// right base form.

import type { LangCode } from './i18n';

export interface BreakdownEntry {
  canonical: string;    // "Critical" | "Major" | "Moderate" | "Minor"
  label?: string;       // backend-localized from DrugInteraction.severity_label
  count: number;
}

interface VerifyI18n {
  severityLabels: Record<string, string>;     // single-interaction badge + breakdown
  riskLevelLabels: Record<string, string>;    // top-of-card overall risk badge; includes Low/Unknown
  formatSummary: (total: number, breakdown: BreakdownEntry[]) => string;
}

function resolveLabel(info: VerifyI18n, entry: BreakdownEntry): string {
  return entry.label || info.severityLabels[entry.canonical] || entry.canonical;
}

// ─── en ────────────────────────────────────────────────────────────────
const EN_SEV = { Critical: 'Critical', Major: 'Major', Moderate: 'Moderate', Minor: 'Minor' };
const EN: VerifyI18n = {
  severityLabels: EN_SEV,
  riskLevelLabels: { ...EN_SEV, Low: 'Low', Unknown: 'Unknown' },
  formatSummary(total, breakdown) {
    const parts = breakdown.map(b => `${b.count} ${resolveLabel(this, b)}`).join(', ');
    return `Found ${total} interaction${total > 1 ? 's' : ''}: ${parts}`;
  },
};

// ─── zh-TW (Taiwan / HK) ───────────────────────────────────────────────
const ZH_TW_SEV = { Critical: '危急', Major: '嚴重', Moderate: '中度', Minor: '輕度' };
const ZH_TW: VerifyI18n = {
  severityLabels: ZH_TW_SEV,
  riskLevelLabels: { ...ZH_TW_SEV, Low: '低', Unknown: '未知' },
  formatSummary(total, breakdown) {
    const parts = breakdown.map(b => `${b.count} ${resolveLabel(this, b)}`).join('、');
    return `發現 ${total} 筆交互作用:${parts}`;
  },
};

// ─── zh-CN (Mainland / Singapore) ──────────────────────────────────────
// 「项」measure word per user spec. Severity vocab: 严重 / 重度 / 中度 / 轻度.
// Cross-variant consistency: zh-CN「严重」maps to Critical, matching zh-TW
//「嚴重」=Major would diverge — see Follow-up 1 note: user chose to align
// zh-CN Critical with the plain-simplified reading of Critical ("严重"=severe),
// and Major=重度 (度 = degree) to sit below. Reviewers should be aware
// there's still a zh-TW「嚴重」(Major) vs zh-CN「严重」(Critical) semantic
// offset at Critical/Major boundary — flagged for native zh-CN review.
const ZH_CN_SEV = { Critical: '严重', Major: '重度', Moderate: '中度', Minor: '轻度' };
const ZH_CN: VerifyI18n = {
  severityLabels: ZH_CN_SEV,
  riskLevelLabels: { ...ZH_CN_SEV, Low: '低', Unknown: '未知' },
  formatSummary(total, breakdown) {
    const parts = breakdown.map(b => `${b.count} ${resolveLabel(this, b)}`).join('、');
    return `发现 ${total} 项相互作用:${parts}`;
  },
};

// ─── ja ────────────────────────────────────────────────────────────────
// Standard Japanese pharmacology severity grading: 重篤 / 重度 / 中等度 / 軽度.
// (重篤 preferred over 重度 for Critical to keep distinct from Major.)
// Breakdown order: label + count + 件 (Japanese measure-word convention).
const JA_SEV = { Critical: '重篤', Major: '重度', Moderate: '中等度', Minor: '軽度' };
const JA: VerifyI18n = {
  severityLabels: JA_SEV,
  riskLevelLabels: { ...JA_SEV, Low: '低度', Unknown: '不明' },
  formatSummary(total, breakdown) {
    const parts = breakdown.map(b => `${resolveLabel(this, b)} ${b.count}件`).join('、');
    return `${total}件の相互作用:${parts}`;
  },
};

// ─── ko ────────────────────────────────────────────────────────────────
// Standard Korean medical severity grading: 중증 / 중등증 / 경증.
// Critical=위험 per user spec; 치명적 (lethal) may be more medically precise —
// flag for native ko medical reviewer.
// Breakdown order: label + count + 건 (Korean measure-word convention).
const KO_SEV = { Critical: '위험', Major: '중증', Moderate: '중등증', Minor: '경증' };
const KO: VerifyI18n = {
  severityLabels: KO_SEV,
  riskLevelLabels: { ...KO_SEV, Low: '낮음', Unknown: '미상' },
  formatSummary(total, breakdown) {
    const parts = breakdown.map(b => `${resolveLabel(this, b)} ${b.count}건`).join(', ');
    return `${total}건의 상호작용 발견: ${parts}`;
  },
};

// ─── es ────────────────────────────────────────────────────────────────
// severity: feminine to agree with `interacción` (f) — crítica/s, grave/s,
// moderada/s, leve/s. Plural = +s rule, applied to backend or dict label.
// riskLevel: masculine to agree with `riesgo` (m) — crítico, grave, moderado,
// leve, bajo, desconocido. Two separate dicts because gender differs.
const ES_SEV = { Critical: 'crítica', Major: 'grave', Moderate: 'moderada', Minor: 'leve' };
const ES: VerifyI18n = {
  severityLabels: ES_SEV,
  riskLevelLabels: {
    Critical: 'crítico', Major: 'grave', Moderate: 'moderado', Minor: 'leve',
    Low: 'bajo', Unknown: 'desconocido',
  },
  formatSummary(total, breakdown) {
    const parts = breakdown.map(b => {
      const base = resolveLabel(this, b);
      const label = b.count > 1 ? base + 's' : base;
      return `${b.count} ${label}`;
    }).join(', ');
    const head = total === 1 ? 'Encontrada 1 interacción' : `Encontradas ${total} interacciones`;
    return `${head}: ${parts}`;
  },
};

// ─── de ────────────────────────────────────────────────────────────────
// Wechselwirkung is the standard medical term for drug interaction
// (Interaktion is colloquial). Plural: Wechselwirkung → Wechselwirkungen.
// German adjectives used as bare short-forms don't inflect for noun gender
// in this standalone UI context, so severity and riskLevel share the same 4.
const DE_SEV = { Critical: 'kritisch', Major: 'schwerwiegend', Moderate: 'mäßig', Minor: 'leicht' };
const DE: VerifyI18n = {
  severityLabels: DE_SEV,
  riskLevelLabels: { ...DE_SEV, Low: 'niedrig', Unknown: 'unbekannt' },
  formatSummary(total, breakdown) {
    const parts = breakdown.map(b => `${b.count} ${resolveLabel(this, b)}`).join(', ');
    const head = total === 1 ? '1 Wechselwirkung' : `${total} Wechselwirkungen`;
    return `${head} gefunden: ${parts}`;
  },
};

// ─── Registry ──────────────────────────────────────────────────────────
const I18N: Partial<Record<LangCode, VerifyI18n>> = {
  en: EN,
  'zh-TW': ZH_TW,
  'zh-CN': ZH_CN,
  ja: JA,
  ko: KO,
  es: ES,
  de: DE,
};

function pick(lang: LangCode): VerifyI18n {
  return I18N[lang] || EN;
}

export function formatInteractionSummary(
  lang: LangCode,
  total: number,
  breakdown: BreakdownEntry[]
): string {
  return pick(lang).formatSummary(total, breakdown);
}

/**
 * Resolve severity label for single-item display (e.g. card badge) when
 * backend `severity_label` is missing. Badge caller should still prefer
 * backend label:  `interaction.severity_label || getSeverityLabel(lang, interaction.severity)`
 */
export function getSeverityLabel(lang: LangCode, canonicalSeverity: string): string {
  const info = pick(lang);
  return info.severityLabels[canonicalSeverity] || canonicalSeverity;
}

/**
 * Resolve risk-level label for top-of-card overall risk badge when backend
 * `risk_level_label` is missing. Covers Critical/Major/Moderate/Minor plus
 * Low/Unknown (severity dict lacks these). Caller chain:
 *   `result.risk_level_label || getRiskLevelLabel(lang, result.risk_level)`
 */
export function getRiskLevelLabel(lang: LangCode, canonicalRiskLevel: string): string {
  const info = pick(lang);
  return info.riskLevelLabels[canonicalRiskLevel] || canonicalRiskLevel;
}
