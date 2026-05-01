"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export type RetentionPoint = { label: string } & Record<string, number | string>;

interface RetentionChartProps {
  data: RetentionPoint[];
  videos: string[];
}

// Distinct palette tuned for dark theme.
const PALETTE = [
  "#4ade80",
  "#60a5fa",
  "#f472b6",
  "#fbbf24",
  "#a78bfa",
  "#fb7185",
  "#34d399",
  "#f59e0b",
  "#94a3b8",
  "#c084fc",
];

const AXIS = "#6b7280";
const GRID = "#374151";
const LABEL = "#9ca3af";

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  const sorted = [...payload].sort((a, b) => b.value - a.value);
  return (
    <div className="rounded-md border border-border bg-popover px-3 py-2 text-xs shadow-md max-w-[260px]">
      <p className="font-medium text-foreground mb-1">{label}</p>
      {sorted.map((p) => (
        <p key={p.name} className="tabular-nums leading-tight" style={{ color: p.color }}>
          <span className="font-medium">{p.name}:</span>{" "}
          {(p.value * 100).toFixed(1)}%
        </p>
      ))}
    </div>
  );
}

export function RetentionChart({ data, videos }: RetentionChartProps) {
  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 10 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID} opacity={0.5} />
        <XAxis
          dataKey="label"
          stroke={AXIS}
          tick={{ fontSize: 11, fill: LABEL }}
          tickLine={false}
        />
        <YAxis
          stroke={AXIS}
          tick={{ fontSize: 11, fill: LABEL }}
          tickLine={false}
          domain={[0, 1]}
          tickFormatter={(v) => `${Math.round(v * 100)}%`}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: 11, paddingTop: 12 }}
          iconType="line"
          formatter={(value) => (
            <span style={{ color: LABEL }}>{value}</span>
          )}
        />
        {videos.map((name, i) => (
          <Line
            key={name}
            type="monotone"
            dataKey={name}
            stroke={PALETTE[i % PALETTE.length]}
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
