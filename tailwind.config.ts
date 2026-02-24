import type { Config } from 'tailwindcss'

export default {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0b0d10',
        text: '#e8ecf2',
        muted: '#9aa4b2',
        accent: '#24d6ff',
        brandRed: '#ff4b5c'
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(36, 214, 255, 0.14), 0 0 28px rgba(36, 214, 255, 0.08)'
      }
    }
  },
  plugins: []
} satisfies Config

