import daisyui from 'daisyui'

export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          'Inter',
          'system-ui',
          '-apple-system',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'sans-serif',
        ],
      },
      boxShadow: {
        glow: '0 0 42px -10px rgba(124, 92, 255, 0.45)',
        card: '0 10px 34px -14px rgba(0, 0, 0, 0.65)',
      },
    },
  },
  daisyui: {
    themes: [
      {
        persona: {
          primary: '#7c5cff',
          'primary-content': '#ffffff',
          secondary: '#f72585',
          'secondary-content': '#ffffff',
          accent: '#2dd4bf',
          'accent-content': '#04121a',
          neutral: '#191d2b',
          'neutral-content': '#e8ebf4',
          'base-100': '#0b0f1a',
          'base-200': '#141a2c',
          'base-300': '#1d2438',
          'base-content': '#e8ebf4',
          info: '#38bdf8',
          success: '#34d399',
          warning: '#fbbf24',
          error: '#fb7185',
        },
      },
    ],
    darkTheme: 'persona',
    base: true,
    styled: true,
    utils: true,
    logs: false,
  },
  plugins: [daisyui],
}
