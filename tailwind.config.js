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
          'success':     'rgb(var(--color-success) / <alpha-value>)',
          'warning':     'rgb(var(--color-warning) / <alpha-value>)',
          'danger':      'rgb(var(--color-danger) / <alpha-value>)',
          'info':        'rgb(var(--color-info) / <alpha-value>)',
          'danger-soft': 'rgb(var(--color-danger-soft) / <alpha-value>)',
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

