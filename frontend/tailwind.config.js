/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', "system-ui", "sans-serif"],
      },
      colors: {
        // Design system: OLED dark + amber/indigo
        bg: {
          deep: "#020203",
          base: "#0F172A",
          elevated: "#1F1E27",
        },
        primary: "#D97706", // amber
        secondary: "#F59E0B",
        accent: "#6366F1", // indigo
        procurement: "#22D3EE", // cyan
        vendor: "#E879F9", // magenta
        success: "#10B981",
        danger: "#DC2626",
        warning: "#F59E0B",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "pulse-ring": {
          "0%, 100%": { opacity: "0.4" },
          "50%": { opacity: "1" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
      },
      animation: {
        "fade-up": "fade-up 280ms cubic-bezier(0.16, 1, 0.3, 1)",
        "pulse-ring": "pulse-ring 1.6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
