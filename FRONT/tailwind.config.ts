import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}", "./features/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17211b",
        cream: "#f5f6f1",
        moss: "#315a45",
        lime: "#ddec62",
        line: "#dfe4dc"
      },
      boxShadow: { soft: "0 18px 50px rgba(23, 33, 27, 0.08)" }
    },
  },
  plugins: [],
};

export default config;

