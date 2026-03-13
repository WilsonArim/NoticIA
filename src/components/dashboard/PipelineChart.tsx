"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface DataPoint {
  date: string;
  articles: number;
  claims: number;
  reviews: number;
}

interface PipelineChartProps {
  data: DataPoint[];
}

export function PipelineChart({ data }: PipelineChartProps) {
  if (data.length === 0) {
    return (
      <div
        className="flex h-64 items-center justify-center text-sm"
        style={{ color: "var(--text-tertiary)" }}
      >
        Sem dados de pipeline disponiveis.
      </div>
    );
  }

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: 0 }}>
          <defs>
            <linearGradient id="fillArticles" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--area-tecnologia)" stopOpacity={0.3} />
              <stop offset="100%" stopColor="var(--area-tecnologia)" stopOpacity={0.02} />
            </linearGradient>
            <linearGradient id="fillClaims" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--area-ciencia)" stopOpacity={0.3} />
              <stop offset="100%" stopColor="var(--area-ciencia)" stopOpacity={0.02} />
            </linearGradient>
            <linearGradient id="fillReviews" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.3} />
              <stop offset="100%" stopColor="var(--accent)" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="date"
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 11, fill: "var(--text-tertiary)" }}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 11, fill: "var(--text-tertiary)" }}
            width={30}
          />
          <Tooltip
            contentStyle={{
              background: "var(--surface-elevated)",
              border: "1px solid var(--border-primary)",
              borderRadius: "0.5rem",
              fontSize: "12px",
              color: "var(--text-primary)",
            }}
          />
          <Area
            type="monotone"
            dataKey="articles"
            stroke="var(--area-tecnologia)"
            fill="url(#fillArticles)"
            strokeWidth={2}
            name="Artigos"
          />
          <Area
            type="monotone"
            dataKey="claims"
            stroke="var(--area-ciencia)"
            fill="url(#fillClaims)"
            strokeWidth={2}
            name="Claims"
          />
          <Area
            type="monotone"
            dataKey="reviews"
            stroke="var(--accent)"
            fill="url(#fillReviews)"
            strokeWidth={2}
            name="Revisoes"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
