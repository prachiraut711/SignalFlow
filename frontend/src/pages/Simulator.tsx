import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Play,
  Square,
  Zap,
  Activity,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
  Cpu,
  Layers,
  MapPin,
  Server,
  BarChart3,
  ShieldAlert,
} from 'lucide-react';
import {
  api,
  SimulatorScenarioItem,
  SimulatorStatusResponse,
} from '../lib/api';

const DURATION_PRESETS = [15, 30, 60, 120];

export const Simulator: React.FC = () => {
  const navigate = useNavigate();

  // Catalog state
  const [scenarios, setScenarios] = useState<SimulatorScenarioItem[]>([]);
  const [services, setServices] = useState<string[]>([]);
  const [regions, setRegions] = useState<string[]>([]);
  const [catalogLoaded, setCatalogLoaded] = useState(false);

  // Form Configuration State
  const [selectedScenarioId, setSelectedScenarioId] = useState('payment_failure_spike');
  const [eventsPerSecond, setEventsPerSecond] = useState(10);
  const [durationSeconds, setDurationSeconds] = useState(60);
  const [selectedService, setSelectedService] = useState('payment-service');
  const [selectedRegion, setSelectedRegion] = useState('Pune');

  // Simulation Execution State
  const [status, setStatus] = useState<SimulatorStatusResponse | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pipelineEvalResult, setPipelineEvalResult] = useState<{
    anomalies: number;
    signals: number;
  } | null>(null);
  const [isEvaluating, setIsEvaluating] = useState(false);

  // Polling ref
  const pollTimerRef = useRef<number | null>(null);
  const wasRunningRef = useRef(false);

  // Fetch initial scenario catalog and status
  const fetchInitialData = useCallback(async () => {
    try {
      setError(null);
      const [catRes, statusRes] = await Promise.all([
        api.getSimulatorScenarios(),
        api.getSimulatorStatus(),
      ]);

      setScenarios(catRes.scenarios);
      setServices(catRes.supported_services);
      setRegions(catRes.supported_regions);
      setCatalogLoaded(true);

      setStatus(statusRes);
      wasRunningRef.current = statusRes.running;

      // Auto-populate defaults from initial scenario
      const initialMeta = catRes.scenarios.find((s) => s.id === selectedScenarioId);
      if (initialMeta) {
        setSelectedService(initialMeta.default_service);
        setSelectedRegion(initialMeta.default_region);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to connect to backend simulator service');
    }
  }, [selectedScenarioId]);

  useEffect(() => {
    fetchInitialData();
  }, [fetchInitialData]);

  // Handle scenario dropdown selection change
  const handleScenarioChange = (scenarioId: string) => {
    setSelectedScenarioId(scenarioId);
    const meta = scenarios.find((s) => s.id === scenarioId);
    if (meta) {
      setSelectedService(meta.default_service);
      setSelectedRegion(meta.default_region);
    }
  };

  // Poll simulator status while running
  const pollStatus = useCallback(async () => {
    try {
      const currentStatus = await api.getSimulatorStatus();
      setStatus(currentStatus);

      // Detect transition from running -> completed
      if (wasRunningRef.current && !currentStatus.running) {
        wasRunningRef.current = false;
        // Notify other components via custom event
        window.dispatchEvent(new CustomEvent('signalflow:refresh'));
      } else {
        wasRunningRef.current = currentStatus.running;
      }
    } catch {
      // Non-fatal polling failure
    }
  }, []);

  useEffect(() => {
    if (status?.running) {
      pollTimerRef.current = window.setInterval(pollStatus, 1500);
    } else if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }

    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
      }
    };
  }, [status?.running, pollStatus]);

  // Start Simulation handler
  const handleStart = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsStarting(true);
    setError(null);
    setPipelineEvalResult(null);

    try {
      const startRes = await api.startSimulation({
        scenario: selectedScenarioId,
        events_per_second: Number(eventsPerSecond),
        duration_seconds: Number(durationSeconds),
        service: selectedService,
        region: selectedRegion,
      });
      setStatus(startRes);
      wasRunningRef.current = true;
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to start simulation');
    } finally {
      setIsStarting(false);
    }
  };

  // Stop Simulation handler
  const handleStop = async () => {
    setIsStopping(true);
    setError(null);
    try {
      const stopRes = await api.stopSimulation();
      setStatus(stopRes);
      wasRunningRef.current = false;
      window.dispatchEvent(new CustomEvent('signalflow:refresh'));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to stop simulation');
    } finally {
      setIsStopping(false);
    }
  };

  // Trigger post-simulation pipeline evaluation (detection + correlation)
  const handleEvaluatePipeline = async () => {
    setIsEvaluating(true);
    setError(null);
    try {
      const res = await api.evaluateSimulation();
      setPipelineEvalResult({
        anomalies: res.anomalies_detected,
        signals: res.signals_created + res.signals_updated,
      });
      window.dispatchEvent(new CustomEvent('signalflow:refresh'));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to evaluate pipeline');
    } finally {
      setIsEvaluating(false);
    }
  };

  const selectedMeta = scenarios.find((s) => s.id === selectedScenarioId);
  const isRunning = Boolean(status?.running);
  const progressPercent =
    status && status.duration_seconds > 0
      ? Math.min(100, Math.round((status.elapsed_seconds / status.duration_seconds) * 100))
      : 0;

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
            <Cpu className="w-4 h-4 text-indigo-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">Event Simulator</h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Generate realistic application events and inject operational anomalies through the production ingestion API.
            </p>
          </div>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div className="text-xs text-rose-200">
            <span className="font-semibold">Simulation Error:</span> {error}
          </div>
        </div>
      )}

      {/* Live Simulation Running Banner / Progress Card */}
      {isRunning && (
        <div className="p-6 rounded-2xl bg-slate-900/90 border border-indigo-500/30 shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-indigo-500 via-sky-400 to-indigo-500 animate-pulse" />

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-800">
            <div className="flex items-center gap-3">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
              </span>
              <div>
                <div className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
                  Simulation Active
                </div>
                <h2 className="text-base font-bold text-white capitalize">
                  {status?.scenario?.replace(/_/g, ' ') || 'Running Scenario'}
                </h2>
              </div>
            </div>

            <button
              onClick={handleStop}
              disabled={isStopping}
              className="inline-flex items-center justify-center gap-2 px-4 py-2 text-xs font-semibold text-rose-200 bg-rose-500/10 border border-rose-500/30 hover:bg-rose-500/20 rounded-xl transition-all disabled:opacity-50"
            >
              {isStopping ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Square className="w-3.5 h-3.5 fill-rose-400 text-rose-400" />
              )}
              Stop Simulation
            </button>
          </div>

          {/* Metric Counter Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 my-5">
            <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800/80">
              <div className="text-[11px] text-slate-400 font-medium">Events Dispatched</div>
              <div className="text-2xl font-bold text-white font-mono mt-1">
                {status?.events_generated.toLocaleString()}
              </div>
            </div>

            <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800/80">
              <div className="text-[11px] text-slate-400 font-medium">Elapsed Time</div>
              <div className="text-2xl font-bold text-indigo-400 font-mono mt-1">
                {status?.elapsed_seconds}s{' '}
                <span className="text-xs text-slate-500 font-normal">/ {status?.duration_seconds}s</span>
              </div>
            </div>

            <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800/80">
              <div className="text-[11px] text-slate-400 font-medium">Ingestion Rate</div>
              <div className="text-2xl font-bold text-sky-400 font-mono mt-1">
                {status?.events_per_second} <span className="text-xs text-slate-500 font-normal">eps</span>
              </div>
            </div>

            <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800/80">
              <div className="text-[11px] text-slate-400 font-medium">Target Service & Region</div>
              <div className="text-xs font-semibold text-slate-200 mt-1.5 truncate">
                {status?.service || 'payment-service'}
              </div>
              <div className="text-[10px] text-slate-400 mt-0.5">Region: {status?.region || 'Pune'}</div>
            </div>
          </div>

          {/* Progress Bar & Phase Indicator */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span className="text-slate-400">Phase:</span>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider ${
                    progressPercent < 50
                      ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                      : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                  }`}
                >
                  {progressPercent < 50 ? '1. Baseline Generation (Healthy)' : '2. Anomaly Injection Active'}
                </span>
              </div>
              <span className="font-mono text-slate-400">{progressPercent}%</span>
            </div>

            <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-indigo-500 to-sky-400 transition-all duration-500 ease-out"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Completion & Next Steps Card */}
      {!isRunning && status && status.events_generated > 0 && (
        <div className="p-6 rounded-2xl bg-slate-900/60 border border-emerald-500/20 space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 shrink-0">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">Simulation Completed</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Generated <span className="font-semibold text-emerald-400">{status.events_generated}</span> events{' '}
                  for <span className="font-semibold text-white">{status.service}</span> ({status.region}) via{' '}
                  <code className="text-indigo-400 font-mono text-[11px]">POST /api/events</code>.
                </p>
              </div>
            </div>

            {/* Run Pipeline Evaluation Button */}
            <button
              onClick={handleEvaluatePipeline}
              disabled={isEvaluating}
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-indigo-200 bg-indigo-500/20 border border-indigo-500/30 hover:bg-indigo-500/30 rounded-xl transition-all disabled:opacity-50 shrink-0"
            >
              {isEvaluating ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Zap className="w-3.5 h-3.5 text-indigo-400" />
              )}
              Run Pipeline Scan
            </button>
          </div>

          {/* Evaluation Result Toast */}
          {pipelineEvalResult && (
            <div className="p-3 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center gap-3 text-xs text-indigo-200">
              <ShieldAlert className="w-4 h-4 text-indigo-400 shrink-0" />
              <div>
                Detection Scan Complete:{' '}
                <span className="font-bold text-white">{pipelineEvalResult.anomalies}</span> anomalies detected,{' '}
                <span className="font-bold text-white">{pipelineEvalResult.signals}</span> operational incident signals
                correlated!
              </div>
            </div>
          )}

          {/* Quick Navigation Links */}
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <button
              onClick={() => navigate('/signals')}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
            >
              <Activity className="w-3.5 h-3.5 text-sky-400" />
              View Incident Signals
              <ArrowRight className="w-3 h-3 text-slate-400" />
            </button>

            <button
              onClick={() => navigate('/')}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
            >
              <BarChart3 className="w-3.5 h-3.5 text-emerald-400" />
              Open Dashboard
              <ArrowRight className="w-3 h-3 text-slate-400" />
            </button>

            <button
              onClick={() => navigate('/events')}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
            >
              <Layers className="w-3.5 h-3.5 text-purple-400" />
              Inspect in Event Explorer
              <ArrowRight className="w-3 h-3 text-slate-400" />
            </button>
          </div>
        </div>
      )}

      {/* Simulator Configuration Card */}
      <form onSubmit={handleStart} className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800 space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-white uppercase tracking-wider text-slate-300">
            Simulation Parameters
          </h2>
          <span className="text-[11px] text-slate-500 font-mono">POST /api/events pipeline</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Scenario Selection */}
          <div className="space-y-2 md:col-span-2">
            <label className="text-xs font-medium text-slate-300 flex items-center justify-between">
              <span>Failure Scenario</span>
              {selectedMeta?.expected_anomaly && (
                <span className="text-[10px] text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                  Target: {selectedMeta.expected_anomaly}
                </span>
              )}
            </label>
            <select
              value={selectedScenarioId}
              onChange={(e) => handleScenarioChange(e.target.value)}
              disabled={isRunning || !catalogLoaded}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500 transition-colors disabled:opacity-50"
            >
              {scenarios.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.title}
                </option>
              ))}
            </select>
            {selectedMeta && (
              <p className="text-[11px] text-slate-400 pt-0.5 leading-relaxed">
                {selectedMeta.description}
              </p>
            )}
          </div>

          {/* Target Service */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
              <Server className="w-3.5 h-3.5 text-slate-400" />
              Target Service
            </label>
            <select
              value={selectedService}
              onChange={(e) => setSelectedService(e.target.value)}
              disabled={isRunning || !catalogLoaded}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500 transition-colors disabled:opacity-50"
            >
              {services.map((srv) => (
                <option key={srv} value={srv}>
                  {srv}
                </option>
              ))}
            </select>
          </div>

          {/* Target Region */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5 text-slate-400" />
              Target Region
            </label>
            <select
              value={selectedRegion}
              onChange={(e) => setSelectedRegion(e.target.value)}
              disabled={isRunning || !catalogLoaded}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500 transition-colors disabled:opacity-50"
            >
              {regions.map((reg) => (
                <option key={reg} value={reg}>
                  {reg}
                </option>
              ))}
            </select>
          </div>

          {/* Events Per Second */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs font-medium text-slate-300">
              <label>Events / Second (Rate)</label>
              <span className="font-mono text-indigo-400 font-semibold">{eventsPerSecond} eps</span>
            </div>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={1}
                max={50}
                value={eventsPerSecond}
                onChange={(e) => setEventsPerSecond(Number(e.target.value))}
                disabled={isRunning}
                className="flex-1 accent-indigo-500 bg-slate-950"
              />
              <input
                type="number"
                min={1}
                max={50}
                value={eventsPerSecond}
                onChange={(e) => setEventsPerSecond(Math.max(1, Math.min(50, Number(e.target.value))))}
                disabled={isRunning}
                className="w-16 bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5 text-xs text-center text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
            <p className="text-[10px] text-slate-500">Safe execution range: 1 to 50 events/sec</p>
          </div>

          {/* Duration */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs font-medium text-slate-300">
              <label>Duration (Seconds)</label>
              <span className="font-mono text-indigo-400 font-semibold">{durationSeconds}s</span>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min={5}
                max={300}
                value={durationSeconds}
                onChange={(e) => setDurationSeconds(Math.max(5, Math.min(300, Number(e.target.value))))}
                disabled={isRunning}
                className="w-24 bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
              {/* Presets */}
              <div className="flex items-center gap-1.5">
                {DURATION_PRESETS.map((p) => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => setDurationSeconds(p)}
                    disabled={isRunning}
                    className={`px-2.5 py-1.5 text-[11px] rounded-lg border transition-colors ${
                      durationSeconds === p
                        ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40'
                        : 'bg-slate-950 text-slate-400 border-slate-800 hover:bg-slate-800'
                    }`}
                  >
                    {p}s
                  </button>
                ))}
              </div>
            </div>
            <p className="text-[10px] text-slate-500">Safe execution range: 5 to 300 seconds</p>
          </div>
        </div>

        {/* Action Button */}
        <div className="pt-2 flex items-center justify-end">
          <button
            type="submit"
            disabled={isRunning || isStarting || !catalogLoaded}
            className="inline-flex items-center gap-2 px-6 py-2.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl transition-all shadow-lg shadow-indigo-600/20 disabled:opacity-50 disabled:pointer-events-none"
          >
            {isStarting ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4 fill-white" />
            )}
            Start Simulation
          </button>
        </div>
      </form>

      {/* Production Pipeline Architecture Explanation */}
      <div className="p-4 rounded-xl bg-slate-900/30 border border-slate-800/60 text-slate-400 text-xs space-y-2">
        <div className="font-semibold text-slate-300 flex items-center gap-2">
          <Zap className="w-3.5 h-3.5 text-indigo-400" />
          End-to-End Production Ingestion Flow
        </div>
        <p className="text-[11px] leading-relaxed">
          The event simulator dispatches events through the standard FastAPI ingestion endpoint (
          <code className="text-slate-300 font-mono">POST /api/events</code>). Telemetry is buffered in Redis Streams,
          stream-consumed by the EventWorker into DuckDB, scanned by Statistical and Isolation Forest detectors, and
          correlated into operational signals displayed in real time on the dashboard.
        </p>
      </div>
    </div>
  );
};
