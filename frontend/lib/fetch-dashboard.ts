import { BACKEND_URL } from "./config";
import type { DashboardData } from "./dashboard-data";

export async function fetchDashboardData(
  cookieHeader: string
): Promise<DashboardData> {
  const response = await fetch(`${BACKEND_URL}/dashboard`, {
    headers: { cookie: cookieHeader },
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
