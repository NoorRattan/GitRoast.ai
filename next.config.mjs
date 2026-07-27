/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    unoptimized: true,
    remotePatterns: [
      {
        protocol: "https",
        hostname: "card.gitroast.ai"
      },
      {
        protocol: "https",
        hostname: "gitroast-card-preview.jnoorrattan.workers.dev"
      }
    ]
  }
};

export default nextConfig;
