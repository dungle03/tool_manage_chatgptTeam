/** @type {import('next').NextConfig} */
const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";

const nextConfig = {
  allowedDevOrigins: ["localhost", "127.0.0.1"],
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
