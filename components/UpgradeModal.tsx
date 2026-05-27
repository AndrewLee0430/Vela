// components/UpgradeModal.tsx

import { useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { clearPlanCache } from './PlanBadge';
import { useLang } from '../utils/LangContext';
import { getUI } from '../utils/i18n-ui';

interface UpgradeModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const MONTHLY_PRODUCT_ID = "pdt_0NbELHXiGodgawGwVaZ3t";
const YEARLY_PRODUCT_ID  = "pdt_0NbELkno040P4wQSaQaam";

export default function UpgradeModal({ isOpen, onClose }: UpgradeModalProps) {
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { getToken } = useAuth();
  const { lang } = useLang();
  const ui = getUI(lang);

  if (!isOpen) return null;

  const handleUpgrade = async (productId: string, plan: string) => {
    setLoading(plan);
    setError(null);
    try {
      const token = await getToken({ skipCache: true });
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/checkout/dodo`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ product_id: productId }),
      });
      const data = await res.json();
      if (data.payment_link) {
        clearPlanCache();
        window.location.href = data.payment_link;
      } else {
        setError('Unable to start checkout. Please try again.');
      }
    } catch {
      setError('Payment failed. Please try again or contact support@an-tho.com');
    } finally {
      setLoading(null);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.7)' }}
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-md rounded-2xl p-8 border border-text/10"
        style={{ background: '#0f1f3d' }}
        onClick={e => e.stopPropagation()}
      >
        {/* Close */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-white text-xl"
        >
          ✕
        </button>

        {/* Header */}
        <div className="text-center mb-6">
          <div className="text-4xl mb-2">🪸</div>
          <h2 className="text-2xl font-bold text-white mb-1">{ui.upgradeTitle}</h2>
          <p className="text-gray-400 text-sm">{ui.upgradeSubtitle}</p>
        </div>

        {/* Features */}
        <ul className="space-y-2 mb-2">
          {[ui.upgradeFeature1, ui.upgradeFeature2, ui.upgradeFeature3, ui.upgradeFeature4].map((f, i) => (
            <li key={i} className="text-gray-300 text-sm">{f}</li>
          ))}
        </ul>
        <p className="text-xs mb-4 text-text/40">
          *Daily credit limit resets at midnight UTC. See <a href="/terms" target="_blank" className="underline hover:opacity-80">Terms of Service</a>.
        </p>

        {/* Error message */}
        {error && (
          <p className="text-xs text-center mb-3 px-2 py-2 rounded-lg" style={{ background: 'rgba(239,68,68,0.1)', color: '#ef4444' }}>
            {error}
          </p>
        )}

        {/* ToS consent */}
        <p className="text-xs text-center mb-3 text-text/45">
          By upgrading, you agree to our{' '}
          <a href="/terms" target="_blank" className="underline hover:text-white transition-colors">Terms of Service</a>
          {' '}and{' '}
          <a href="/refund" target="_blank" className="underline hover:text-white transition-colors">Refund Policy</a>.
        </p>

        {/* Pricing buttons */}
        <div className="space-y-3">
          <button
            onClick={() => handleUpgrade(MONTHLY_PRODUCT_ID, 'monthly')}
            disabled={!!loading}
            className="w-full py-3 rounded-xl font-semibold text-white transition-all"
            style={{ background: loading === 'monthly' ? '#cc5533' : '#ff6b4a' }}
          >
            {loading === 'monthly' ? ui.redirecting : ui.monthlyBtn}
          </button>

          <button
            onClick={() => handleUpgrade(YEARLY_PRODUCT_ID, 'yearly')}
            disabled={!!loading}
            className="w-full py-3 rounded-xl font-semibold text-white transition-all"
            style={{ background: loading === 'yearly' ? '#1a3a6a' : '#1e4a8a' }}
          >
            {loading === 'yearly' ? ui.redirecting : ui.yearlyBtn}
          </button>
        </div>

        <p className="text-center text-gray-500 text-xs mt-4">
          {ui.moneyBackGuarantee}
        </p>
      </div>
    </div>
  );
}
