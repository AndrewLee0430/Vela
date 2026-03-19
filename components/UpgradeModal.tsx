// components/UpgradeModal.tsx

import { useState } from 'react';

interface UpgradeModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const MONTHLY_VARIANT_ID = "待填入";  // Lemon Squeezy variant ID
const YEARLY_VARIANT_ID = "待填入";   // Lemon Squeezy variant ID

export default function UpgradeModal({ isOpen, onClose }: UpgradeModalProps) {
  const [loading, setLoading] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleUpgrade = async (variantId: string, plan: string) => {
    setLoading(plan);
    try {
      const res = await fetch('/api/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ variant_id: variantId }),
        credentials: 'include'
      });
      const data = await res.json();
      if (data.url) {
        window.location.href = data.url;
      }
    } catch (err) {
      console.error('Checkout error:', err);
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
        className="relative w-full max-w-md rounded-2xl p-8"
        style={{ background: '#0f1f3d', border: '1px solid rgba(255,255,255,0.1)' }}
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
          <h2 className="text-2xl font-bold text-white mb-1">Upgrade to Vela Pro</h2>
          <p className="text-gray-400 text-sm">Unlimited access to all features</p>
        </div>

        {/* Features */}
        <ul className="space-y-2 mb-6">
          {[
            '✅ Unlimited Research queries',
            '✅ Unlimited Drug Verification',
            '✅ Unlimited Report Explanation',
            '✅ Priority support',
          ].map((f, i) => (
            <li key={i} className="text-gray-300 text-sm">{f}</li>
          ))}
        </ul>

        {/* Pricing buttons */}
        <div className="space-y-3">
          <button
            onClick={() => handleUpgrade(MONTHLY_VARIANT_ID, 'monthly')}
            disabled={!!loading}
            className="w-full py-3 rounded-xl font-semibold text-white transition-all"
            style={{ background: loading === 'monthly' ? '#cc5533' : '#ff6b4a' }}
          >
            {loading === 'monthly' ? 'Redirecting...' : 'Monthly — $8.99 / month'}
          </button>

          <button
            onClick={() => handleUpgrade(YEARLY_VARIANT_ID, 'yearly')}
            disabled={!!loading}
            className="w-full py-3 rounded-xl font-semibold text-white transition-all"
            style={{ background: loading === 'yearly' ? '#1a3a6a' : '#1e4a8a' }}
          >
            {loading === 'yearly' ? 'Redirecting...' : 'Yearly — $89.99 / year (save 17%)'}
          </button>
        </div>

        <p className="text-center text-gray-500 text-xs mt-4">
          7-day money-back guarantee · Cancel anytime
        </p>
      </div>
    </div>
  );
}
