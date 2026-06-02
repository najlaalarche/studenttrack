/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: { sans: ["Inter", "sans-serif"] },
      colors: {
        bg:      "#0A0A0F",
        surface: "#111118",
        card:    "#16161F",
        border:  "#1E1E2E",
        accent:  "#6366F1",
        green:   "#22C55E",
        orange:  "#F97316",
        red:     "#EF4444",
        text:    "#F8FAFC",
        sub:     "#94A3B8",
        muted:   "#64748B",
      },
      borderRadius: {
        card: "8px",
        badge: "6px",
      },
      boxShadow: {
        card: "0 1px 3px rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.3)",
        "card-hover": "0 4px 12px rgba(0,0,0,0.5)",
      },
    },
  },
  plugins: [],
};
