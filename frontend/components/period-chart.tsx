"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
} from "recharts";
import type { PeriodPoint } from "@/lib/aggregate";

function usd(n: number) {
  return (
    "$" +
    n.toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  );
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: PeriodPoint }>;
  label?: string;
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-md border border-border bg-popover px-3 py-2 text-xs shadow-md">
      <p className="font-medium text-foreground">
        {p.label}
        {p.isPartial && (
          <span className="ml-2 text-[10px] font-normal text-amber-400">
            (partial)
          </span>
        )}
      </p>
      <p className="text-muted-foreground">
        {p.views.toLocaleString()} views
      </p>
      <p className="text-muted-foreground">Spend: {usd(p.cost)}</p>
      <p className="text-muted-foreground">
        CPV: ${p.cpv.toFixed(3)}
      </p>
    </div>
  );
}

export function PeriodChart({ data }: { data: PeriodPoint[] }) {
  return (
    <div className="h-60">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="var(--border)"
            vertical={false}
          />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
            tickLine={false}
            axisLine={{ stroke: "var(--border)" }}
            angle={-30}
            textAnchor="end"
            height={60}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<CustomTooltip />} cursor={false} />
          <Bar
            dataKey="views"
            radius={[3, 3, 0, 0]}
            maxBarSize={60}
          >
            {data.map((d, i) => (
              <Cell
                key={i}
                fill={d.isPartial ? "#42CA8055" : "#42CA80"}
                stroke={d.isPartial ? "#42CA80" : undefined}
                strokeDasharray={d.isPartial ? "4 2" : undefined}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
