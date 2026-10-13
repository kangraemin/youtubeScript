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
          DEFAULT: '#f6f7f3',
          card: '#ffffff',
          soft: '#edf2ec',
        },
        border: {
          DEFAULT: '#d8dfd8',
          soft: '#e6ebe5',
        },
      },
    },
  },
  plugins: [],
}

export default config
