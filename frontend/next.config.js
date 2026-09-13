const path = require("path");

/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    // Deploy must not fail on missing local ESLint plugin rules
    ignoreDuringBuilds: true,
  },
  output: "standalone",
  // Product-root frontend\ - one level up is C:\RealAI-clean
  outputFileTracingRoot: path.join(__dirname, ".."),
  // Dev: browser may open 127.0.0.1 while next prints localhost
  allowedDevOrigins: ["127.0.0.1", "localhost", "192.168.0.19"],
  env: {
    // On Vercel, NEXT_PUBLIC_API_URL must be set in the project env (Render URL).
    // Local default only when not building for Vercel.
    NEXT_PUBLIC_API_URL:
      process.env.NEXT_PUBLIC_API_URL ||
      process.env.REALAI_API_BASE ||
      (process.env.VERCEL ? "https://realai-api.onrender.com" : "http://127.0.0.1:8001"),
    NEXT_PUBLIC_SITE_URL:
      process.env.NEXT_PUBLIC_SITE_URL ||
      (process.env.VERCEL_URL
        ? `https://${process.env.VERCEL_URL}`
        : "http://127.0.0.1:3000"),
  },
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**",
      },
    ],
  },
};

module.exports = nextConfig;
