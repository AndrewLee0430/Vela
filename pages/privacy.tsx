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
                <p className="text-sm mb-8 text-text/40">Last updated: 2026-05-08</p>

                <div className="space-y-8 text-sm leading-relaxed text-text/75">

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">1. Data We Collect</h2>
                        <ul className="list-disc list-inside space-y-1">
                            <li><strong className="text-white">Account data:</strong> Name, email address (via Clerk authentication)</li>
                            <li><strong className="text-white">Usage data:</strong> Feature usage counts, subscription status</li>
                            <li><strong className="text-white">Query logs:</strong> Anonymized and sanitized query content for audit purposes</li>
                            <li><strong className="text-white">Payment data:</strong> Processed exclusively by Dodo Payments — we never store card details</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">2. No PHI Storage</h2>
                        <p>We do not store patient health information (PHI). Our PHI detection system actively blocks inputs containing identifiable patient data such as national IDs, passport numbers, or medical record numbers. Anonymized query logs are retained for audit and service improvement purposes (see §4 Data Retention below).</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">3. No AI Training</h2>
                        <p>Your queries and inputs are <strong className="text-white">never used to train AI models</strong>, including OpenAI models. We use the OpenAI API with data processing agreements that prohibit training on customer data.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">4. Data Retention</h2>
                        <p className="mb-2">Anonymized audit logs and chat history are retained for <strong className="text-white">up to 6 months</strong> for service improvement and compliance purposes. After 6 months, records are automatically deleted. You may request earlier deletion at any time (see §6 Data Deletion).</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">5. Third-Party Services</h2>
                        <p className="mb-2">We use the following third-party services to operate Vela:</p>
                        <ul className="list-disc list-inside space-y-1">
                            <li><strong className="text-white">OpenAI</strong> — AI language model processing</li>
                            <li><strong className="text-white">Clerk</strong> — User authentication</li>
                            <li><strong className="text-white">Dodo Payments</strong> — Payment processing (Merchant of Record)</li>
                            <li><strong className="text-white">Sentry</strong> — Error monitoring and performance tracking (no PII collected)</li>
                            <li><strong className="text-white">PostHog</strong> — Anonymous product analytics</li>
                            <li><strong className="text-white">Neon</strong> — Database hosting</li>
                            <li><strong className="text-white">Fly.io</strong> — Application hosting</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">6. Cookies</h2>
                        <p>We use essential cookies for authentication session management (via Clerk). We do not use advertising or tracking cookies.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">7. Public Sharing</h2>
                        <p className="mb-3">When you choose to share a query and answer via Vela&rsquo;s Share feature, the shared content (the query text, the answer, and citations) becomes publicly accessible at a share URL. We do not consider publicly shared content to be personal information, but you remain responsible for ensuring no patient identifiers or personal health information is included before you share. Vela does not actively monitor or pre-screen all publicly shared content.</p>
                        <p className="mb-3">You retain the ability to revoke any share at any time via Settings → Manage shares. After revocation, the public page will display a &ldquo;share has been revoked&rdquo; notice and we will stop serving the original content. However, third-party caches (search engines, social media platforms) may retain previews for some time after revocation; we cannot control these external caches.</p>
                        <p>We track aggregate view counts on shared pages for service quality and abuse prevention purposes; we do not associate visitor identity with shared page views beyond what is required for rate limiting.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">8. Data Deletion</h2>
                        <p>To request deletion of your account and associated data, email us at <a href="mailto:support@an-tho.com" className="underline" style={{ color: "#ff8e6e" }}>support@an-tho.com</a>. We will process your request within 30 days.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">9. Contact</h2>
                        <p>For privacy-related inquiries: <a href="mailto:support@an-tho.com" className="underline" style={{ color: "#ff8e6e" }}>support@an-tho.com</a></p>
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
