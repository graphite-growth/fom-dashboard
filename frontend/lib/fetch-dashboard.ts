import { BACKEND_URL } from "./config";
import type { DashboardData } from "./dashboard-data";

const AUTH_SECRET = process.env.AUTH_SECRET || "";

export async function fetchDashboardData(
  cookieHeader: string
): Promise<DashboardData> {
  const url = `${BACKEND_URL}/dashboard/internal`;
  const response = await fetch(url, {
    headers: {
      "x-internal-secret": AUTH_SECRET,
    },
  });
  if (!response.ok) {
    throw new Error(`Dashboard API returned HTTP ${response.status}`);
  }
  const data = (await response.json()) as DashboardData;
  if (!data.videos || data.videos.length === 0) {
    throw new Error("Dashboard API returned no video data");
  }
  return data;
}
