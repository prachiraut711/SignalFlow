import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  AlertTriangle,
  Clock,
  Radio,
  AlertOctagon,
  ArrowRight,
  TrendingUp,
} from 'lucide-react';
import {
  api,
  AnalyticsOverview,
  ServiceMetric,
  TimeWindowMetric,
  Signal,
} from '../lib/api';
import { StatCard } from '../components/StatCard';
import { SeverityBadge } from '../components/SeverityBadge';
import { StatusBadge } from '../components/StatusBadge';
import { EventVolumeChart } from '../components/EventVolumeChart';
import { ErrorRateChart } from '../components/ErrorRateChart';
import { ServiceHealthTable } from '../components/ServiceHealthTable';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();

  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [services, setServices] = useState<ServiceMetric[]>([]);
  const [windows, setWindows] = useState<TimeWindowMetric[]>([]);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboardData = useCallback(async () => {
    try {
      setError(null);
      const [ov, srv, win, sig] = await Promise.all([
        api.getOverview(),
        api.getServiceMetrics(),
        api.getTimeWindows(1),
        api.getSignals({ limit: 10 }),
      ]);
      setOverview(ov);
      setServices(srv);
      setWindows(win);
      setSignals(sig);
    } catch (err: any) {
      console.error('Failed to load dashboard data:', err);
      setError(err?.message || 'Unable to connect to SignalFlow backend API.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardData();
    const interval = setInterval(loadDashboardData, 30000); // 30-second polling

    const handleRefresh = () => loadDashboardData();
    window.addEventListener('signalflow:refresh', handleRefresh);

    return () => {
      clearInterval(interval);
      window.removeEventListener('signalflow:refresh', handleRefresh);
    };
  }, [loadDashboardData]);

  if (loading && !overview) {
    return <LoadingState message="Connecting to SignalFlow analytical pipeline..." />;
  }

  if (error && !overview) {
    return <ErrorState message={error} onRetry={loadDashboardData} />;
  }

  const activeSignalsCount = signals.filter((s) => s.status === 'OPEN').length;
  const criticalSignalsCount = signals.filter(
    (s) => s.status === 'OPEN' && s.severity === 'CRITICAL'
  ).length;

  return (
    <div className="space-y-6">
      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <StatCard
          title="Total Events"
          value={overview?.total_events.toLocaleString() || '0'}
          subtext="In analytical store"
          icon={Activity}
          variant="default"
        />
        <StatCard
          title="Error Count"
          value={overview?.total_errors.toLocaleString() || '0'}
          subtext="HTTP 4xx/5xx & failures"
          icon={AlertTriangle}
          variant={overview && overview.total_errors > 0 ? 'warning' : 'default'}
        />
        <StatCard
          title="Error Rate"
          value={`${overview?.error_rate.toFixed(2) || '0.00'}%`}
          subtext={
            overview && overview.error_rate > 5.0
              ? 'Elevated baseline'
              : 'Within normal bounds'
          }
          icon={TrendingUp}
          variant={
            overview && overview.error_rate > 10.0
              ? 'critical'
              : overview && overview.error_rate > 3.0
              ? 'warning'
              : 'success'
          }
        />
        <StatCard
          title="Avg Latency"
          value={`${overview?.average_latency_ms.toFixed(1) || '0.0'} ms`}
          subtext="End-to-end telemetry"
          icon={Clock}
          variant="default"
        />
        <StatCard
          title="Active Signals"
          value={activeSignalsCount}
          subtext="Open correlated incidents"
          icon={Radio}
          variant={activeSignalsCount > 0 ? 'warning' : 'success'}
        />
        <StatCard
          title="Critical Incidents"
          value={criticalSignalsCount}
          subtext="High-priority triage"
          icon={AlertOctagon}
          variant={criticalSignalsCount > 0 ? 'critical' : 'success'}
        />
      </div>

      {/* Analytical Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Event Volume Chart */}
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-white tracking-tight">
                Event Throughput Over Time
              </h3>
              <p className="text-xs text-slate-400">1-minute aggregation buckets from DuckDB</p>
            </div>
            <span className="text-[11px] font-mono text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
              Live Trend
            </span>
          </div>
          <EventVolumeChart data={windows} height={220} />
        </div>

        {/* Success vs Error Distribution Chart */}
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-white tracking-tight">
                Success vs. Error Distribution
              </h3>
              <p className="text-xs text-slate-400">Time-window operational breakdown</p>
            </div>
            <span className="text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
              Reliability
            </span>
          </div>
          <ErrorRateChart data={windows} height={220} />
        </div>
      </div>

      {/* Service Health Table & Recent Signals */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Service Health Overview (2 cols on lg) */}
        <div className="lg:col-span-2 p-5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-semibold text-white tracking-tight">
                  Service Health Overview
                </h3>
                <p className="text-xs text-slate-400">
                  Microservice operational status derived from error rates
                </p>
              </div>
              <button
                onClick={() => navigate('/services')}
                className="text-xs font-medium text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition-colors"
              >
                View all <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
            <ServiceHealthTable
              services={services}
              onSelectService={(s) => navigate(`/signals?service=${s}`)}
            />
          </div>
        </div>

        {/* Recent Correlated Signals (1 col on lg) */}
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-white tracking-tight">
                Recent Incident Signals
              </h3>
              <p className="text-xs text-slate-400">Correlated multi-anomaly incidents</p>
            </div>
            <button
              onClick={() => navigate('/signals')}
              className="text-xs font-medium text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition-colors"
            >
              All <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="flex-1 space-y-3">
            {signals.length === 0 ? (
              <div className="h-full flex items-center justify-center p-6 text-xs text-slate-500 italic text-center">
                No incident signals detected yet.
              </div>
            ) : (
              signals.slice(0, 4).map((sig) => (
                <div
                  key={sig.id}
                  onClick={() => navigate(`/signals/${sig.id}`)}
                  className="p-3.5 rounded-lg border border-slate-800 bg-slate-900/40 hover:bg-slate-850 hover:border-slate-700 transition-all cursor-pointer group"
                >
                  <div className="flex items-start justify-between gap-2 mb-1.5">
                    <span className="text-xs font-semibold text-slate-200 group-hover:text-indigo-300 transition-colors line-clamp-1">
                      {sig.title}
                    </span>
                    <SeverityBadge severity={sig.severity} size="sm" />
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                    <span>
                      {sig.service} &middot; {sig.region}
                    </span>
                    <StatusBadge status={sig.status} size="sm" />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
