import type { DailyData } from "@/lib/dashboard-data";

export interface PeriodPoint {
  periodStart: string;
  periodEnd: string;
  label: string;
  views: number;
  cost: number;
  cpv: number;
  isPartial: boolean;
}

function parseDate(d: string): Date {
  return new Date(d + "T00:00:00");
}

function fmtDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function shortLabel(d: Date): string {
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function startOfWeekMonday(date: Date): Date {
  const d = new Date(date);
  const day = d.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  d.setDate(d.getDate() + diff);
  d.setHours(0, 0, 0, 0);
  return d;
}

function endOfWeekSunday(monday: Date): Date {
  const sun = new Date(monday);
  sun.setDate(sun.getDate() + 6);
  return sun;
}

function startOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function endOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth() + 1, 0);
}

export function aggregateDaily(
  daily: DailyData[],
  by: "week" | "month",
  asOf: Date,
): PeriodPoint[] {
  const buckets = new Map<string, { views: number; cost: number; start: Date; end: Date }>();

  for (const row of daily) {
    const d = parseDate(row.date);
    const start = by === "week" ? startOfWeekMonday(d) : startOfMonth(d);
    const end = by === "week" ? endOfWeekSunday(start) : endOfMonth(start);
    const key = fmtDate(start);
    const bucket = buckets.get(key) ?? { views: 0, cost: 0, start, end };
    bucket.views += row.views;
    bucket.cost += row.cost;
    buckets.set(key, bucket);
  }

  const sorted = [...buckets.entries()].sort(([a], [b]) => a.localeCompare(b));
  const today = new Date(asOf.getFullYear(), asOf.getMonth(), asOf.getDate());

  return sorted.map(([key, b]) => {
    const isPartial = b.end >= today;
    const label =
      by === "week"
        ? `${shortLabel(b.start)} – ${shortLabel(b.end)}`
        : b.start.toLocaleDateString("en-US", { month: "short", year: "numeric" });
    return {
      periodStart: key,
      periodEnd: fmtDate(b.end),
      label,
      views: b.views,
      cost: Math.round(b.cost * 100) / 100,
      cpv: b.views > 0 ? b.cost / b.views : 0,
      isPartial,
    };
  });
}

export function deltaPct(current: number, previous: number): number | null {
  if (previous === 0) return null;
  return (current - previous) / previous;
}
