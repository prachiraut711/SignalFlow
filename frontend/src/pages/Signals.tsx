import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  AlertOctagon,
  Filter,
  Search,
  RefreshCw,
  GitMerge,
  ArrowRight,
  Layers,
  Clock,
  MapPin,
} from 'lucide-react';
import { api, Signal } from '../lib/api';
import { SeverityBadge } from '../components/SeverityBadge';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';

export const Signals: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // Filters from URL query params or state defaults
  const [severityFilter, setSeverityFilter] = useState<string>(
    searchParams.get('severity') || 'ALL'
  );
  const [statusFilter, setStatusFilter] = useState<string>(
    searchParams.get('status') || 'ALL'
  );
  const [serviceFilter, setServiceFilter] = useState<string>(
    searchParams.get('service') || ''
  );
  const [regionFilter, setRegionFilter] = useState<string>(
    searchParams.get('region') || ''
  );

  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [correlating, setCorrelating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSignals = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getSignals({
        severity: severityFilter,
        status: statusFilter,
        service: serviceFilter || undefined,
        region: regionFilter || undefined,
        limit: 100,
      });
      setSignals(data);
    } catch (err: any) {
      console.error('Error fetching signals:', err);
      setError(err?.message || 'Failed to load signals from backend.');
    } finally {
      setLoading(false);
    }
  }, [severityFilter, statusFilter, serviceFilter, regionFilter]);

  useEffect(() => {
    fetchSignals();
  }, [fetchSignals]);

  // Sync state to URL params
  const updateFilter = (key: string, value: string) => {
    const nextParams = new URLSearchParams(searchParams);
    if (value && value !== 'ALL') {
      nextParams.set(key, value);
    } else {
      nextParams.delete(key);
    }
    setSearchParams(nextParams);
  };

  const handleCorrelate = async () => {
    try {
      setCorrelating(true);
      await api.correlateSignals();
      await fetchSignals();
    } catch (err: any) {
      alert(`Correlation error: ${err?.message || 'Failed to trigger correlation.'}`);
    } finally {
      setCorrelating(false);
    }
  };

  const formatDate = (isoStr: string) => {
    try {
      return new Date(isoStr).toLocaleString([], {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoStr;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Action & Filter Toolbar */}
      <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur space-y-3">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
          <div className="flex items-center gap-2 text-xs font-semibold text-white uppercase tracking-wider">
            <Filter className="w-4 h-4 text-indigo-400" />
            Filter Incidents
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <button
              onClick={handleCorrelate}
              disabled={correlating}
              className="flex-1 sm:flex-initial inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-colors disabled:opacity-50 shadow-sm"
              title="Run sliding-window correlation scan across recent anomalies"
            >
              <GitMerge className={`w-3.5 h-3.5 ${correlating ? 'animate-spin' : ''}`} />
              {correlating ? 'Correlating...' : 'Trigger Correlation'}
            </button>
            <button
              onClick={fetchSignals}
              disabled={loading}
              className="p-1.5 rounded-lg border border-slate-700 bg-slate-800 text-slate-300 hover:text-white transition-colors"
              title="Refresh"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Filter Inputs Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
          {/* Severity Filter */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">Severity</label>
            <select
              value={severityFilter}
              onChange={(e) => {
                setSeverityFilter(e.target.value);
                updateFilter('severity', e.target.value);
              }}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="ALL">All Severities</option>
              <option value="CRITICAL">CRITICAL</option>
              <option value="HIGH">HIGH</option>
              <option value="WARNING">WARNING</option>
              <option value="INFO">INFO</option>
            </select>
          </div>

          {/* Status Filter */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                updateFilter('status', e.target.value);
              }}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="ALL">All Statuses</option>
              <option value="OPEN">OPEN</option>
              <option value="RESOLVED">RESOLVED</option>
            </select>
          </div>

          {/* Service Search */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">Service</label>
            <div className="relative">
              <input
                type="text"
                placeholder="e.g. payment-service"
                value={serviceFilter}
                onChange={(e) => {
                  setServiceFilter(e.target.value);
                  updateFilter('service', e.target.value);
                }}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-2.5 py-1.5 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-indigo-500"
              />
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2" />
            </div>
          </div>

          {/* Region Search */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">Region</label>
            <div className="relative">
              <input
                type="text"
                placeholder="e.g. Pune"
                value={regionFilter}
                onChange={(e) => {
                  setRegionFilter(e.target.value);
                  updateFilter('region', e.target.value);
                }}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-2.5 py-1.5 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-indigo-500"
              />
              <MapPin className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2" />
            </div>
          </div>
        </div>
      </div>

      {/* Signals Content Area */}
      {loading ? (
        <LoadingState message="Fetching correlated incident signals..." />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchSignals} />
      ) : signals.length === 0 ? (
        <EmptyState
          icon={AlertOctagon}
          title="No incident signals found"
          message="No operational signals match your filter criteria. Trigger correlation or reset filters."
          action={{
            label: 'Clear Filters',
            onClick: () => {
              setSeverityFilter('ALL');
              setStatusFilter('ALL');
              setServiceFilter('');
              setRegionFilter('');
              setSearchParams({});
            },
          }}
        />
      ) : (
        <div className="space-y-3">
          {signals.map((sig) => (
            <div
              key={sig.id}
              onClick={() => navigate(`/signals/${sig.id}`)}
              className="p-4 sm:p-5 rounded-xl border border-slate-800 bg-slate-900/60 hover:bg-slate-850 hover:border-slate-700 transition-all cursor-pointer group shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              {/* Left Column: Title, Metadata, Description */}
              <div className="space-y-2 max-w-2xl">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold text-white group-hover:text-indigo-300 transition-colors">
                    {sig.title}
                  </h3>
                  <SeverityBadge severity={sig.severity} size="sm" />
                  <StatusBadge status={sig.status} size="sm" />
                </div>

                <p className="text-xs text-slate-300 line-clamp-1">{sig.description}</p>

                <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 font-mono">
                  <span className="flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
                    {sig.service}
                  </span>
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3 h-3 text-slate-500" />
                    {sig.region}
                  </span>
                  <span className="flex items-center gap-1">
                    <Layers className="w-3 h-3 text-slate-500" />
                    {sig.related_anomalies_count} correlated{' '}
                    {sig.related_anomalies_count === 1 ? 'anomaly' : 'anomalies'}
                  </span>
                </div>
              </div>

              {/* Right Column: Timestamps & Detail Arrow */}
              <div className="flex items-center justify-between md:justify-end gap-6 pt-3 md:pt-0 border-t md:border-t-0 border-slate-800/80 text-xs">
                <div className="text-left md:text-right font-mono space-y-1 text-slate-400">
                  <div className="flex items-center md:justify-end gap-1 text-[11px]">
                    <Clock className="w-3 h-3 text-slate-500" />
                    First: {formatDate(sig.first_detected_at)}
                  </div>
                  <div className="text-[11px] text-slate-500">
                    Last: {formatDate(sig.last_detected_at)}
                  </div>
                </div>

                <div className="p-2 rounded-lg bg-slate-800/80 text-slate-400 group-hover:text-white group-hover:bg-indigo-600 transition-all">
                  <ArrowRight className="w-4 h-4" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
