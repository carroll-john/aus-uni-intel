import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#002451",
        muted: "#5a6779",
        line: "#d8dde4",
        teal: "#0070c0",
        amber: "#d9a514",
        navy: "#002451",
        "navy-deep": "#001737",
        gold: "#fdcf41",
        coral: "#e35a4f",
        cream: "#f6f1e7",
        paper: "#ffffff",
        cyan: "#02c6fa",
      },
      boxShadow: {
        panel: "0 2px 8px rgba(10, 31, 68, 0.10)",
      },
    },
  },
  plugins: [],
};

export default config;
