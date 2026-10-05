import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Server,
  Search,
  RefreshCw,
  ArrowRight,
} from 'lucide-react';
import { api, ServiceMetric } from '../lib/api';
import { getServiceHealth } from '../components/ServiceHealthTable';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';

export const Services: React.FC = () => {
  const navigate = useNavigate();
  const [services, setServices] = useState<ServiceMetric[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const fetchServices = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getServiceMetrics();
      setServices(data);
    } catch (err: any) {
      console.error('Failed to load service metrics:', err);
      setError(err?.message || 'Failed to query service metrics from DuckDB store.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchServices();
  }, [fetchServices]);

  const filteredServices = services.filter((s) =>
    s.service.toLowerCase().includes(searchQuery.toLowerCase().trim())
  );

  return (
    <div className="space-y-6">
      {/* Header and Search Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-4 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur">
        <div className="relative w-full sm:w-72">
          <input
            type="text"
            placeholder="Search microservices..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500"
          />
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
        </div>

        <button
          onClick={fetchServices}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800 text-xs font-medium text-slate-300 hover:text-white transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {loading ? (
        <LoadingState message="Aggregating service performance metrics..." />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchServices} />
      ) : filteredServices.length === 0 ? (
        <EmptyState
          icon={Server}
          title="No services found"
          message={
            searchQuery
              ? `No service matches query "${searchQuery}".`
              : 'No services currently recorded in DuckDB analytical store.'
          }
          action={searchQuery ? { label: 'Clear Search', onClick: () => setSearchQuery('') } : undefined}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredServices.map((svc) => {
            const health = getServiceHealth(svc.error_rate);
            const HealthIcon = health.icon;

            return (
              <div
                key={svc.service}
                className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 hover:bg-slate-850 hover:border-slate-700 transition-all space-y-4 shadow-sm"
              >
                {/* Service Header */}
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full bg-indigo-500" />
                      <h3 className="text-sm font-bold text-white tracking-tight">{svc.service}</h3>
                    </div>
                    <span className="text-[11px] font-mono text-slate-500 block">
                      {svc.event_count.toLocaleString()} total events
                    </span>
                  </div>

                  <span
                    className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full border text-[11px] font-medium ${health.badge}`}
                  >
                    <HealthIcon className="w-3.5 h-3.5" />
                    {health.label}
                  </span>
                </div>

                {/* Metric Summary Grid */}
                <div className="grid grid-cols-3 gap-2 p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 font-mono text-xs">
                  <div>
                    <span className="text-[10px] text-slate-500 block uppercase">Error Rate</span>
                    <span
                      className={`font-semibold ${
                        svc.error_rate > 5 ? 'text-rose-400' : 'text-slate-200'
                      }`}
                    >
                      {svc.error_rate.toFixed(1)}%
                    </span>
                  </div>

                  <div>
                    <span className="text-[10px] text-slate-500 block uppercase">Errors</span>
                    <span className="text-slate-300 font-semibold">
                      {svc.error_count.toLocaleString()}
                    </span>
                  </div>

                  <div>
                    <span className="text-[10px] text-slate-500 block uppercase">Latency</span>
                    <span className="text-slate-300 font-semibold">
                      {svc.average_latency_ms.toFixed(0)} ms
                    </span>
                  </div>
                </div>

                {/* Action Links */}
                <div className="flex items-center justify-between pt-2 border-t border-slate-800/80 text-xs">
                  <button
                    onClick={() => navigate(`/signals?service=${svc.service}`)}
                    className="text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1 transition-colors"
                  >
                    View Incidents <ArrowRight className="w-3.5 h-3.5" />
                  </button>

                  <button
                    onClick={() => navigate(`/events?service=${svc.service}`)}
                    className="text-slate-400 hover:text-slate-200 text-[11px] transition-colors"
                  >
                    Explore Events
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
