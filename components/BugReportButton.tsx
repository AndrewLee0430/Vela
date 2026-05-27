"use client";

import { useEffect, useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { useLang } from '../utils/LangContext';
import { getBugReport } from '../utils/i18n-bug-report';
import { track, getCurrentQueryId } from '../utils/analytics';

type IssueType = 'inaccurate' | 'ui_error' | 'feature_request' | 'other';
type Status = 'idle' | 'submitting' | 'success' | 'error';

export default function BugReportButton() {
  const { getToken, isSignedIn } = useAuth();
  const { lang } = useLang();
  const t = getBugReport(lang);

  const [open, setOpen] = useState(false);
  const [issueType, setIssueType] = useState<IssueType>('inaccurate');
  const [description, setDescription] = useState('');
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<Status>('idle');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeModal();
    };
    window.addEventListener('keydown', onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener('keydown', onKey);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const openModal = () => {
    setOpen(true);
    setStatus('idle');
    setErrorMsg(null);
    try {
      track('bug_report_opened', {
        page: typeof window !== 'undefined' ? window.location.pathname : null,
        trigger: 'fab',
      });
    } catch {}
  };

  const closeModal = () => {
    if (status === 'submitting') return;
    setOpen(false);
    // Reset only after close animation-free state flip
    setTimeout(() => {
      setIssueType('inaccurate');
      setDescription('');
      setEmail('');
      setStatus('idle');
      setErrorMsg(null);
    }, 100);
  };

  const submit = async () => {
    const trimmed = description.trim();
    if (trimmed.length === 0) {
      setErrorMsg(t.errorTooShort);
      return;
    }
    setStatus('submitting');
    setErrorMsg(null);

    const query_id = getCurrentQueryId();
    const page_url = typeof window !== 'undefined' ? window.location.pathname : null;

    try {
      let token: string | null = null;
      if (isSignedIn) {
        try { token = await getToken({ skipCache: true }); } catch {}
      }
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/bug-report`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          issue_type: issueType,
          description: trimmed.slice(0, 2000),
          email: email.trim() || null,
          query_id,
          page_url,
          locale: lang,
        }),
      });

      if (res.status === 429) {
        setStatus('error');
        setErrorMsg(t.errorRateLimit);
        return;
      }
      if (!res.ok) {
        setStatus('error');
        setErrorMsg(t.errorGeneric);
        return;
      }

      try {
        track('bug_report_submitted', {
          issue_type: issueType,
          has_email: Boolean(email.trim()),
          has_query_id: Boolean(query_id),
          locale: lang,
        });
      } catch {}

      setStatus('success');
    } catch {
      setStatus('error');
      setErrorMsg(t.errorGeneric);
    }
  };

  return (
    <>
      {/* Floating Action Button — bottom-24 on mobile to clear MobileNav, bottom-5 desktop */}
      <button
        type="button"
        onClick={openModal}
        aria-label={t.fabTooltip}
        title={t.fabTooltip}
        className="fixed right-5 bottom-24 md:bottom-5 z-40 flex items-center justify-center rounded-full shadow-lg transition-transform hover:scale-105 active:scale-95 bg-slate-600 hover:bg-slate-700 text-white border border-text/15"
        style={{
          width: '3rem',
          height: '3rem',
        }}
      >
        {/* Chat bubble icon */}
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
        </svg>
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-end md:items-center justify-center p-4"
          style={{ background: 'rgba(0,0,0,0.7)' }}
          onClick={closeModal}
        >
          <div
            className="relative w-full max-w-lg rounded-2xl p-6 md:p-8 border border-text/10"
            style={{ background: '#0f1f3d', maxHeight: 'calc(100vh - 2rem)', overflowY: 'auto' }}
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              onClick={closeModal}
              disabled={status === 'submitting'}
              aria-label={t.closeBtn}
              className="absolute top-4 right-4 text-gray-400 hover:text-white text-xl disabled:opacity-50"
            >
              ✕
            </button>

            {status === 'success' ? (
              <div className="text-center py-6">
                <div className="text-4xl mb-3">💬</div>
                <h2 className="text-xl font-bold text-white mb-2">{t.thanksTitle}</h2>
                <p className="text-sm text-text/70">{t.thanksBody}</p>
                <button
                  type="button"
                  onClick={closeModal}
                  className="mt-6 py-2 px-6 rounded-xl font-semibold text-white"
                  style={{ background: '#1e4a8a' }}
                >
                  {t.closeBtn}
                </button>
              </div>
            ) : (
              <>
                <div className="mb-5">
                  <h2 className="text-xl font-bold text-white mb-1">{t.modalTitle}</h2>
                  <p className="text-sm text-text/60">{t.modalSubtitle}</p>
                </div>

                <label className="block text-xs font-semibold mb-1 text-text/80">{t.issueTypeLabel}</label>
                <select
                  value={issueType}
                  onChange={(e) => setIssueType(e.target.value as IssueType)}
                  disabled={status === 'submitting'}
                  className="w-full mb-4 rounded-lg px-3 py-2 text-sm text-white bg-text/8 border border-text/15"
                >
                  <option value="inaccurate" style={{ background: '#0f1f3d' }}>{t.issueTypeInaccurate}</option>
                  <option value="ui_error" style={{ background: '#0f1f3d' }}>{t.issueTypeUiError}</option>
                  <option value="feature_request" style={{ background: '#0f1f3d' }}>{t.issueTypeFeatureRequest}</option>
                  <option value="other" style={{ background: '#0f1f3d' }}>{t.issueTypeOther}</option>
                </select>

                <label className="block text-xs font-semibold mb-1 text-text/80">{t.descriptionLabel}</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value.slice(0, 2000))}
                  placeholder={t.descriptionPlaceholder}
                  disabled={status === 'submitting'}
                  rows={5}
                  className="w-full mb-1 rounded-lg px-3 py-2 text-sm text-white resize-y bg-text/8 border border-text/15"
                />
                <p className="text-xs mb-4 text-text/40">
                  {description.length} / 2000 · {t.descriptionHint}
                </p>

                <label className="block text-xs font-semibold mb-1 text-text/80">{t.emailLabel}</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value.slice(0, 200))}
                  placeholder={t.emailPlaceholder}
                  disabled={status === 'submitting'}
                  className="w-full rounded-lg px-3 py-2 text-sm text-white bg-text/8 border border-text/15"
                />
                <p className="text-xs mb-4 text-text/40">{t.emailHint}</p>

                {errorMsg && (
                  <p className="text-xs mb-3 px-3 py-2 rounded-lg" style={{ background: 'rgb(var(--color-danger) / 0.1)', color: 'rgb(var(--color-danger))' }}>
                    {errorMsg}
                  </p>
                )}

                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={closeModal}
                    disabled={status === 'submitting'}
                    className="flex-1 py-2 rounded-xl text-sm font-medium bg-text/6 text-text/85 border border-text/12"
                  >
                    {t.cancelBtn}
                  </button>
                  <button
                    type="button"
                    onClick={submit}
                    disabled={status === 'submitting' || description.trim().length === 0}
                    className="flex-1 py-2 rounded-xl text-sm font-semibold text-white disabled:opacity-60"
                    style={{ background: status === 'submitting' ? '#cc5533' : '#ff6b4a' }}
                  >
                    {status === 'submitting' ? t.submittingBtn : t.submitBtn}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}
