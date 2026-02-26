"use client"

import Link from 'next/link';
import { SignedIn, SignedOut, SignInButton, UserButton } from '@clerk/nextjs';
import { useState, useEffect } from 'react';
import Image from 'next/image';

const PROMPTS = [
  { text: 'Research Metformin interactions in renal impairment', color: '#ff8e6e' },
  { text: 'Verify Warfarin + Aspirin — is it safe?',            color: '#63b3ed' },
  { text: 'Write a patient letter from my clinical notes',      color: '#68d391' },
];

function TypewriterPrompt() {
  const [index, setIndex] = useState(0);
  const [text, setText] = useState('');
  const [deleting, setDeleting] = useState(false);

  const current = PROMPTS[index];

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (!deleting && text.length < current.text.length) {
      timer = setTimeout(() => setText(current.text.slice(0, text.length + 1)), 50);
    } else if (!deleting && text.length === current.text.length) {
      timer = setTimeout(() => setDeleting(true), 2200);
    } else if (deleting && text.length > 0) {
      timer = setTimeout(() => setText(text.slice(0, -1)), 25);
    } else {
      setDeleting(false);
      setIndex((prev) => (prev + 1) % PROMPTS.length);
    }
    return () => clearTimeout(timer);
  }, [text, deleting, index, current.text]);

  return (
    <span style={{ color: current.color, transition: 'color 0.3s ease' }}>
      {text}
      <span
        style={{ background: current.color }}
        className="inline-block w-0.5 h-5 ml-0.5 align-middle animate-pulse"
      />
    </span>
  );
}

const featureCards = [
  {
    href: '/research',
    icon: '🔬',
    label: 'Research',
    sub: 'PubMed 36M+',
    desc: 'Evidence-based answers grounded in peer-reviewed literature.',
    privacy: '🔒 No PHI stored',
    hoverColor: 'rgba(255,142,110,0.15)',
    borderHover: 'rgba(255,142,110,0.5)',
  },
  {
    href: '/verify',
    icon: '💊',
    label: 'Verify',
    sub: 'FDA Official',
    desc: 'Check drug interactions against official FDA label data.',
    privacy: '🔒 No PHI stored',
    hoverColor: 'rgba(99,179,237,0.15)',
    borderHover: 'rgba(99,179,237,0.5)',
  },
  {
    href: '/product',
    icon: '✉️',
    label: 'Document',
    sub: 'AI-Powered',
    desc: 'Turn clinical notes into clear patient education letters.',
    privacy: '🔒 No PHI stored',
    hoverColor: 'rgba(104,211,145,0.15)',
    borderHover: 'rgba(104,211,145,0.5)',
  },
];

export default function Home() {
  return (
    <>
      <style>{`
        @keyframes float {
          0%   { transform: translateY(0px); }
          50%  { transform: translateY(-12px); }
          100% { transform: translateY(0px); }
        }
        .logo-float {
          animation: float 3.5s ease-in-out infinite;
        }
      `}</style>

      <div
        className="min-h-screen flex flex-col"
        style={{
          background: 'linear-gradient(135deg, #0a1628 0%, #0f2040 45%, #1a1035 75%, #0d1a2e 100%)',
        }}
      >
        {/* ── Nav ── */}
        <nav className="flex-shrink-0 flex justify-end items-center px-10 py-5">
          <SignedIn><UserButton /></SignedIn>
          <SignedOut>
            <SignInButton mode="modal">
              <button
                className="px-5 py-2 text-sm font-medium text-white rounded-lg transition-all duration-200"
                style={{ border: '1px solid rgba(255,255,255,0.2)' }}
                onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.1)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                Sign In
              </button>
            </SignInButton>
          </SignedOut>
        </nav>

        {/* ── Hero ── */}
        <div className="flex-1 flex flex-col items-center justify-center px-10 text-center py-8">

          <div className="flex flex-col items-center mb-5">
            <div className="logo-float">
              <Image
                src="/coral_logo.png"
                alt="Vela logo"
                width={180}
                height={180}
                style={{ objectFit: 'contain' }}
                priority
              />
            </div>

            <h1
              className="mt-1 font-black"
              style={{
                fontSize: 'clamp(2.8rem, 7vw, 5rem)',
                background: 'linear-gradient(90deg, #ff6b6b, #ff8e6e, #ffb347)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                letterSpacing: '0.08em',
                lineHeight: 1,
              }}
            >
              Vela
            </h1>
          </div>

          <p className="text-2xl font-semibold text-white mb-2 tracking-tight">
            Medical Research, Simplified.
          </p>

          <p className="text-sm mb-10" style={{ color: 'rgba(255,255,255,0.35)' }}>
            ✦ Ask in any language — we search in English, answer in yours
          </p>

          {/* Typewriter box */}
          <div
            className="w-full rounded-2xl px-7 py-5 mb-10 text-left"
            style={{
              maxWidth: '680px',
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.12)',
              backdropFilter: 'blur(12px)',
            }}
          >
            <p className="text-xs uppercase tracking-widest mb-2 font-medium" style={{ color: 'rgba(255,255,255,0.35)' }}>
              Ask Vela to
            </p>
            <p className="text-lg leading-relaxed min-h-[1.8rem] text-white">
              <TypewriterPrompt />
            </p>
          </div>

          {/* CTA */}
          <div className="flex gap-3 mb-12">
            <SignedOut>
              <SignInButton mode="modal">
                <button
                  className="group px-8 py-3.5 text-white text-sm font-semibold rounded-xl transition-all duration-300 hover:scale-105 flex items-center gap-2"
                  style={{
                    background: 'linear-gradient(135deg, #ff6b6b, #ff8e6e)',
                    boxShadow: '0 0 28px rgba(255,107,107,0.4)',
                  }}
                >
                  Get Started Free
                  <span className="group-hover:translate-x-1 transition-transform">→</span>
                </button>
              </SignInButton>
            </SignedOut>
            <SignedIn>
              <Link href="/research">
                <button
                  className="group px-8 py-3.5 text-white text-sm font-semibold rounded-xl transition-all duration-300 hover:scale-105 flex items-center gap-2"
                  style={{
                    background: 'linear-gradient(135deg, #ff6b6b, #ff8e6e)',
                    boxShadow: '0 0 28px rgba(255,107,107,0.4)',
                  }}
                >
                  Open App
                  <span className="group-hover:translate-x-1 transition-transform">→</span>
                </button>
              </Link>
            </SignedIn>
            <Link href="/research">
              <button
                className="px-8 py-3.5 text-sm font-medium rounded-xl transition-all duration-200"
                style={{ color: 'rgba(255,255,255,0.55)', border: '1px solid rgba(255,255,255,0.15)' }}
                onMouseEnter={e => {
                  (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.08)';
                  (e.currentTarget as HTMLElement).style.color = 'white';
                }}
                onMouseLeave={e => {
                  (e.currentTarget as HTMLElement).style.background = 'transparent';
                  (e.currentTarget as HTMLElement).style.color = 'rgba(255,255,255,0.55)';
                }}
              >
                Try it now
              </button>
            </Link>
          </div>

          {/* Feature cards */}
          <div className="flex flex-col sm:flex-row gap-4 w-full" style={{ maxWidth: '780px' }}>
            {featureCards.map((f) => (
              <Link key={f.label} href={f.href} className="flex-1">
                <div
                  className="h-full rounded-2xl px-6 py-5 text-left cursor-pointer transition-all duration-300"
                  style={{
                    background: 'rgba(255,255,255,0.05)',
                    border: '1px solid rgba(255,255,255,0.1)',
                  }}
                  onMouseEnter={e => {
                    const el = e.currentTarget as HTMLElement;
                    el.style.background = f.hoverColor;
                    el.style.border = `1px solid ${f.borderHover}`;
                    el.style.transform = 'translateY(-3px)';
                    el.style.boxShadow = `0 8px 32px ${f.hoverColor}`;
                  }}
                  onMouseLeave={e => {
                    const el = e.currentTarget as HTMLElement;
                    el.style.background = 'rgba(255,255,255,0.05)';
                    el.style.border = '1px solid rgba(255,255,255,0.1)';
                    el.style.transform = 'translateY(0)';
                    el.style.boxShadow = 'none';
                  }}
                >
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-white text-base font-semibold">{f.icon} {f.label}</p>
                    <span
                      className="text-xs font-medium px-2 py-0.5 rounded-full"
                      style={{ background: 'rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.5)' }}
                    >
                      {f.sub}
                    </span>
                  </div>
                  <p className="text-sm mb-3" style={{ color: 'rgba(255,255,255,0.45)' }}>{f.desc}</p>
                  <p className="text-xs" style={{ color: 'rgba(255,255,255,0.25)' }}>{f.privacy}</p>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* ── Footer ── */}
        <div
          className="flex-shrink-0 flex justify-center items-center px-10 py-5 text-sm"
          style={{
            borderTop: '1px solid rgba(255,255,255,0.07)',
            color: 'rgba(255,255,255,0.3)',
          }}
        >
          <span>
            © {new Date().getFullYear()} Vela. All rights reserved. · Hosted on secure infrastructure · De-identified data only
          </span>
        </div>
      </div>
    </>
  );
}