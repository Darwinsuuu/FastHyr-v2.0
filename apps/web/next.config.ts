import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Import only the icons we use from Phosphor's barrel file.
  experimental: { optimizePackageImports: ["@phosphor-icons/react"] },
};

export default nextConfig;
