import { useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { LANGUAGES, type LangCode } from '../utils/i18n';
import { useLang } from '../utils/LangContext';
import { getUI } from '../utils/i18n-ui';
import { readRaw, setWorkplace, setRole, setWorkLanguage, setLocale } from '../utils/userContext';
import { COUNTRY_CODES, type LocaleSetting } from '../utils/country';
import { WORKPLACES, ROLES_BY_WORKPLACE, FALLBACK_ROLES } from '../utils/contextOptions';
import { postContextHash } from '../utils/contextSync';

// 在地差異 b1 country selector — native endonyms (language-neutral, mirrors the language
// selector's native labels), so the 6 options need no per-locale i18n keys.
const NATIVE_COUNTRY_NAMES: Record<(typeof COUNTRY_CODES)[number], string> = {
  TW: '台灣 (Taiwan)',
  JP: '日本 (Japan)',
  KR: '대한민국 (Korea)',
  SG: 'Singapore',
  MY: 'Malaysia',
  TH: 'ประเทศไทย (Thailand)',
};

// PRD §4.3 — Settings "My Context" tab. Signed-in surface (free OR Pro). Edits
// write THROUGH utils/userContext.ts (no parallel writer); language reuses
// useLang().setLang → PHASE C dual-write. On save, free users write locally only;
// Pro users additionally sync the hash via contextSync (silent, Pro-gated).
export default function MyContextTab() {
  const { lang, setLang } = useLang();
  const { getToken } = useAuth();
  const ui = getUI(lang);

  const init = readRaw();
  const [workplace, setWp] = useState<string | null>(init.workplace ?? null);
  const [role, setRoleState] = useState<string | null>(init.role ?? null);
  const [langSel, setLangSel] = useState<LangCode>(
    (init.work_language as LangCode | undefined) ?? lang
  );
  const [locale, setLocaleSel] = useState<LocaleSetting | null>(
    (init.locale as LocaleSetting | undefined) ?? null
  );
  const [saved, setSaved] = useState(false);
  // Country-selector labels: en/zh-TW real, other UI locales fall back to en (b1 scope).
  const enUI = getUI('en');
  const countryLabel = ui.myContextCountry ?? enUI.myContextCountry ?? 'Country / region';
  const countryOtherLabel = ui.myContextCountryOther ?? enUI.myContextCountryOther ?? 'Other (use international sources)';

  const roleOptions = workplace ? ROLES_BY_WORKPLACE[workplace] ?? FALLBACK_ROLES : FALLBACK_ROLES;

  const onWorkplace = (v: string) => {
    setWp(v);
    // drop the selected role if it no longer belongs to the new workplace
    const stillValid = (ROLES_BY_WORKPLACE[v] ?? FALLBACK_ROLES).some((r) => r.value === role);
    if (!stillValid) setRoleState(null);
    setSaved(false);
  };

  const save = async () => {
    await setWorkplace(workplace);
    await setRole(role);
    setLang(langSel);                // live UI switch + vela_lang (PHASE C dual-write)
    await setWorkLanguage(langSel);  // awaited so the cached hash is fresh before POST
    setLocale(locale);               // COUNTRY (b1) — persisted to vela_user_context.locale
    void postContextHash(() => getToken({ skipCache: true })); // Pro-only, silent (posts locale too)
    setSaved(true);
  };

  return (
    <div className="max-w-md">
      {/* Workplace */}
      <p className="text-sm font-semibold text-text mb-2">{ui.myContextWorkplace}</p>
      <div className="grid grid-cols-2 gap-2 mb-5">
        {WORKPLACES.map(({ value, icon, labelKey }) => {
          const selected = workplace === value;
          return (
            <button
              key={value}
              type="button"
              onClick={() => onWorkplace(value)}
              className={`flex items-center gap-2 px-3 py-2.5 rounded-lg border text-sm transition-all ${selected ? 'border-brand bg-brand/10 text-brand' : 'border-text/10 bg-text/[0.04] text-text/70 hover:bg-text/8 hover:border-text/20'}`}
            >
              <span className="text-lg">{icon}</span>
              <span className="font-medium">{ui[labelKey]}</span>
            </button>
          );
        })}
      </div>

      {/* Role */}
      <p className="text-sm font-semibold text-text mb-2">{ui.myContextRole}</p>
      <select
        aria-label={ui.myContextRole}
        value={role ?? ''}
        onChange={(e) => { setRoleState(e.target.value || null); setSaved(false); }}
        className="w-full bg-text/[0.05] border border-text/15 text-text/80 rounded-lg px-3 py-2.5 text-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-brand/30 mb-5"
      >
        <option value="">{ui.myContextSelectPlaceholder}</option>
        {roleOptions.map(({ value, labelKey }) => (
          <option key={value} value={value}>{ui[labelKey]}</option>
        ))}
      </select>

      {/* Answer language */}
      <p className="text-sm font-semibold text-text mb-2">{ui.myContextLanguage}</p>
      <select
        aria-label={ui.myContextLanguage}
        value={langSel}
        onChange={(e) => { setLangSel(e.target.value as LangCode); setSaved(false); }}
        className="w-full bg-text/[0.05] border border-text/15 text-text/80 rounded-lg px-3 py-2.5 text-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-brand/30 mb-6"
      >
        {LANGUAGES.map((l) => (
          <option key={l.code} value={l.code}>{l.label} ({l.code})</option>
        ))}
      </select>

      {/* Country / region (在地差異 b1) — selects WHICH authorities the regional-differences
          panel points to; independent of the answer language above. */}
      <p className="text-sm font-semibold text-text mb-2">{countryLabel}</p>
      <select
        aria-label={countryLabel}
        value={locale ?? ''}
        onChange={(e) => { setLocaleSel((e.target.value || null) as LocaleSetting | null); setSaved(false); }}
        className="w-full bg-text/[0.05] border border-text/15 text-text/80 rounded-lg px-3 py-2.5 text-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-brand/30 mb-6"
      >
        <option value="">{ui.myContextSelectPlaceholder}</option>
        {COUNTRY_CODES.map((c) => (
          <option key={c} value={c}>{NATIVE_COUNTRY_NAMES[c]}</option>
        ))}
        <option value="OTHER">{countryOtherLabel}</option>
      </select>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={save}
          className="text-sm font-semibold px-6 py-2 rounded-lg transition-all"
          style={{ background: 'rgb(var(--color-brand))', color: '#0a1628' }}
        >
          {ui.myContextSave}
        </button>
        {saved && (
          <span className="text-sm" style={{ color: 'rgb(var(--color-success))' }}>
            ✓ {ui.myContextSaved}
          </span>
        )}
      </div>
    </div>
  );
}
