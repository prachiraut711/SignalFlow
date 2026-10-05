import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { TimeWindowMetric } from '../lib/api';

interface EventVolumeChartProps {
  data: TimeWindowMetric[];
  height?: number;
}

export const EventVolumeChart: React.FC<EventVolumeChartProps> = ({
  data,
  height = 240,
}) => {
  // Aggregate events by time_window
  const chartData = React.useMemo(() => {
    const buckets: Record<string, { time: string; events: number; errors: number }> = {};

    // Sort chronologically ascending
    const sorted = [...data].sort((a, b) =>
      new Date(a.time_window).getTime() - new Date(b.time_window).getTime()
    );

    sorted.forEach((item) => {
      const d = new Date(item.time_window);
      const label = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      if (!buckets[label]) {
        buckets[label] = { time: label, events: 0, errors: 0 };
      }
      buckets[label].events += item.event_count;
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
        <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="eventVolumeGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0} />
            </linearGradient>
          </defs>
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
            labelStyle={{ color: '#94a3b8', fontWeight: 600, marginBottom: '4px' }}
          />
          <Area
            type="monotone"
            dataKey="events"
            name="Total Events"
            stroke="#6366f1"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#eventVolumeGradient)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};
