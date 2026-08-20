// pages/refund.tsx
import Link from 'next/link';
import Image from 'next/image';

export default function Refund() {
    return (
        <main className="min-h-screen bg-app-bg">
            <nav className="border-b bg-app-bg border-text/7">
                <div className="container mx-auto px-4 py-3 flex items-center">
                    <Link href="/" className="flex items-center">
                        <Image src="/coral_logo.png" alt="Vela" width={40} height={40} style={{ objectFit: 'contain' }} />
                    </Link>
                </div>
            </nav>

            <div className="container mx-auto px-4 py-12 max-w-3xl">
                <h1 className="text-3xl font-bold text-text mb-2">Refund Policy</h1>
                <p className="text-sm mb-8 text-text/40">Last updated: March 2026</p>

                <div className="space-y-8 text-sm leading-relaxed text-text/75">

                    <section>
                        <h2 className="text-lg font-semibold text-text mb-3">1. 7-Day Money-Back Guarantee</h2>
                        <p>If you are not satisfied with Vela Pro, you may request a full refund within <strong className="text-text">7 days</strong> of your initial purchase. No questions asked.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-text mb-3">2. How to Request a Refund</h2>
                        <p>Email us at <a href="mailto:support@an-tho.com" className="underline" style={{ color: "rgb(var(--color-brand))" }}>support@an-tho.com</a> with:</p>
                        <ul className="list-disc list-inside space-y-1 mt-2">
                            <li>Your account email address</li>
                            <li>The date of purchase</li>
                            <li>Reason for refund (optional)</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-text mb-3">3. Processing Time</h2>
                        <p>Refunds are processed within <strong className="text-text">5–10 business days</strong> and returned to your original payment method.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-text mb-3">4. Cancellation</h2>
                        <p>You may cancel your subscription at any time through the <strong className="text-text">Dodo Payments Customer Portal</strong> at <a href="https://customer.dodopayments.com" target="_blank" rel="noopener noreferrer" className="underline" style={{ color: "rgb(var(--color-brand))" }}>customer.dodopayments.com</a> — enter the email address used at purchase to access your account. After cancellation, you retain access until the end of your current billing period. No partial refunds are issued for unused time after the 7-day window.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-text mb-3">5. Exceptions</h2>
                        <p>Refunds will not be issued for accounts terminated due to violations of our Terms of Service.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-text mb-3">6. Contact</h2>
                        <p>For refund requests or questions: <a href="mailto:support@an-tho.com" className="underline" style={{ color: "rgb(var(--color-brand))" }}>support@an-tho.com</a></p>
                    </section>
                </div>

                <div className="mt-12 pt-6 flex gap-6 text-xs border-t border-t-text/7 text-text/30">
                    <Link href="/terms" className="hover:text-text transition-colors">Terms of Service</Link>
                    <Link href="/privacy" className="hover:text-text transition-colors">Privacy Policy</Link>
                    <Link href="/" className="hover:text-text transition-colors">Back to Vela</Link>
                </div>
            </div>
        </main>
    );
}
