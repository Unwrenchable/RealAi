const path = require("path");

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Keep monorepo tracing rooted at C:\realai without confusing Turbopack
  output: "standalone",
  outputFileTracingRoot: path.join(__dirname, "../.."),
  // Force project root so Next resolves local node_modules/next
  turbopack: {
    root: __dirname,
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
