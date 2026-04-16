"use client";

import { useEffect, useState } from "react";
import App from "@/app/ui/app";
import type { User } from "@/lib/auth";
import type { DashboardData } from "@/lib/dashboard-data";

export default function AppWithData({ user }: { user: User }) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/v1/dashboard")
      .then(async (res) => {
        if (!res.ok) {
          const body = await res.json().catch(() => null);
          const detail = body?.error || `HTTP ${res.status}`;
          throw new Error(detail);
        }
        return res.json();
      })
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-red-500">Failed to load dashboard: {error}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-muted-foreground">Loading dashboard data...</p>
      </div>
    );
  }

  return <App user={user} data={data} />;
}
