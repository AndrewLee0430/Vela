// utils/i18n-bug-report.ts — PRD 2.4 Bug Report translations.
// Phase 0 coverage: en + zh-TW in full; other 14 languages fall back to en
// (PRD allows progressive i18n rollout; full 16-language pass deferred).

import type { LangCode } from './i18n';

export interface BugReportTranslations {
  fabTooltip: string;           // hover tooltip on the floating button
  modalTitle: string;
  modalSubtitle: string;
  issueTypeLabel: string;
  issueTypeInaccurate: string;  // "答案不準確"
  issueTypeUiError: string;     // "UI 錯誤"
  issueTypeFeatureRequest: string;
  issueTypeOther: string;
  descriptionLabel: string;
  descriptionPlaceholder: string;
  descriptionHint: string;      // "Max 2000 characters"
  emailLabel: string;           // optional email
  emailPlaceholder: string;
  emailHint: string;            // "We only use this if we need to follow up."
  submitBtn: string;
  submittingBtn: string;
  cancelBtn: string;
  closeBtn: string;
  thanksTitle: string;
  thanksBody: string;
  errorGeneric: string;
  errorRateLimit: string;
  errorTooShort: string;
}

const en: BugReportTranslations = {
  fabTooltip: 'Report an issue',
  modalTitle: 'Report an issue',
  modalSubtitle: 'Tell us what went wrong or what you wish Vela could do better.',
  issueTypeLabel: 'What kind of issue?',
  issueTypeInaccurate: 'Answer was inaccurate',
  issueTypeUiError: 'UI / display bug',
  issueTypeFeatureRequest: 'Feature request',
  issueTypeOther: 'Other',
  descriptionLabel: 'Description',
  descriptionPlaceholder: 'What happened? If it was a specific answer, paste what you expected vs. what you got.',
  descriptionHint: 'Up to 2,000 characters.',
  emailLabel: 'Email (optional)',
  emailPlaceholder: 'you@example.com',
  emailHint: "We'll only use this if we need to follow up.",
  submitBtn: 'Send report',
  submittingBtn: 'Sending…',
  cancelBtn: 'Cancel',
  closeBtn: 'Close',
  thanksTitle: 'Thanks for the report',
  thanksBody: "We read every message. We'll reach out only if we need more detail.",
  errorGeneric: 'Could not send. Please try again.',
  errorRateLimit: "You've sent several reports recently — please try again later.",
  errorTooShort: 'Please add a short description before sending.',
};

const zhTW: BugReportTranslations = {
  fabTooltip: '回報問題',
  modalTitle: '回報問題',
  modalSubtitle: '告訴我們哪裡不對,或你希望 Vela 有哪些改進。',
  issueTypeLabel: '問題類型',
  issueTypeInaccurate: '答案不準確',
  issueTypeUiError: 'UI / 顯示錯誤',
  issueTypeFeatureRequest: '功能建議',
  issueTypeOther: '其他',
  descriptionLabel: '描述',
  descriptionPlaceholder: '發生了什麼狀況?如果是針對特定答案,可以貼上你原本期待的答案與實際收到的答案。',
  descriptionHint: '最多 2,000 字。',
  emailLabel: 'Email(選填)',
  emailPlaceholder: 'you@example.com',
  emailHint: '只有在需要進一步釐清時才會聯繫你。',
  submitBtn: '送出',
  submittingBtn: '送出中⋯',
  cancelBtn: '取消',
  closeBtn: '關閉',
  thanksTitle: '感謝你的回報',
  thanksBody: '我們會看每一則回報,若需更多細節再與你聯繫。',
  errorGeneric: '送出失敗,請再試一次。',
  errorRateLimit: '短時間內送出次數已達上限,請稍後再試。',
  errorTooShort: '請先填寫簡短描述。',
};

export function getBugReport(lang: LangCode): BugReportTranslations {
  if (lang === 'zh-TW') return zhTW;
  return en;
}
