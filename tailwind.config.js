/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './apps/landing/templates/**/*.html',
    './apps/dashboard/templates/**/*.html',
    './templates/**/*.html',
  ],
  theme: {
    extend: {
      colors: {
        cream: '#FBF7F2',
        ink:   '#3A2430',
        rose: {
          50:'#FDF3F5', 100:'#FAE4E9', 200:'#F4C6D0',
          300:'#EBA0B0', 400:'#E0768C', 500:'#D8556B',
          600:'#C13E55', 700:'#A02F44'
        },
        gold: '#C79A6D',
      },
      fontFamily: {
        display: ['Lalezar', 'cursive'],
        body: ['Vazirmatn', 'sans-serif'],
      },
      boxShadow: {
        soft: '0 8px 30px -12px rgba(58,36,48,.12)',
        lift: '0 20px 40px -20px rgba(58,36,48,.18)',
      },
    },
  },
  plugins: [],
}