/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,jsx}", "./components/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Anciennement "olive" : devient l'échelle bleu marine OliveSoft
        olive: {
          50: "#F1F5FA", 100: "#E3EAF3", 200: "#C7D4E6", 300: "#9DB3D0", 400: "#6F8DB5",
          500: "#4A6C9B", 600: "#2A4F80", 700: "#0B3A6E", 800: "#08305D", 900: "#03224C", 950: "#021834",
        },
        // Anciennement "sand" : devient le vert feuille du logo
        sand: {
          50: "#F5F8FC", 100: "#ECF6E2", 200: "#D7EBBE", 300: "#84C441", 400: "#6FB02F",
        },
        brand: {
          navy: "#03224C", ink: "#060D1F", slate: "#1B365D",
          teal: "#1DE9B6", cyan: "#19C3C9", lime: "#84C441",
        },
      },
      fontFamily: { sans: ["var(--font-jakarta)", "system-ui", "sans-serif"] },
      boxShadow: {
        soft: "0 1px 2px rgba(3,34,76,.05), 0 12px 30px -16px rgba(3,34,76,.25)",
      },
      keyframes: {
        fadeUp: { "0%": { opacity: "0", transform: "translateY(10px)" }, "100%": { opacity: "1", transform: "translateY(0)" } },
      },
      animation: { "fade-up": "fadeUp .45s ease-out both" },
    },
  },
  plugins: [],
};