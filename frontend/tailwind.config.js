/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#8B5CF6", // Purple/violet accent
        dark: "#121212", // Black / charcoal background
        card: "#1E1E1E", // Clean cards
      }
    },
  },
  plugins: [],
}
