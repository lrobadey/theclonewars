/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"] ,
  theme: {
    extend: {
      colors: {
        base: "#070b0f",
        panel: "#0e141c",
        glow: "#c8102e",
        accent: "#c8102e",
        ember: "#f2c14e",
        alert: "#ff6b6b"
      },
      boxShadow: {
        glow: "0 0 30px rgba(200, 16, 46, 0.25)",
        edge: "0 0 0 1px rgba(200, 16, 46, 0.18)"
      },
      keyframes: {
        floaty: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-6px)" }
        },
        scan: {
          "0%": { backgroundPosition: "0 0" },
          "100%": { backgroundPosition: "0 80px" }
        },
        pulseSoft: {
          "0%, 100%": { opacity: 0.65 },
          "50%": { opacity: 1 }
        }
      },
      animation: {
        floaty: "floaty 6s ease-in-out infinite",
        scan: "scan 12s linear infinite",
        pulseSoft: "pulseSoft 2.4s ease-in-out infinite"
      }
    }
  },
  plugins: []
};
