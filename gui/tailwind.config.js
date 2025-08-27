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
      animation: {
        'glow': 'glow 2s ease-in-out infinite alternate',
        'matrix': 'matrix 0.5s linear infinite',
        'scan': 'scan 2s linear infinite',
        'flicker': 'flicker 0.15s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          '0%': { 
            boxShadow: '0 0 5px currentColor',
            textShadow: '0 0 5px currentColor'
          },
          '100%': { 
            boxShadow: '0 0 20px currentColor, 0 0 30px currentColor',
            textShadow: '0 0 10px currentColor'
          },
        },
        matrix: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100vh)' },
        },
        scan: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100vw)' },
        },
        flicker: {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.8 },
        }
      }
    },
  },
  plugins: [],
}