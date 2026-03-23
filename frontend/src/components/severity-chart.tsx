"use client";

import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from "recharts";
import { Card } from "@/components/ui/card";
import { SEVERITY_ORDER, SEVERITY_CHART_COLORS } from "@/lib/types";

interface SeverityChartProps {
  summary: Record<string, number>;
}

export function SeverityChart({ summary }: SeverityChartProps) {
  const data = SEVERITY_ORDER
    .filter((sev) => (summary[sev] || 0) > 0)
    .map((sev) => ({
      name: sev,
      value: summary[sev] || 0,
      color: SEVERITY_CHART_COLORS[sev],
    }));

  if (data.length === 0) return null;

  return (
    <Card>
      <h3 className="text-sm font-semibold mb-4">Severity Distribution</h3>
      <ResponsiveContainer width="100%" height={250}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={90}
            paddingAngle={2}
            dataKey="value"
          >
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: "#141414",
              border: "1px solid #262626",
              borderRadius: "8px",
              color: "#ededed",
            }}
          />
          <Legend
            formatter={(value) => (
              <span style={{ color: "#ededed", fontSize: "12px" }}>{value}</span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    </Card>
  );
}
