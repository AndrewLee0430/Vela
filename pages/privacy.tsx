// pages/privacy.tsx
import Link from 'next/link';
import Image from 'next/image';

export default function Privacy() {
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
                <h1 className="text-3xl font-bold text-white mb-2">Privacy Policy</h1>
                <p className="text-sm mb-8" style={{ color: "rgba(255,255,255,0.4)" }}>Last updated: March 2026</p>

                <div className="space-y-8 text-sm leading-relaxed" style={{ color: "rgba(255,255,255,0.75)" }}>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">1. Data We Collect</h2>
                        <ul className="list-disc list-inside space-y-1">
                            <li><strong className="text-white">Account data:</strong> Name, email address (via Clerk authentication)</li>
                            <li><strong className="text-white">Usage data:</strong> Feature usage counts, subscription status</li>
                            <li><strong className="text-white">Query logs:</strong> Anonymized and sanitized query content for audit purposes</li>
                            <li><strong className="text-white">Payment data:</strong> Processed exclusively by Lemon Squeezy — we never store card details</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">2. No PHI Storage</h2>
                        <p>Vela is designed to process queries <strong className="text-white">in memory only</strong>. We do not store patient health information (PHI). Our PHI detection system actively blocks inputs containing identifiable patient data such as national IDs, passport numbers, or medical record numbers.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">3. No AI Training</h2>
                        <p>Your queries and inputs are <strong className="text-white">never used to train AI models</strong>, including OpenAI models. We use the OpenAI API with data processing agreements that prohibit training on customer data.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">4. Third-Party Services</h2>
                        <p className="mb-2">We use the following third-party services to operate Vela:</p>
                        <ul className="list-disc list-inside space-y-1">
                            <li><strong className="text-white">OpenAI</strong> — AI language model processing</li>
                            <li><strong className="text-white">Clerk</strong> — User authentication</li>
                            <li><strong className="text-white">Lemon Squeezy</strong> — Payment processing</li>
                            <li><strong className="text-white">PostHog</strong> — Anonymous product analytics</li>
                            <li><strong className="text-white">Neon</strong> — Database hosting</li>
                            <li><strong className="text-white">Fly.io</strong> — Application hosting</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">5. Cookies</h2>
                        <p>We use essential cookies for authentication session management (via Clerk). We do not use advertising or tracking cookies.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">6. Data Deletion</h2>
                        <p>To request deletion of your account and associated data, email us at <a href="mailto:support@an-tho.com" className="underline" style={{ color: "#ff8e6e" }}>support@an-tho.com</a>. We will process your request within 30 days.</p>
                    </section>

                    <section>
                        <h2 className="text-lg font-semibold text-white mb-3">7. Contact</h2>
                        <p>For privacy-related inquiries: <a href="mailto:support@an-tho.com" className="underline" style={{ color: "#ff8e6e" }}>support@an-tho.com</a></p>
                    </section>
                </div>

                <div className="mt-12 pt-6 flex gap-6 text-xs" style={{ borderTop: "1px solid rgba(255,255,255,0.07)", color: "rgba(255,255,255,0.3)" }}>
                    <Link href="/terms" className="hover:text-white transition-colors">Terms of Service</Link>
                    <Link href="/refund" className="hover:text-white transition-colors">Refund Policy</Link>
                    <Link href="/" className="hover:text-white transition-colors">Back to Vela</Link>
                </div>
            </div>
        </main>
    );
}
