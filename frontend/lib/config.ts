export const BACKEND_URL =
  process.env.BACKEND_URL ||
  (process.env.VERCEL_URL
    ? `https://${process.env.VERCEL_URL}/api/v1`
    : "http://localhost:8000");
