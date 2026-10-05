import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts';
import { TimeWindowMetric } from '../lib/api';

interface ErrorRateChartProps {
  data: TimeWindowMetric[];
  height?: number;
}

export const ErrorRateChart: React.FC<ErrorRateChartProps> = ({
  data,
  height = 240,
}) => {
  const chartData = React.useMemo(() => {
    const buckets: Record<string, { time: string; success: number; errors: number }> = {};

    // Sort chronologically ascending
    const sorted = [...data].sort((a, b) =>
      new Date(a.time_window).getTime() - new Date(b.time_window).getTime()
    );

    sorted.forEach((item) => {
      const d = new Date(item.time_window);
      const label = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      if (!buckets[label]) {
        buckets[label] = { time: label, success: 0, errors: 0 };
      }
      buckets[label].success += item.success_count;
      buckets[label].errors += item.error_count;
    });

    return Object.values(buckets);
  }, [data]);

  if (chartData.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-xs text-slate-500 italic bg-slate-900/30 rounded-lg border border-slate-800/80"
        style={{ height }}
      >
        Awaiting telemetry time windows...
      </div>
    );
  }

  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.4} vertical={false} />
          <XAxis
            dataKey="time"
            stroke="#94a3b8"
            fontSize={11}
            tickLine={false}
            axisLine={{ stroke: '#334155' }}
          />
          <YAxis
            stroke="#94a3b8"
            fontSize={11}
            tickLine={false}
            axisLine={{ stroke: '#334155' }}
            allowDecimals={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#0f172a',
              borderColor: '#334155',
              borderRadius: '0.5rem',
              color: '#f8fafc',
              fontSize: '12px',
            }}
          />
          <Legend
            verticalAlign="top"
            align="right"
            iconType="circle"
            iconSize={8}
            wrapperStyle={{ fontSize: '11px', paddingBottom: '8px' }}
          />
          <Bar dataKey="success" name="Success Events" fill="#10b981" radius={[4, 4, 0, 0]} stackId="a" />
          <Bar dataKey="errors" name="Error Events" fill="#f43f5e" radius={[4, 4, 0, 0]} stackId="a" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};
