// pages/terms.tsx
import Link from 'next/link';
import Image from 'next/image';

export default function Terms() {
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
                <h1 className="text-3xl font-bold text-white mb-2">Terms of Service</h1>
                <p className="text-sm mb-8 text-text/40">Last updated: 2026-08-11</p>

                <div className="space-y-8 text-sm leading-relaxed text-text/75">

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
                        <p>Paid subscriptions are processed by Dodo Payments, our Merchant of Record. By subscribing, you agree to Dodo Payments' terms of service. Subscription fees are billed in advance on a monthly or annual basis. Subscription fees may be displayed in local currency based on your location.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">5. Refund Policy</h2>
                        <p>We offer a <strong className="text-white">7-day money-back guarantee</strong> from the date of your first subscription payment. To request a refund, email <a href="mailto:support@an-tho.com" className="underline" style={{ color: "rgb(var(--color-brand))" }}>support@an-tho.com</a> within 7 days of purchase. Refunds are processed by Dodo Payments and typically appear within 5–10 business days. After the 7-day window, subscription payments are non-refundable. For full details, see our <a href="/refund" className="underline" style={{ color: "rgb(var(--color-brand))" }}>Refund Policy</a>.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">6. Fair Use Policy</h2>
                        <p>Pro subscribers enjoy unlimited access to all features subject to our fair use policy. To prevent automated abuse, a daily usage limit of <strong className="text-white">100 credits</strong> applies (approximately 33 Research queries, 100 Verify queries, or 50 Explain queries per day). This limit is designed to prevent scripted or automated use and will not affect normal clinical workflows. Free plan users receive <strong className="text-white">10 credits per day</strong>, resetting at midnight UTC. Users who reach their daily limit will be notified and can resume usage the following day.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">7. Account Termination</h2>
                        <p>We reserve the right to suspend or terminate accounts that violate these terms, engage in abuse, or use the service for unlawful purposes. You may cancel your subscription at any time through the Customer Portal.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">8. Public Sharing</h2>
                        <p className="mb-3">When you create a public share link via the Share feature, you grant Vela a non-exclusive, worldwide, royalty-free license to display the shared query and its answer on the public page accessible via the share URL. Vela reserves the right to remove any shared content that violates these Terms or our content policies, at our sole discretion and without prior notice.</p>
                        <p className="mb-3">You are responsible for ensuring that any query you choose to share publicly does not contain personal health information, patient identifiers, or other sensitive data. Once shared, the content becomes accessible to anyone with the share URL.</p>
                        <p>You may revoke a share at any time via Settings → Manage shares. Revocation will cause the public page to display a &ldquo;share has been revoked&rdquo; notice. Cached previews on third-party platforms (e.g. social media link cards) may continue to display for some time after revocation.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">9. Governing Law</h2>
                        <p>These terms are governed by the laws of Taiwan (R.O.C.), without regard to conflict of law principles.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">10. Contact</h2>
                        <p>For questions about these terms, contact us at <a href="mailto:support@an-tho.com" className="underline" style={{ color: "rgb(var(--color-brand))" }}>support@an-tho.com</a>.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">11. Language and Governing Translation</h2>
                        <p>This Agreement is written and executed in the English language. Any translation of this Agreement into any other language is provided for convenience only and shall have no legal force or effect. In the event of any inconsistency, ambiguity, or conflict between the English language version and any translated version, the English language version shall prevail and control in all respects.</p>
                    </section>
                </div>

                <p className="mt-10 text-xs text-text/40">If you need to access previous versions of our Terms of Service or Privacy Policy, please contact us at <a href="mailto:support@an-tho.com" className="underline" style={{ color: "rgb(var(--color-brand))" }}>support@an-tho.com</a>.</p>

                <div className="mt-12 pt-6 flex gap-6 text-xs border-t border-t-text/7 text-text/30">
                    <Link href="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link>
                    <Link href="/refund" className="hover:text-white transition-colors">Refund Policy</Link>
                    <Link href="/" className="hover:text-white transition-colors">Back to Vela</Link>
                </div>
            </div>
        </main>
    );
}
