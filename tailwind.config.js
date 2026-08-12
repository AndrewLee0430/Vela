/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: 'class',
    content: [
      "./pages/**/*.{js,ts,jsx,tsx,mdx}",
      "./components/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
      extend: {
        colors: {
          'bg-1':    'rgb(var(--color-bg-1) / <alpha-value>)',
          'bg-2':    'rgb(var(--color-bg-2) / <alpha-value>)',
          'bg-3':    'rgb(var(--color-bg-3) / <alpha-value>)',
          'bg-4':    'rgb(var(--color-bg-4) / <alpha-value>)',
          'text':    'rgb(var(--color-text) / <alpha-value>)',
          'card':    'rgb(var(--color-text) / <alpha-value>)',
          'brand':   'rgb(var(--color-brand) / <alpha-value>)',
          // B3 paper palette (NOT named 'card' — that name is already bound
          // to the text variable above).
          'paper':    'rgb(var(--color-paper) / <alpha-value>)',
          'paper-2':  'rgb(var(--color-paper-2) / <alpha-value>)',
          'hairline': 'rgb(var(--color-hairline) / <alpha-value>)',
          'success':     'rgb(var(--color-success) / <alpha-value>)',
          'warning':     'rgb(var(--color-warning) / <alpha-value>)',
          'danger':      'rgb(var(--color-danger) / <alpha-value>)',
          'info':        'rgb(var(--color-info) / <alpha-value>)',
          'danger-soft': 'rgb(var(--color-danger-soft) / <alpha-value>)',
        },
        boxShadow: {
          // B4: value defined once in globals.css (--shadow-card) so no rgba
          // literal appears in components.
          card: 'var(--shadow-card)',
        },
        backgroundImage: {
          'app-bg': 'linear-gradient(135deg, rgb(var(--color-bg-1)) 0%, rgb(var(--color-bg-2)) 45%, rgb(var(--color-bg-3)) 75%, rgb(var(--color-bg-4)) 100%)',
        },
        opacity: {
          '4':  '0.04',
          '6':  '0.06',
          '7':  '0.07',
          '8':  '0.08',
          '12': '0.12',
        },
        fontFamily: {
          sans: ['var(--font-sans)', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', '"Noto Sans"', '"Noto Sans CJK TC"', 'sans-serif'],
          // B3 editorial serif — deliberate fallback stack: Latin gets Source
          // Serif 4 (self-hosted); non-Latin scripts fall through to system
          // serifs / the existing CJK entry. Gate 4 verifies zh-TW + ar look
          // intentional under fallback.
          serif: ['var(--font-serif)', 'Georgia', '"Times New Roman"', '"Noto Sans CJK TC"', 'serif'],
        },
        keyframes: {
          slideUp: {
            '0%': { transform: 'translateY(100%)', opacity: '0' },
            '100%': { transform: 'translateY(0)', opacity: '1' },
          },
        },
        animation: {
          slideUp: 'slideUp 0.3s ease-out',
        },
      },
    },
    plugins: [],
  }

