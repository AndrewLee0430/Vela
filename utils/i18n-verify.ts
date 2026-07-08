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
  // Option-C honesty (DailyMed Verify surface, 2026-07-08): the AI-severity marker
  // shown AT the badge eyeline, the localized "Source:" prefix, and the three
  // attribution captions that REPLACE the raw backend `source` display string.
  provenance: {
    aiSeverityNote: string;   // beside/under the severity badge — severity is Vela AI, not label-stated
    sourcePrefix: string;     // localized "Source:"
    dailymed: string;         // interaction text cited from DailyMed label; severity = Vela AI
    openfda: string;          // AI analysis of FDA label
    nolabel: string;          // clinical knowledge, no FDA label available
  };
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
  provenance: {
    aiSeverityNote: 'Vela AI-assessed (not label-stated)',
    sourcePrefix: 'Source:',
    dailymed: 'Interaction text cited from DailyMed label; severity is Vela AI',
    openfda: 'AI analysis of FDA label',
    nolabel: 'Clinical knowledge (no FDA label available)',
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
  provenance: {
    aiSeverityNote: 'Vela AI 研判（非仿單標示）',
    sourcePrefix: '來源：',
    dailymed: '交互作用內文引用自 DailyMed 仿單；嚴重程度為 Vela AI 研判',
    openfda: 'Vela AI 分析 FDA 仿單',
    nolabel: '臨床知識（無 FDA 仿單資料）',
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
  provenance: {
    aiSeverityNote: 'Vela AI 研判（非说明书标示）',
    sourcePrefix: '来源：',
    dailymed: '相互作用内容引用自 DailyMed 说明书；严重程度为 Vela AI 研判',
    openfda: 'Vela AI 分析 FDA 说明书',
    nolabel: '临床知识（无 FDA 说明书数据）',
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
  provenance: {
    aiSeverityNote: 'Vela AI 推定（添付文書の記載ではありません）',
    sourcePrefix: '出典：',
    dailymed: '相互作用の記述は DailyMed 添付文書から引用；重症度は Vela AI の推定',
    openfda: 'FDA 添付文書の Vela AI 分析',
    nolabel: '臨床知識（FDA 添付文書なし）',
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
  provenance: {
    aiSeverityNote: 'Vela AI 판단（라벨 명시 아님）',
    sourcePrefix: '출처:',
    dailymed: '상호작용 내용은 DailyMed 라벨에서 인용; 중증도는 Vela AI 판단',
    openfda: 'FDA 라벨의 Vela AI 분석',
    nolabel: '임상 지식（FDA 라벨 없음）',
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
  provenance: {
    aiSeverityNote: 'Evaluado por Vela AI (no indicado en la etiqueta)',
    sourcePrefix: 'Fuente:',
    dailymed: 'Texto de interacción citado de la etiqueta DailyMed; gravedad evaluada por Vela AI',
    openfda: 'Análisis por IA de la etiqueta de la FDA',
    nolabel: 'Conocimiento clínico (sin etiqueta de la FDA)',
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
  provenance: {
    aiSeverityNote: 'Von Vela AI eingeschätzt (nicht laut Etikett)',
    sourcePrefix: 'Quelle:',
    dailymed: 'Interaktionstext aus DailyMed-Etikett zitiert; Schweregrad von Vela AI',
    openfda: 'KI-Analyse des FDA-Etiketts',
    nolabel: 'Klinisches Wissen (kein FDA-Etikett verfügbar)',
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

// ─── Option-C attribution (DailyMed Verify surface) ──────────────────────
// The STABLE attribution_kind enum emitted by the backend (DrugInteraction.attribution_kind,
// set in api/server.py). The frontend renders honesty captions from THIS durable key — NOT
// from substring-matching the display `source` string (that wording is Option-C copy and may
// be tuned; matching it would silently break the honesty marker with no test catching it).
export const ATTRIBUTION_KINDS = ['dailymed_grounded', 'openfda_analysis', 'no_label'] as const;
export type AttributionKind = typeof ATTRIBUTION_KINDS[number];

// attribution_kind → the provenance caption key. Kept exhaustive: the guard test
// (tests/test-verify-attribution.mjs) iterates ATTRIBUTION_KINDS and asserts each resolves
// to a non-empty caption in every defined locale, so an unmapped/renamed kind fails LOUD.
const KIND_TO_CAPTION: Record<AttributionKind, keyof VerifyI18n['provenance']> = {
  dailymed_grounded: 'dailymed',
  openfda_analysis: 'openfda',
  no_label: 'nolabel',
};

/**
 * Localized attribution caption from the STABLE attribution_kind. An absent/unknown kind
 * (older payload, unexpected value) falls back to the AI-analysis caption — a SAFE default
 * that STILL shows an honesty marker and NEVER reads as label-stated.
 */
export function getSourceCaptionByKind(lang: LangCode, kind: string | null | undefined): string {
  const captionKey = KIND_TO_CAPTION[(kind || '') as AttributionKind] || 'openfda';
  return pick(lang).provenance[captionKey];
}

/** The AI-severity marker shown at the badge eyeline (severity is Vela AI, not label-stated). */
export function getAiSeverityNote(lang: LangCode): string {
  return pick(lang).provenance.aiSeverityNote;
}

/** Localized "Source:" prefix. */
export function getSourcePrefix(lang: LangCode): string {
  return pick(lang).provenance.sourcePrefix;
}
