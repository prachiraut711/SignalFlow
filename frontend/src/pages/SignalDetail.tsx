import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  CheckCircle2,
  Sparkles,
  Layers,
  Clock,
  MapPin,
  Server,
  AlertCircle,
  HelpCircle,
  Wrench,
  Loader2,
  TrendingUp,
} from 'lucide-react';
import { api, SignalDetail as ISignalDetail, AIExplanation } from '../lib/api';
import { SeverityBadge } from '../components/SeverityBadge';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';

export const SignalDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [signal, setSignal] = useState<ISignalDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // AI Explanation State
  const [explanation, setExplanation] = useState<AIExplanation | null>(null);
  const [explaining, setExplaining] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  // Resolve State
  const [resolving, setResolving] = useState(false);
  const [resolveSuccess, setResolveSuccess] = useState(false);

  const fetchDetail = useCallback(async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const data = await api.getSignal(Number(id));
      setSignal(data);
    } catch (err: any) {
      console.error('Failed to load signal detail:', err);
      setError(err?.message || `Signal with ID ${id} was not found.`);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  const handleResolve = async () => {
    if (!signal) return;
    try {
      setResolving(true);
      const updated = await api.resolveSignal(signal.id);
      setSignal(updated);
      setResolveSuccess(true);
      setTimeout(() => setResolveSuccess(false), 5000);
    } catch (err: any) {
      alert(`Failed to resolve incident: ${err?.message || 'Server error'}`);
    } finally {
      setResolving(false);
    }
  };

  const handleGenerateAI = async () => {
    if (!signal) return;
    try {
      setExplaining(true);
      setAiError(null);
      const res = await api.explainSignal(signal.id);
      setExplanation(res);
    } catch (err: any) {
      console.error('AI Explanation Error:', err);
      if (err?.status === 503 || (err?.message && err.message.includes('not configured'))) {
        setAiError(
          'AI analysis is unavailable. Configure the OpenRouter API key in .env to enable this feature.'
        );
      } else {
        setAiError(
          err?.message || 'AI explanation service is temporarily unavailable. Please retry.'
        );
      }
    } finally {
      setExplaining(false);
    }
  };

  const formatDate = (isoStr: string) => {
    try {
      return new Date(isoStr).toLocaleString([], {
        year: 'numeric',
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

  if (loading) {
    return <LoadingState message="Loading incident telemetry & correlation tree..." />;
  }

  if (error || !signal) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => navigate('/signals')}
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Signals
        </button>
        <ErrorState
          title="Signal Not Found"
          message={error || 'The requested incident signal does not exist or has been removed.'}
          onRetry={fetchDetail}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Back Navigation & Breadcrumb */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/signals')}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Signals
        </button>

        {/* Resolve Action Button */}
        {signal.status === 'OPEN' && (
          <button
            onClick={handleResolve}
            disabled={resolving}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition-colors disabled:opacity-50 shadow-sm"
          >
            <CheckCircle2 className="w-4 h-4" />
            {resolving ? 'Resolving Incident...' : 'Resolve Incident'}
          </button>
        )}
      </div>

      {/* Resolution Confirmation Banner */}
      {resolveSuccess && (
        <div className="p-3.5 rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          <span>Incident successfully marked as RESOLVED. Historical telemetry preserved.</span>
        </div>
      )}

      {/* Incident Header Card */}
      <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800/80">
          <div className="space-y-1">
            <div className="text-[11px] font-mono text-indigo-400 font-semibold">
              {signal.signal_key}
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
              {signal.title}
            </h2>
          </div>

          <div className="flex items-center gap-2">
            <SeverityBadge severity={signal.severity} size="md" />
            <StatusBadge status={signal.status} size="md" />
          </div>
        </div>

        {/* Narrative Description */}
        <div className="text-sm text-slate-300 leading-relaxed font-sans bg-slate-950/40 p-4 rounded-lg border border-slate-800/60">
          <span className="text-xs uppercase font-mono tracking-wider text-slate-500 block mb-1">
            Diagnostic Summary
          </span>
          {signal.description}
        </div>

        {/* Telemetry Metadata Pills */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
          <div className="p-3 rounded-lg bg-slate-950/50 border border-slate-800">
            <span className="text-slate-500 text-[10px] uppercase block mb-1 flex items-center gap-1">
              <Server className="w-3 h-3" /> Service
            </span>
            <span className="text-white font-medium">{signal.service}</span>
          </div>

          <div className="p-3 rounded-lg bg-slate-950/50 border border-slate-800">
            <span className="text-slate-500 text-[10px] uppercase block mb-1 flex items-center gap-1">
              <MapPin className="w-3 h-3" /> Region
            </span>
            <span className="text-white font-medium">{signal.region}</span>
          </div>

          <div className="p-3 rounded-lg bg-slate-950/50 border border-slate-800">
            <span className="text-slate-500 text-[10px] uppercase block mb-1 flex items-center gap-1">
              <Clock className="w-3 h-3" /> First Detected
            </span>
            <span className="text-slate-200 text-[11px]">{formatDate(signal.first_detected_at)}</span>
          </div>

          <div className="p-3 rounded-lg bg-slate-950/50 border border-slate-800">
            <span className="text-slate-500 text-[10px] uppercase block mb-1 flex items-center gap-1">
              <Clock className="w-3 h-3" /> Last Detected
            </span>
            <span className="text-slate-200 text-[11px]">{formatDate(signal.last_detected_at)}</span>
          </div>
        </div>
      </div>

      {/* AI Incident Analysis Section */}
      <div className="p-6 rounded-xl border border-indigo-950/60 bg-gradient-to-b from-indigo-950/20 to-slate-900/60 backdrop-blur space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white tracking-tight flex items-center gap-2">
                AI Operational Diagnostics
                <span className="text-[10px] font-mono px-2 py-0.2 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  OpenRouter
                </span>
              </h3>
              <p className="text-xs text-slate-400">
                Automated incident summarization, likely causes, and remediation guidance
              </p>
            </div>
          </div>

          <button
            onClick={handleGenerateAI}
            disabled={explaining}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-colors disabled:opacity-50 shadow-md shadow-indigo-600/20"
          >
            {explaining ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" /> Analyzing Telemetry...
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5" />
                {explanation ? 'Regenerate Analysis' : 'Generate AI Analysis'}
              </>
            )}
          </button>
        </div>

        {/* AI Error Notification */}
        {aiError && (
          <div className="p-3.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="font-semibold block">AI Diagnostic Notice</span>
              <span>{aiError}</span>
            </div>
          </div>
        )}

        {/* AI Explanation Content Box */}
        {explanation && (
          <div className="space-y-4 pt-2 border-t border-slate-800">
            {/* Summary */}
            <div className="p-4 rounded-lg bg-slate-950/60 border border-slate-800 space-y-1">
              <span className="text-[10px] uppercase font-mono tracking-wider text-indigo-400 font-semibold block">
                Executive Incident Overview
              </span>
              <p className="text-xs text-slate-200 leading-relaxed">{explanation.summary}</p>
            </div>

            {/* Likely Causes & Actions Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Likely Causes */}
              <div className="p-4 rounded-lg bg-slate-950/60 border border-slate-800 space-y-2">
                <span className="text-[10px] uppercase font-mono tracking-wider text-amber-400 font-semibold flex items-center gap-1.5">
                  <HelpCircle className="w-3.5 h-3.5" /> Likely Hypotheses (Unconfirmed)
                </span>
                <ul className="space-y-1.5 text-xs text-slate-300 list-disc list-inside">
                  {explanation.likely_causes.map((cause, i) => (
                    <li key={i} className="leading-relaxed">
                      {cause}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Recommended Actions */}
              <div className="p-4 rounded-lg bg-slate-950/60 border border-slate-800 space-y-2">
                <span className="text-[10px] uppercase font-mono tracking-wider text-emerald-400 font-semibold flex items-center gap-1.5">
                  <Wrench className="w-3.5 h-3.5" /> Recommended Remediation Steps
                </span>
                <ul className="space-y-1.5 text-xs text-slate-300 list-disc list-inside">
                  {explanation.recommended_actions.map((act, i) => (
                    <li key={i} className="leading-relaxed">
                      {act}
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* AI Model Attribution */}
            <div className="flex items-center justify-between text-[11px] text-slate-500 font-mono pt-1">
              <span>Model: {explanation.model}</span>
              <span>Generated: {formatDate(explanation.generated_at)}</span>
            </div>
          </div>
        )}
      </div>

      {/* Correlated Anomalies & Timeline Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Correlated Anomalies Table (2 cols on lg) */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white tracking-tight flex items-center gap-2">
              <Layers className="w-4 h-4 text-indigo-400" />
              Correlated Raw Anomalies ({signal.anomalies.length})
            </h3>
            <span className="text-xs text-slate-400 font-mono">
              Aggregated inside 10-min window
            </span>
          </div>

          <div className="space-y-3">
            {signal.anomalies.map((anom) => (
              <div
                key={anom.id || anom.metric}
                className="p-4 rounded-xl border border-slate-800 bg-slate-900/50 space-y-2.5"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-white font-mono">{anom.metric}</span>
                    <span className="text-[11px] px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
                      {anom.anomaly_type}
                    </span>
                  </div>
                  <SeverityBadge severity={anom.severity} size="sm" />
                </div>

                <p className="text-xs text-slate-300">{anom.reason}</p>

                {/* Metric Statistics */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-800/80 font-mono text-[11px]">
                  <div>
                    <span className="text-slate-500 block text-[10px]">Observed</span>
                    <span className="text-white font-semibold">{anom.current_value.toFixed(2)}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">Baseline</span>
                    <span className="text-slate-300">{anom.baseline_value.toFixed(2)}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">Deviation</span>
                    <span
                      className={`font-semibold flex items-center gap-0.5 ${
                        anom.percentage_change > 0 ? 'text-rose-400' : 'text-emerald-400'
                      }`}
                    >
                      <TrendingUp className="w-3 h-3" />
                      {anom.percentage_change > 0 ? '+' : ''}
                      {anom.percentage_change.toFixed(1)}%
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">Z-Score / Iso</span>
                    <span className="text-slate-300">
                      {anom.z_score !== null && anom.z_score !== undefined
                        ? `Z: ${anom.z_score.toFixed(1)}`
                        : anom.isolation_score !== null && anom.isolation_score !== undefined
                        ? `Iso: ${anom.isolation_score.toFixed(3)}`
                        : 'N/A'}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Simple Vertical Timeline (1 col on lg) */}
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-white tracking-tight flex items-center gap-2">
            <Clock className="w-4 h-4 text-indigo-400" />
            Detection Timeline
          </h3>

          <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/50">
            <div className="relative border-l border-slate-800 ml-3 space-y-6">
              {signal.anomalies.map((anom, idx) => (
                <div key={idx} className="relative pl-6">
                  {/* Timeline Node */}
                  <span className="absolute -left-1.5 top-1 w-3 h-3 rounded-full bg-slate-950 border-2 border-indigo-500" />
                  <div className="text-[11px] font-mono text-slate-500">
                    {formatDate(anom.time_window)}
                  </div>
                  <div className="text-xs font-medium text-white mt-0.5">{anom.metric} anomaly</div>
                  <div className="text-[11px] text-slate-400 mt-0.5 line-clamp-2">
                    {anom.reason}
                  </div>
                </div>
              ))}

              {signal.status === 'RESOLVED' && (
                <div className="relative pl-6">
                  <span className="absolute -left-1.5 top-1 w-3 h-3 rounded-full bg-slate-950 border-2 border-emerald-500" />
                  <div className="text-[11px] font-mono text-emerald-400 font-semibold">
                    Incident Resolved
                  </div>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    Updated: {formatDate(signal.updated_at)}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
