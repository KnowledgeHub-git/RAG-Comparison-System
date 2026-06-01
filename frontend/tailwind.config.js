/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        darkbg: '#090d16',
        cardbg: 'rgba(17, 25, 40, 0.75)',
        bordercol: 'rgba(255, 255, 255, 0.08)',
        primary: '#00d2ff',
        accent: '#00f2fe',
        greenacc: '#10b981',
      }
    },
  },
  plugins: [],
}
