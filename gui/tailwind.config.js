/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        retro: {
          cyan: '#00ffff',
          magenta: '#ff00ff',
          green: '#00ff00',
          yellow: '#ffff00',
          purple: '#8b00ff',
          blue: '#0080ff',
        },
        claude: {
          orange: '#f97316',
          amber: '#f59e0b', 
          warmgray: '#78716c',
          slate: '#64748b',
          primary: '#f97316',
          secondary: '#f59e0b',
          accent: '#78716c',
        },
        'purple-haze': {
          primary: '#7f5af0',
          secondary: '#2cb67d',
          bg: '#16161a',
          surface: '#242629',
          card: '#2e2f33',
          border: '#72757e',
          text: '#94a1b2',
          headline: '#fffffe',
        },
        'happy-hues': {
          primary: '#7f5af0',
          secondary: '#2cb67d',
          tertiary: '#f2757e',
          bg: '#16161a',
          surface: '#242629',
          card: '#2e2f33',
          border: '#3a3d42',
          text: '#94a1b2',
          headline: '#fffffe',
          button: '#fffffe',
        },
        dark: {
          bg: '#0a0a0a',
          surface: '#1a1a1a',
          card: '#2a2a2a',
          border: '#3a3a3a',
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Courier New', 'monospace'],
        retro: ['Orbitron', 'monospace'],
      },
    },
  },
  plugins: [],
}