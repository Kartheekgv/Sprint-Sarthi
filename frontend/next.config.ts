import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/health",
        destination: `${process.env.BACKEND_INTERNAL_URL ?? "http://backend:8000"}/health`,
      },
      {
        source: "/api/v1/:path*",
        destination: `${process.env.BACKEND_INTERNAL_URL ?? "http://backend:8000"}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
