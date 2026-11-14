/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: '#FAF9F5',
        card: '#FFFFFF',
        border: '#E7DCB8',
        primary: {
          50: '#ecfdf5',
          500: '#10b981',
          600: '#059669',
          700: '#047857',
        },
        status: {
          healthy: '#10b981',
          warning: '#C9A227',
          critical: '#ef4444',
          paused: '#6b7280',
          running: '#059669',
        }
      },
    },
  },
  plugins: [],
}
