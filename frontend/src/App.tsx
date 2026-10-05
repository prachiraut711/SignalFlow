import React, { useEffect, useState } from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import { 
  Activity, 
  Radio, 
  Cpu, 
  Database, 
  ShieldAlert, 
  CheckCircle2, 
  RefreshCw, 
  ExternalLink,
  Terminal,
  Sparkles
} from 'lucide-react';

interface HealthData {
  status: string;
  service: string;
}

const StarterHome: React.FC = () => {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const checkHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      // Calls /health endpoint (proxied through Vite in dev to backend:8000)
      const res = await fetch('/health');
      if (!res.ok) {
        throw new Error(`HTTP error ${res.status}`);
      }
      const data: HealthData = await res.json();
      setHealth(data);
    } catch (err: any) {
      setError(err?.message || 'Unable to connect to backend');
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-indigo-500 selection:text-white">
      {/* Top Navbar */}
      <header className="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-sky-400 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Activity className="w-6 h-6 text-white" />
            </div>
            <div>
              <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                SignalFlow
              </span>
              <span className="ml-2 text-xs font-mono uppercase px-2 py-0.5 rounded-full bg-indigo-950/80 text-indigo-300 border border-indigo-800/60">
                v0.1.0
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <div className="hidden sm:flex items-center space-x-2 text-xs font-mono px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-900">
              <span className="text-slate-400">Backend API:</span>
              {loading ? (
                <span className="flex items-center text-amber-400">
                  <RefreshCw className="w-3 h-3 mr-1 animate-spin" /> Checking
                </span>
              ) : health?.status === 'healthy' ? (
                <span className="flex items-center text-emerald-400">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse mr-1.5"></span>
                  Healthy
                </span>
              ) : (
                <span className="flex items-center text-rose-400">
                  <span className="w-2 h-2 rounded-full bg-rose-400 mr-1.5"></span>
                  Offline
                </span>
              )}
            </div>

            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs font-medium px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition flex items-center shadow-sm"
            >
              API Docs
              <ExternalLink className="w-3.5 h-3.5 ml-1.5 opacity-70" />
            </a>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-16 flex flex-col justify-center">
        <div className="text-center max-w-3xl mx-auto space-y-6">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full border border-indigo-500/30 bg-indigo-950/40 text-indigo-300 text-xs font-medium tracking-wide">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            <span>Phase 1 — Project Foundation Established</span>
          </div>

          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-tight sm:leading-none">
            SignalFlow
          </h1>

          <p className="text-xl sm:text-2xl font-medium text-indigo-200/90 tracking-tight">
            Application Event Intelligence & Anomaly Detection Platform
          </p>

          <p className="text-sm sm:text-base text-slate-400 leading-relaxed max-w-2xl mx-auto">
            A resilient full-stack platform designed to capture real-time business telemetry,
            detect operational spikes and failures with ML & statistical baselines, and provide
            diagnostic intelligence for modern distributed architectures.
          </p>

          {/* Quick Health Card */}
          <div className="pt-4">
            <div className="inline-block p-4 sm:p-5 rounded-2xl border border-slate-800 bg-slate-900/80 shadow-2xl backdrop-blur max-w-md w-full text-left">
              <div className="flex items-center justify-between mb-3 pb-3 border-b border-slate-800">
                <span className="text-xs font-mono text-slate-400 uppercase tracking-wider flex items-center">
                  <Terminal className="w-3.5 h-3.5 mr-1.5 text-indigo-400" />
                  Backend Health Status
                </span>
                <button
                  onClick={checkHealth}
                  disabled={loading}
                  className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center font-mono focus:outline-none"
                  title="Recheck Health"
                >
                  <RefreshCw className={`w-3 h-3 mr-1 ${loading ? 'animate-spin' : ''}`} />
                  Refresh
                </button>
              </div>

              {loading ? (
                <div className="py-2 text-xs text-slate-400 flex items-center">
                  <RefreshCw className="w-3.5 h-3.5 animate-spin mr-2 text-indigo-400" />
                  Connecting to http://localhost:8000/health...
                </div>
              ) : health ? (
                <div className="space-y-1.5 font-mono text-xs">
                  <div className="flex items-center justify-between text-slate-300">
                    <span>Service:</span>
                    <span className="text-indigo-300 font-semibold">{health.service}</span>
                  </div>
                  <div className="flex items-center justify-between text-slate-300">
                    <span>Status:</span>
                    <span className="text-emerald-400 font-semibold flex items-center">
                      <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-400" />
                      {health.status}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="text-xs font-mono text-rose-400/90 py-1">
                  Offline ({error || 'Backend not running'})
                  <div className="text-[11px] text-slate-500 mt-1">
                    Start backend via: <code className="text-slate-300">uvicorn app.main:app --reload</code>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Planned Architecture Grid */}
        <div className="mt-20">
          <div className="text-center mb-8">
            <h2 className="text-xs font-mono uppercase tracking-widest text-slate-400">
              Planned Platform Architecture & Core Modules
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Feature 1 */}
            <div className="p-6 rounded-2xl border border-slate-800/80 bg-slate-900/40 hover:border-slate-700/80 transition group">
              <div className="w-10 h-10 rounded-xl bg-indigo-950/80 border border-indigo-800/50 flex items-center justify-center mb-4 text-indigo-400 group-hover:scale-105 transition">
                <Radio className="w-5 h-5" />
              </div>
              <div className="flex items-center justify-between mb-1.5">
                <h3 className="font-semibold text-white text-base">Event Ingestion</h3>
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                  Planned
                </span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Buffered ingestion via Redis Streams, handling bursts with consumer group distribution and zero data drop.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="p-6 rounded-2xl border border-slate-800/80 bg-slate-900/40 hover:border-slate-700/80 transition group">
              <div className="w-10 h-10 rounded-xl bg-purple-950/80 border border-purple-800/50 flex items-center justify-center mb-4 text-purple-400 group-hover:scale-105 transition">
                <ShieldAlert className="w-5 h-5" />
              </div>
              <div className="flex items-center justify-between mb-1.5">
                <h3 className="font-semibold text-white text-base">Anomaly Detection</h3>
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                  Planned
                </span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Z-score sliding-window thresholding and Isolation Forests to detect anomalous error spikes and payment failures.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="p-6 rounded-2xl border border-slate-800/80 bg-slate-900/40 hover:border-slate-700/80 transition group">
              <div className="w-10 h-10 rounded-xl bg-sky-950/80 border border-sky-800/50 flex items-center justify-center mb-4 text-sky-400 group-hover:scale-105 transition">
                <Database className="w-5 h-5" />
              </div>
              <div className="flex items-center justify-between mb-1.5">
                <h3 className="font-semibold text-white text-base">Dual Storage</h3>
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                  Planned
                </span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                PostgreSQL for durable transactional metadata combined with embedded DuckDB for ultra-fast columnar analytical queries.
              </p>
            </div>

            {/* Feature 4 */}
            <div className="p-6 rounded-2xl border border-slate-800/80 bg-slate-900/40 hover:border-slate-700/80 transition group">
              <div className="w-10 h-10 rounded-xl bg-emerald-950/80 border border-emerald-800/50 flex items-center justify-center mb-4 text-emerald-400 group-hover:scale-105 transition">
                <Cpu className="w-5 h-5" />
              </div>
              <div className="flex items-center justify-between mb-1.5">
                <h3 className="font-semibold text-white text-base">AI Root-Cause</h3>
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                  Planned
                </span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Gemini integration to parse anomaly clusters and summarize actionable incident root-cause explanations.
              </p>
            </div>
          </div>
        </div>

        {/* Tech Stack Badges */}
        <div className="mt-16 pt-8 border-t border-slate-900 flex flex-wrap items-center justify-center gap-2">
          {[
            'React 18',
            'TypeScript',
            'Vite',
            'Tailwind CSS',
            'Python 3.12',
            'FastAPI',
            'PostgreSQL',
            'Redis Streams',
            'DuckDB',
            'Docker Compose',
          ].map((tech) => (
            <span
              key={tech}
              className="text-xs font-mono px-3 py-1 rounded-md bg-slate-900 text-slate-400 border border-slate-800/70"
            >
              {tech}
            </span>
          ))}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 py-6 text-center text-xs text-slate-600">
        <p>SignalFlow Platform • Portfolio Engineering Project • Designed for Clarity & Scale</p>
      </footer>
    </div>
  );
};

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<StarterHome />} />
      <Route
        path="*"
        element={
          <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-4">
            <h1 className="text-3xl font-bold mb-2">404 - Page Not Found</h1>
            <Link to="/" className="text-indigo-400 hover:underline text-sm font-mono">
              Return to SignalFlow Home
            </Link>
          </div>
        }
      />
    </Routes>
  );
}
