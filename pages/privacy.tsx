// pages/privacy.tsx
import Link from 'next/link';
import Image from 'next/image';

export default function Privacy() {
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
                <h1 className="text-3xl font-bold text-white mb-2">Privacy Policy</h1>
                <p className="text-sm mb-2 text-text/40">Last updated: 2026-06-12</p>
                <p className="text-xs mb-8 text-text/40">This Privacy Policy is written in English. Any translation into another language is provided for convenience only. In the event of any inconsistency or conflict between the English version and any translated version, the English version shall prevail and control.</p>

                <div className="space-y-8 text-sm leading-relaxed text-text/75">

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">1. Data We Collect</h2>
                        <ul className="list-disc list-inside space-y-1 mb-3">
                            <li><strong className="text-white">Account data:</strong> Name, email address (via Clerk authentication)</li>
                            <li><strong className="text-white">Usage data:</strong> Feature usage counts, subscription status</li>
                            <li><strong className="text-white">Payment data:</strong> Processed exclusively by Dodo Payments — we never store card details</li>
                        </ul>
                        <p className="mb-2"><strong className="text-white">Signed-out (Anonymous) Usage:</strong> Query content and AI-generated responses are processed in real-time solely to fulfill your request. This data is processed in volatile memory and is not stored or logged on our servers.</p>
                        <p className="mb-2"><strong className="text-white">Signed-in Usage (Free &amp; Pro):</strong> To provide chat history and ensure service quality, query and answer content are processed, de-identified (via PHI masking as a primary safeguard), and linked to your account. This data is retained for a limited period of up to 6 months and is strictly never used to train artificial intelligence models.</p>
                        <p><strong className="text-white">Pro Subscription Preferences:</strong> For Pro subscribers, we synchronize a 16-character cryptographic hash derived from your workplace, role, and language preferences, alongside your locale, to enable cross-device consistency. The original, raw preference text never leaves your device. This hash is a pseudonymized value (not anonymous) and is treated as personal data linked to your account.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">2. No PHI Storage</h2>
                        <p>We do not store patient health information (PHI). Our PHI detection system actively blocks inputs containing identifiable patient data such as national IDs, passport numbers, or medical record numbers. De-identified query logs are retained for audit and service improvement purposes (see §4 below).</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">3. No AI Training</h2>
                        <p>Your queries and inputs are <strong className="text-white">never used to train AI models</strong>, including OpenAI models. We use the OpenAI API with data processing agreements that prohibit training on customer data.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">4. Data Retention, Deletion, and User Rights</h2>
                        <p className="mb-2">We retain your signed-in chat history and related audit logs (in their de-identified state) for up to 6 months for the sole purposes of providing you with continuity of service, conducting system security audits, and improving user experience. Data is automatically deleted after 6 months.</p>
                        <p className="mb-2">You have the right to request the deletion of your account and personal data at any time by contacting us via email at <a href="mailto:support@an-tho.com" className="underline" style={{ color: "rgb(var(--color-brand))" }}>support@an-tho.com</a>. Upon verifying your request, we will permanently erase or de-identify your personal data from our active production systems within 30 days.</p>
                        <p className="mb-2"><strong className="text-white">Statutory Exception for Financial Records:</strong> Please note that pursuant to Article 38 of the Taiwan Business Accounting Act, GDPR Article 6(1)(c), and applicable tax regulations, we are legally obligated to retain transactional, billing, and usage records (including transaction amounts, plan types, and payment processor identifiers) for a minimum of five (5) years solely for financial auditing and tax compliance purposes. During this statutory retention period, such data will be strictly restricted from any operational or marketing use and will be automatically purged once the legal retention period expires.</p>
                        <p>When you delete your account or chat history, the eligible personal data (excluding the statutory financial records described above) will be immediately and permanently deleted from our active production databases. Residual copies of this data contained within our automated system backups and transaction histories will naturally expire and be completely overwritten within 24 hours.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">5. Third-Party Services</h2>
                        <p className="mb-2">We use the following third-party services to operate Vela:</p>
                        <ul className="list-disc list-inside space-y-1">
                            <li><strong className="text-white">OpenAI</strong> — AI language model processing</li>
                            <li><strong className="text-white">Clerk</strong> — User authentication</li>
                            <li><strong className="text-white">Dodo Payments</strong> — Payment processing (Merchant of Record)</li>
                            <li><strong className="text-white">Sentry</strong> — Error monitoring and performance tracking (no PII collected)</li>
                            <li><strong className="text-white">PostHog</strong> — De-identified product analytics</li>
                            <li><strong className="text-white">Neon</strong> — Database hosting</li>
                            <li><strong className="text-white">Fly.io</strong> — Application hosting</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">6. International Data Transfers</h2>
                        <p>Our services are hosted and managed through cloud servers located in Tokyo, Japan (via Fly.io). By using Vela, users in Taiwan and other jurisdictions acknowledge and agree that their personal and pseudonymized data will be transferred to, stored, and processed in Japan. We ensure that our hosting providers maintain industry-standard security measures to protect your data in alignment with applicable data protection laws.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">7. Cookies</h2>
                        <p>We use essential cookies for authentication session management (via Clerk). We do not use advertising or tracking cookies.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">8. Public Sharing</h2>
                        <p className="mb-3">When you choose to share a query and answer via Vela&rsquo;s Share feature, the shared content (the query text, the answer, and citations) becomes publicly accessible at a share URL. We do not consider publicly shared content to be personal information, but you remain responsible for ensuring no patient identifiers or personal health information is included before you share. Vela does not actively monitor or pre-screen all publicly shared content.</p>
                        <p className="mb-3">You retain the ability to revoke any share at any time via Settings → Manage shares. After revocation, the public page will display a &ldquo;share has been revoked&rdquo; notice and we will stop serving the original content. However, third-party caches (search engines, social media platforms) may retain previews for some time after revocation; we cannot control these external caches.</p>
                        <p>We track aggregate view counts on shared pages for service quality and abuse prevention purposes; we do not associate visitor identity with shared page views beyond what is required for rate limiting.</p>
                        <p className="mt-3">If you delete your account, the link between you and any pages you previously shared is removed (your authorship association is severed), but the shared page itself remains publicly accessible unless you revoke it.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">9. Contact</h2>
                        <p>For privacy-related inquiries: <a href="mailto:support@an-tho.com" className="underline" style={{ color: "rgb(var(--color-brand))" }}>support@an-tho.com</a></p>
                    </section>
                </div>

                <div className="mt-12 pt-6 flex gap-6 text-xs border-t border-t-text/7 text-text/30">
                    <Link href="/terms" className="hover:text-white transition-colors">Terms of Service</Link>
                    <Link href="/refund" className="hover:text-white transition-colors">Refund Policy</Link>
                    <Link href="/" className="hover:text-white transition-colors">Back to Vela</Link>
                </div>
            </div>
        </main>
    );
}
