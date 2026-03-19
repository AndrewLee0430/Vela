// pages/terms.tsx
import Link from 'next/link';
import Image from 'next/image';

export default function Terms() {
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
                <h1 className="text-3xl font-bold text-white mb-2">Terms of Service</h1>
                <p className="text-sm mb-8" style={{ color: "rgba(255,255,255,0.4)" }}>Last updated: March 2026</p>

                <div className="space-y-8 text-sm leading-relaxed" style={{ color: "rgba(255,255,255,0.75)" }}>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">1. Service Description</h2>
                        <p>Vela is an AI-powered clinical reference tool that provides evidence-based information from PubMed, FDA, LOINC, RxNorm, and MedlinePlus. Vela offers three core features: Research (literature-based Q&A), Verify (drug interaction checking), and Explain (medical report interpretation).</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">2. Medical Disclaimer</h2>
                        <p>Vela is for <strong className="text-white">educational and reference purposes only</strong>. It does not constitute medical advice, diagnosis, or treatment recommendations. All clinical decisions must be made by qualified healthcare professionals based on comprehensive patient assessment. Do not use Vela as a substitute for professional medical judgment.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">3. User Responsibilities</h2>
                        <ul className="list-disc list-inside space-y-1">
                            <li>Do not upload or input identifiable patient information (PHI)</li>
                            <li>Do not use Vela for direct clinical decision-making without professional verification</li>
                            <li>Do not attempt to circumvent usage limits or access controls</li>
                            <li>Use Vela only for lawful purposes consistent with applicable regulations</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">4. Subscription & Payment</h2>
                        <p>Paid subscriptions are processed by Lemon Squeezy. By subscribing, you agree to Lemon Squeezy's terms of service. Subscription fees are billed in advance on a monthly or annual basis. All payments are in USD.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">5. Fair Use Policy</h2>
                        <p>Vela Pro provides unlimited access for normal individual professional use. Automated, programmatic, or systematically excessive usage that disrupts service quality for other users may be subject to temporary rate limiting. Vela reserves the right to contact users whose usage patterns significantly exceed typical professional use to discuss appropriate plans.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">6. Account Termination</h2>
                        <p>We reserve the right to suspend or terminate accounts that violate these terms, engage in abuse, or use the service for unlawful purposes. You may cancel your subscription at any time through the Customer Portal.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">7. Governing Law</h2>
                        <p>These terms are governed by the laws of Taiwan (R.O.C.), without regard to conflict of law principles.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">8. Contact</h2>
                        <p>For questions about these terms, contact us at <a href="mailto:support@an-tho.com" className="underline" style={{ color: "#ff8e6e" }}>support@an-tho.com</a>.</p>
                    </section>
                </div>

                <div className="mt-12 pt-6 flex gap-6 text-xs" style={{ borderTop: "1px solid rgba(255,255,255,0.07)", color: "rgba(255,255,255,0.3)" }}>
                    <Link href="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link>
                    <Link href="/refund" className="hover:text-white transition-colors">Refund Policy</Link>
                    <Link href="/" className="hover:text-white transition-colors">Back to Vela</Link>
                </div>
            </div>
        </main>
    );
}
