import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    const apiBaseUrl =
      process.env.API_INTERNAL_BASE_URL ??
      process.env.LOCAL_API_BASE_URL ??
      "http://127.0.0.1:8001/api/v1";
    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiBaseUrl}/:path*`
      }
    ];
  }
};

export default nextConfig;
