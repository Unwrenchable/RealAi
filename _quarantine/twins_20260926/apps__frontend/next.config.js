const path = require("path");

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Keep monorepo tracing rooted at repo root; turbopack.root must match.
  output: "standalone",
  outputFileTracingRoot: path.join(__dirname, "../.."),
  turbopack: {
    root: path.join(__dirname, "../.."),
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
