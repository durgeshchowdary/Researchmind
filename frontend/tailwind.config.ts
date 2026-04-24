import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#6366F1",
          hover: "#4F46E5",
          soft: "#EEF2FF",
        },
        cyan: "#06B6D4",
        violet: "#8B5CF6",
        emerald: "#10B981",
        amber: "#F59E0B",
        navy: "#0F172A",
        "soft-navy": "#1E293B",
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "Segoe UI", "sans-serif"],
      },
      boxShadow: {
        panel: "0 18px 45px rgba(15, 23, 42, 0.08)",
        lift: "0 20px 50px rgba(99, 102, 241, 0.14)",
      },
    },
  },
  plugins: [],
};

export default config;
