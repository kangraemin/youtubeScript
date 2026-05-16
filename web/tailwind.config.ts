import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: '#0e0f12',
          card: '#14161b',
          soft: '#1a1d24',
        },
        border: {
          DEFAULT: '#2a2e38',
          soft: '#1f232c',
        },
      },
    },
  },
  plugins: [],
}

export default config
