import React from 'react';
import { ServiceMetric } from '../lib/api';
import { CheckCircle2, AlertTriangle, AlertOctagon } from 'lucide-react';

interface ServiceHealthTableProps {
  services: ServiceMetric[];
  onSelectService?: (serviceName: string) => void;
}

/**
 * Health Determination Logic:
 * - Healthy:  Error Rate <= 3.0%
 * - Warning:  Error Rate > 3.0% and <= 10.0%
 * - Critical: Error Rate > 10.0%
 */
export const getServiceHealth = (errorRate: number) => {
  if (errorRate > 10.0) {
    return {
      label: 'Critical',
      badge: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
      icon: AlertOctagon,
    };
  }
  if (errorRate > 3.0) {
    return {
      label: 'Warning',
      badge: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
      icon: AlertTriangle,
    };
  }
  return {
    label: 'Healthy',
    badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    icon: CheckCircle2,
  };
};

export const ServiceHealthTable: React.FC<ServiceHealthTableProps> = ({
  services,
  onSelectService,
}) => {
  if (services.length === 0) {
    return (
      <div className="p-8 text-center text-xs text-slate-500 italic bg-slate-900/30 rounded-xl border border-slate-800">
        No active services recorded in DuckDB analytics store.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/40">
      <table className="w-full text-left text-xs">
        <thead className="bg-slate-900/80 text-slate-400 font-medium uppercase tracking-wider border-b border-slate-800">
          <tr>
            <th className="py-3 px-4">Service</th>
            <th className="py-3 px-4">Events</th>
            <th className="py-3 px-4">Error Rate</th>
            <th className="py-3 px-4">Avg Latency</th>
            <th className="py-3 px-4 text-right">Health Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
          {services.map((item) => {
            const health = getServiceHealth(item.error_rate);
            const HealthIcon = health.icon;
            return (
              <tr
                key={item.service}
                onClick={() => onSelectService?.(item.service)}
                className={`hover:bg-slate-800/40 transition-colors ${
                  onSelectService ? 'cursor-pointer' : ''
                }`}
              >
                <td className="py-3 px-4 font-sans font-medium text-white flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-indigo-500" />
                  {item.service}
                </td>
                <td className="py-3 px-4">{item.event_count.toLocaleString()}</td>
                <td className="py-3 px-4">
                  <span className={item.error_rate > 5 ? 'text-rose-400 font-semibold' : ''}>
                    {item.error_rate.toFixed(2)}%
                  </span>
                  <span className="text-[10px] text-slate-500 ml-1">
                    ({item.error_count.toLocaleString()})
                  </span>
                </td>
                <td className="py-3 px-4">{item.average_latency_ms.toFixed(1)} ms</td>
                <td className="py-3 px-4 text-right">
                  <span
                    className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full border text-[11px] font-sans font-medium ${health.badge}`}
                  >
                    <HealthIcon className="w-3.5 h-3.5" />
                    {health.label}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
