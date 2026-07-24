"use client";

import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis } from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDate, formatNumber } from "@/lib/utils";
import type { MetricPoint } from "@/lib/types";

interface MetricChartProps {
  title: string;
  data: MetricPoint[];
  color: string;
  gradientId: string;
}

export function MetricChart({ title, data, color, gradientId }: MetricChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="h-56 pt-0">
        {data.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            No data yet for this window
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.4} />
                  <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="date"
                tickFormatter={(value: string) => formatDate(value, { month: "short", day: "numeric", year: undefined })}
                tick={{ fontSize: 11, fill: "hsl(220 9% 65%)" }}
                axisLine={false}
                tickLine={false}
                minTickGap={24}
              />
              <Tooltip
                contentStyle={{
                  background: "hsl(240 10% 12%)",
                  border: "1px solid hsl(240 8% 24%)",
                  borderRadius: 8,
                  fontSize: 12,
                }}
                labelFormatter={(value) => (typeof value === "string" ? formatDate(value) : String(value ?? ""))}
                formatter={(value) => (typeof value === "number" ? formatNumber(value) : String(value ?? ""))}
              />
              <Area type="monotone" dataKey="value" stroke={color} strokeWidth={2} fill={`url(#${gradientId})`} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
