interface PHIWarningProps {
    detail: string;
    suggestion: string;
    onDismiss?: () => void;
}

export default function PHIWarning({ detail, suggestion, onDismiss }: PHIWarningProps) {
    return (
        <div className="rounded-xl p-4 mb-4" style={{
            background: 'rgba(239, 68, 68, 0.08)',
            border: '1px solid rgba(239, 68, 68, 0.25)',
        }}>
            <div className="flex items-start gap-3">
                <span className="text-base mt-0.5" style={{ color: '#ef4444' }}>&#x1F512;</span>
                <div className="flex-1">
                    <p className="text-sm font-semibold mb-1" style={{ color: '#fca5a5' }}>
                        Personal information detected
                    </p>
                    <p className="text-sm mb-2" style={{ color: 'rgba(252, 165, 165, 0.85)' }}>
                        {detail}
                    </p>
                    <p className="text-xs" style={{ color: 'rgba(252, 165, 165, 0.65)' }}>
                        {suggestion}
                    </p>
                </div>
                {onDismiss && (
                    <button
                        onClick={onDismiss}
                        className="text-sm px-2 py-0.5 rounded transition-colors"
                        style={{ color: 'rgba(252, 165, 165, 0.6)' }}
                        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = '#fca5a5'; }}
                        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = 'rgba(252, 165, 165, 0.6)'; }}
                    >
                        &times;
                    </button>
                )}
            </div>
        </div>
    );
}
