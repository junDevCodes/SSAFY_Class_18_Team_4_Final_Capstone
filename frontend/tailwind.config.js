/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f3e8f5',
          500: '#5f0080',
          600: '#4c0066',
          900: '#2d003d',
        },
        gray: {
          850: '#1f2937',
          900: '#111827',
        },
        kakao: '#FEE500',
        google: '#FFFFFF'
      },
      fontFamily: {
        sans: ['Pretendard Variable', 'Pretendard', 'sans-serif'],
        display: ['GmarketSans', 'sans-serif'],
      }
    },
  },
  plugins: [],
}

