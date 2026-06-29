import path from "node:path";

/** @type {import('next').NextConfig} */
const nextConfig = {
  outputFileTracingRoot: process.env.VERCEL ? process.cwd() : path.join(process.cwd(), "../.."),
  reactStrictMode: true
};

export default nextConfig;
