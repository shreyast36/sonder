/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg:       '#040404',
        surface:  '#0B0B12',
        gold:     '#D8B77A',
        goldHi:   '#EDD59A',
        violet:   '#8B5CF6',
        ivory:    '#F5F1E8',
        muted:    '#9C968E',
      },
      fontFamily: {
        sans:  ['Inter', 'system-ui', 'sans-serif'],
        serif: ['Playfair Display', 'Georgia', 'serif'],
      },
    },
  },
  plugins: [],
}
