import React, { useState, useEffect, useCallback } from 'react';
import {
  Activity,
  Filter,
  Search,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { api, EventItem } from '../lib/api';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';

export const Events: React.FC = () => {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter States
  const [service, setService] = useState('');
  const [eventType, setEventType] = useState('ALL');
  const [region, setRegion] = useState('');
  const [statusCode, setStatusCode] = useState('');
  const [limit, setLimit] = useState(50);
  const [offset, setOffset] = useState(0);

  const fetchEvents = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const parsedStatus = statusCode.trim() ? Number(statusCode) : undefined;
      const data = await api.getEvents({
        service: service.trim() || undefined,
        event_type: eventType !== 'ALL' ? eventType : undefined,
        region: region.trim() || undefined,
        status_code: parsedStatus,
        limit,
        offset,
      });
      setEvents(data);
    } catch (err: any) {
      console.error('Error fetching events:', err);
      setError(err?.message || 'Failed to query events from DuckDB store.');
    } finally {
      setLoading(false);
    }
  }, [service, eventType, region, statusCode, limit, offset]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  const handleApplyFilter = (e: React.FormEvent) => {
    e.preventDefault();
    setOffset(0); // Reset to first page
    fetchEvents();
  };

  const handleResetFilters = () => {
    setService('');
    setEventType('ALL');
    setRegion('');
    setStatusCode('');
    setOffset(0);
  };

  const formatTimestamp = (isoStr: string) => {
    try {
      return new Date(isoStr).toLocaleString([], {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return isoStr;
    }
  };

  const getStatusBadge = (code: number) => {
    if (code >= 500) {
      return 'bg-rose-500/10 text-rose-400 border-rose-500/30';
    }
    if (code >= 400) {
      return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
    }
    return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
  };

  return (
    <div className="space-y-6">
      {/* Search & Filter Toolbar */}
      <form
        onSubmit={handleApplyFilter}
        className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur space-y-3"
      >
        <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
          <div className="flex items-center gap-2 text-xs font-semibold text-white uppercase tracking-wider">
            <Filter className="w-4 h-4 text-indigo-400" />
            Event Explorer Filters
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleResetFilters}
              className="text-xs text-slate-400 hover:text-white transition-colors"
            >
              Reset
            </button>
            <button
              type="submit"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-colors"
            >
              <Search className="w-3.5 h-3.5" />
              Search
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 text-xs">
          {/* Service Filter */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">Service</label>
            <input
              type="text"
              placeholder="e.g. payment-service"
              value={service}
              onChange={(e) => setService(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-indigo-500"
            />
          </div>

          {/* Event Type Filter */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">Event Type</label>
            <select
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="ALL">All Event Types</option>
              <option value="payment_success">payment_success</option>
              <option value="payment_failed">payment_failed</option>
              <option value="order_created">order_created</option>
              <option value="order_cancelled">order_cancelled</option>
              <option value="user_login">user_login</option>
              <option value="user_signup">user_signup</option>
              <option value="api_request">api_request</option>
              <option value="api_error">api_error</option>
              <option value="refund_created">refund_created</option>
              <option value="file_upload">file_upload</option>
              <option value="notification_sent">notification_sent</option>
            </select>
          </div>

          {/* Region Filter */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">Region</label>
            <input
              type="text"
              placeholder="e.g. Pune"
              value={region}
              onChange={(e) => setRegion(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-indigo-500"
            />
          </div>

          {/* HTTP Status Code Filter */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">Status Code</label>
            <input
              type="number"
              placeholder="e.g. 500"
              value={statusCode}
              onChange={(e) => setStatusCode(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-indigo-500"
            />
          </div>

          {/* Rows Limit */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">Page Size</label>
            <select
              value={limit}
              onChange={(e) => {
                setLimit(Number(e.target.value));
                setOffset(0);
              }}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value={25}>25 rows</option>
              <option value={50}>50 rows</option>
              <option value={100}>100 rows</option>
            </select>
          </div>
        </div>
      </form>

      {/* Events Table Section */}
      {loading ? (
        <LoadingState message="Querying analytical events from DuckDB..." />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchEvents} />
      ) : events.length === 0 ? (
        <EmptyState
          icon={Activity}
          title="No analytical events found"
          message="No records match the current filter criteria or the analytical store is currently empty."
          action={{
            label: 'Reset Filters',
            onClick: handleResetFilters,
          }}
        />
      ) : (
        <div className="space-y-4">
          <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900 text-slate-400 font-medium uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4">Service</th>
                  <th className="py-3 px-4">Event Type</th>
                  <th className="py-3 px-4">Region</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Latency</th>
                  <th className="py-3 px-4">Value</th>
                  <th className="py-3 px-4">User</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                {events.map((evt) => (
                  <tr key={evt.event_id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-4 text-slate-400 whitespace-nowrap">
                      {formatTimestamp(evt.timestamp)}
                    </td>
                    <td className="py-3 px-4 font-sans font-medium text-white">
                      {evt.service}
                    </td>
                    <td className="py-3 px-4 text-indigo-300">
                      {evt.event_type}
                    </td>
                    <td className="py-3 px-4 text-slate-400">
                      {evt.region}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold border ${getStatusBadge(
                          evt.status_code
                        )}`}
                      >
                        {evt.status_code}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className={evt.latency_ms > 1000 ? 'text-amber-400 font-semibold' : ''}>
                        {evt.latency_ms.toFixed(0)} ms
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      {evt.value ? `$${evt.value.toFixed(2)}` : '—'}
                    </td>
                    <td className="py-3 px-4 text-slate-500 text-[11px]">
                      {evt.user_id || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          <div className="flex items-center justify-between text-xs text-slate-400 px-1">
            <div>
              Showing {offset + 1} to {offset + events.length} events
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setOffset(Math.max(0, offset - limit))}
                disabled={offset === 0}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-900 text-slate-300 hover:text-white hover:border-slate-700 transition-colors disabled:opacity-40"
              >
                <ChevronLeft className="w-3.5 h-3.5" /> Previous
              </button>
              <button
                onClick={() => setOffset(offset + limit)}
                disabled={events.length < limit}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-900 text-slate-300 hover:text-white hover:border-slate-700 transition-colors disabled:opacity-40"
              >
                Next <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
