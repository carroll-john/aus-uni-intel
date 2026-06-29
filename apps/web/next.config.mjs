import path from "node:path";

/** @type {import('next').NextConfig} */
const nextConfig = {
  outputFileTracingRoot: path.join(process.cwd(), "../.."),
  reactStrictMode: true
};

export default nextConfig;
