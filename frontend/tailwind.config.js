/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0B1220",
          900: "#0F172A",
          800: "#16213A",
          700: "#1E293B",
          600: "#334155",
          400: "#64748B",
          200: "#CBD5E1",
          100: "#E2E8F0",
        },
        paper: {
          50: "#F7F8FA",
          100: "#EEF1F5",
        },
        brand: {
          600: "#0D9488",
          700: "#0F766E",
          100: "#CCFBF1",
        },
        mora: {
          low: "#D97706",
          mid: "#EA580C",
          high: "#DC2626",
        },
      },
      fontFamily: {
        display: ["Sora", "sans-serif"],
        body: ["Inter", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px 0 rgba(15, 23, 42, 0.06), 0 1px 3px 0 rgba(15, 23, 42, 0.08)",
      },
    },
  },
  plugins: [],
};
