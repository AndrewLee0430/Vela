import { useLang } from '../utils/LangContext';
import { getUI } from '../utils/i18n-ui';

interface PHIWarningProps {
    detail: string;
    suggestion: string;
    onDismiss?: () => void;
}

export default function PHIWarning({ detail, suggestion, onDismiss }: PHIWarningProps) {
    const { lang } = useLang();
    const ui = getUI(lang);
    return (
        <div className="rounded-xl p-4 mb-4" style={{
            background: 'rgb(var(--color-danger) / 0.08)',
            border: '1px solid rgb(var(--color-danger) / 0.25)',
        }}>
            <div className="flex items-start gap-3">
                <span className="text-base mt-0.5" style={{ color: 'rgb(var(--color-danger))' }}>&#x1F512;</span>
                <div className="flex-1">
                    <p className="text-sm font-semibold mb-1" style={{ color: 'rgb(var(--color-danger-soft))' }}>
                        {ui.phiDetected}
                    </p>
                    <p className="text-sm mb-2" style={{ color: 'rgb(var(--color-danger-soft) / 0.85)' }}>
                        {detail}
                    </p>
                    <p className="text-xs" style={{ color: 'rgb(var(--color-danger-soft) / 0.65)' }}>
                        {suggestion}
                    </p>
                </div>
                {onDismiss && (
                    <button
                        onClick={onDismiss}
                        className="text-sm px-2 py-0.5 rounded transition-colors"
                        style={{ color: 'rgb(var(--color-danger-soft) / 0.6)' }}
                        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = 'rgb(var(--color-danger-soft))'; }}
                        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = 'rgb(var(--color-danger-soft) / 0.6)'; }}
                    >
                        &times;
                    </button>
                )}
            </div>
        </div>
    );
}
