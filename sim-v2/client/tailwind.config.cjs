/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Node colors from reference image
        core: "#00D4FF",
        "core-glow": "rgba(0, 212, 255, 0.5)",
        deep: "#FFB800",
        "deep-glow": "rgba(255, 184, 0, 0.5)",
        contested: "#FF3B3B",
        "contested-glow": "rgba(255, 59, 59, 0.5)",
        // Background
        space: "#0A0E14",
        "space-light": "#0F1620",
        // Text
        "text-primary": "#E8F4F8",
        "text-secondary": "#8BA4B4"
      },
      fontFamily: {
        mono: ["Space Mono", "monospace"],
        sans: ["Space Grotesk", "sans-serif"]
      },
      animation: {
        "pulse-slow": "pulseSlow 3s ease-in-out infinite",
        "glow-breath": "glowBreath 2.5s ease-in-out infinite",
        scan: "scan 12s linear infinite"
      },
      keyframes: {
        pulseSlow: {
          "0%, 100%": { transform: "scale(1)", opacity: "1" },
          "50%": { transform: "scale(1.02)", opacity: "0.9" }
        },
        glowBreath: {
          "0%, 100%": { opacity: "0.6" },
          "50%": { opacity: "1" }
        },
        scan: {
          "0%": { backgroundPosition: "0 0" },
          "100%": { backgroundPosition: "0 80px" }
        }
      }
    }
  },
  plugins: []
};
