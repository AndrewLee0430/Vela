// pages/refund.tsx
import Link from 'next/link';
import Image from 'next/image';

export default function Refund() {
    return (
        <main className="min-h-screen" style={{ background: "linear-gradient(135deg, #0a1628 0%, #0f2040 45%, #1a1035 75%, #0d1a2e 100%)" }}>
            <nav className="border-b" style={{ background: "linear-gradient(135deg, #0a1628 0%, #0f2040 45%, #1a1035 75%, #0d1a2e 100%)", borderColor: "rgba(255,255,255,0.07)" }}>
                <div className="container mx-auto px-4 py-3 flex items-center">
                    <Link href="/" className="flex items-center">
                        <Image src="/coral_logo.png" alt="Vela" width={40} height={40} style={{ objectFit: 'contain' }} />
                    </Link>
                </div>
            </nav>

            <div className="container mx-auto px-4 py-12 max-w-3xl">
                <h1 className="text-3xl font-bold text-white mb-2">Refund Policy</h1>
                <p className="text-sm mb-8" style={{ color: "rgba(255,255,255,0.4)" }}>Last updated: March 2026</p>

                <div className="space-y-8 text-sm leading-relaxed" style={{ color: "rgba(255,255,255,0.75)" }}>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">1. 7-Day Money-Back Guarantee</h2>
                        <p>If you are not satisfied with Vela Pro, you may request a full refund within <strong className="text-white">7 days</strong> of your initial purchase. No questions asked.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">2. How to Request a Refund</h2>
                        <p>Email us at <a href="mailto:support@an-tho.com" className="underline" style={{ color: "#ff8e6e" }}>support@an-tho.com</a> with:</p>
                        <ul className="list-disc list-inside space-y-1 mt-2">
                            <li>Your account email address</li>
                            <li>The date of purchase</li>
                            <li>Reason for refund (optional)</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">3. Processing Time</h2>
                        <p>Refunds are processed within <strong className="text-white">5–10 business days</strong> and returned to your original payment method.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">4. Cancellation</h2>
                        <p>You may cancel your subscription at any time through the <strong className="text-white">Customer Portal</strong> (accessible from the navbar when logged in as Pro). After cancellation, you retain access until the end of your current billing period. No partial refunds are issued for unused time after the 7-day window.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">5. Exceptions</h2>
                        <p>Refunds will not be issued for accounts terminated due to violations of our Terms of Service.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">6. Contact</h2>
                        <p>For refund requests or questions: <a href="mailto:support@an-tho.com" className="underline" style={{ color: "#ff8e6e" }}>support@an-tho.com</a></p>
                    </section>
                </div>

                <div className="mt-12 pt-6 flex gap-6 text-xs" style={{ borderTop: "1px solid rgba(255,255,255,0.07)", color: "rgba(255,255,255,0.3)" }}>
                    <Link href="/terms" className="hover:text-white transition-colors">Terms of Service</Link>
                    <Link href="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link>
                    <Link href="/" className="hover:text-white transition-colors">Back to Vela</Link>
                </div>
            </div>
        </main>
    );
}
