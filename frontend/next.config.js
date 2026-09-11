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
  // Product-root frontend\\ — one level up is C:\\RealAI-clean
  outputFileTracingRoot: path.join(__dirname, ".."),
  // Dev: browser may open 127.0.0.1 while next prints localhost
  allowedDevOrigins: ["127.0.0.1", "localhost", "192.168.0.19"],
  env: {
    // Prefer hive orchestrator :8001 (console/fusion remain there)
    NEXT_PUBLIC_API_URL:
      process.env.NEXT_PUBLIC_API_URL ||
      process.env.REALAI_API_BASE ||
      "http://127.0.0.1:8001",
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
