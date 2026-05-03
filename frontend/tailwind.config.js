/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#080C14',
        surface: '#0E1420',
        elevated: '#141B2D',
        muted: '#6B7A99',
        body: '#C8D3E8',
        heading: '#EEF2FF',
        divider: 'rgba(255,255,255,0.06)',
      },
      fontFamily: {
        syne: ['Syne', 'sans-serif'],
        heading: ['DM Sans', 'sans-serif'],
        body: ['IBM Plex Sans', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
