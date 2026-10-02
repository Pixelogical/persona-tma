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
        glow: '0 0 42px -10px rgba(200, 61, 74, 0.5)',
        card: '0 10px 34px -14px rgba(0, 0, 0, 0.75)',
      },
    },
  },
  daisyui: {
    themes: [
      {
        persona: {
          primary: '#C83D4A',
          'primary-content': '#F3F1F2',
          secondary: '#E08A92',
          'secondary-content': '#090A0F',
          accent: '#4D8DCC',
          'accent-content': '#F3F1F2',
          neutral: '#20232D',
          'neutral-content': '#F3F1F2',
          'base-100': '#090A0F',
          'base-200': '#11131A',
          'base-300': '#181B23',
          'base-content': '#F3F1F2',
          info: '#4D8DCC',
          success: '#35B779',
          warning: '#E5A93D',
          error: '#E05260',
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
