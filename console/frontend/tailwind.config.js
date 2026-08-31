/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        dark: {
          canvas: '#09090b',
          card: '#111318',
          'card-hover': '#181b22',
          border: '#27272a',
          'border-subtle': '#1f2128'
        },
        neon: {
          emerald: '#10b981',
          cyan: '#06b6d4',
          indigo: '#6366f1',
          rose: '#f43f5e',
          amber: '#f59e0b'
        }
      },
      fontFamily: {
        sans: ['Inter', 'DM Sans', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace']
      }
    },
  },
  plugins: [],
}
