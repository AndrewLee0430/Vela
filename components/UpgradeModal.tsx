// components/UpgradeModal.tsx

import { useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { clearPlanCache } from './PlanBadge';

interface UpgradeModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const MONTHLY_PRODUCT_ID = "pdt_0NbELHXiGodgawGwVaZ3t";
const YEARLY_PRODUCT_ID  = "pdt_0NbELkno040P4wQSaQaam";

export default function UpgradeModal({ isOpen, onClose }: UpgradeModalProps) {
  const [loading, setLoading] = useState<string | null>(null);
  const { getToken } = useAuth();

  if (!isOpen) return null;

  const handleUpgrade = async (productId: string, plan: string) => {
    setLoading(plan);
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
          <p className="text-gray-400 text-sm">Unlimited* access to all features</p>
        </div>

        {/* Features */}
        <ul className="space-y-2 mb-2">
          {[
            '✅ Unlimited* Research queries',
            '✅ Unlimited* Drug Verification',
            '✅ Unlimited* Report Explanation',
            '✅ Priority support',
          ].map((f, i) => (
            <li key={i} className="text-gray-300 text-sm">{f}</li>
          ))}
        </ul>
        <p className="text-xs mb-4" style={{ color: 'rgba(255,255,255,0.4)' }}>
          *Subject to fair use policy. See <a href="/terms" target="_blank" className="underline hover:opacity-80">Terms of Service</a>.
        </p>

        {/* ToS consent */}
        <p className="text-xs text-center mb-3" style={{ color: 'rgba(255,255,255,0.45)' }}>
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
            {loading === 'monthly' ? 'Redirecting...' : 'Monthly — $8.99 / month'}
          </button>

          <button
            onClick={() => handleUpgrade(YEARLY_PRODUCT_ID, 'yearly')}
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
