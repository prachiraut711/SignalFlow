import React, { useState, useEffect, useCallback } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { api, HealthResponse, RedisHealthResponse } from '../lib/api';

export const Layout: React.FC = () => {
  const location = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [backendHealth, setBackendHealth] = useState<HealthResponse | null>(null);
  const [redisHealth, setRedisHealth] = useState<RedisHealthResponse | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchHealth = useCallback(async () => {
    try {
      const bh = await api.getHealth();
      setBackendHealth(bh);
    } catch {
      setBackendHealth({ status: 'unhealthy', service: 'signalflow-backend' });
    }

    try {
      const rh = await api.getRedisHealth();
      setRedisHealth(rh);
    } catch {
      setRedisHealth({ status: 'unhealthy', service: 'redis' });
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000); // Poll health every 30s
    return () => clearInterval(interval);
  }, [fetchHealth]);

  const handleManualRefresh = async () => {
    setIsRefreshing(true);
    await fetchHealth();
    // Dispatch custom event so active pages can refresh their data on click
    window.dispatchEvent(new CustomEvent('signalflow:refresh'));
    setTimeout(() => setIsRefreshing(false), 500);
  };

  // Compute page titles based on current route
  const pageMeta = (() => {
    if (location.pathname === '/') {
      return {
        title: 'Platform Overview',
        subtitle: 'Real-time telemetry, operational aggregates, and detected incidents',
      };
    }
    if (location.pathname.startsWith('/signals/')) {
      return {
        title: 'Incident Analysis',
        subtitle: 'Correlated metric telemetry, anomaly timeline, and AI diagnostic guidance',
      };
    }
    if (location.pathname === '/signals') {
      return {
        title: 'Incident Signals',
        subtitle: 'Aggregated operational events grouped by service, region, and sliding window',
      };
    }
    if (location.pathname === '/events') {
      return {
        title: 'Event Explorer',
        subtitle: 'Inspect raw analytical events ingested across distributed services',
      };
    }
    if (location.pathname === '/services') {
      return {
        title: 'Service Explorer',
        subtitle: 'Service-level throughput, latency distributions, and health states',
      };
    }
    return {
      title: 'SignalFlow Platform',
      subtitle: 'Business Event Intelligence & Anomaly Detection',
    };
  })();

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-indigo-500/30 selection:text-indigo-200">
      {/* Sidebar */}
      <Sidebar
        backendHealth={backendHealth}
        redisHealth={redisHealth}
        isOpenMobile={isMobileMenuOpen}
        onCloseMobile={() => setIsMobileMenuOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header
          title={pageMeta.title}
          subtitle={pageMeta.subtitle}
          backendHealth={backendHealth}
          onRefresh={handleManualRefresh}
          isRefreshing={isRefreshing}
          onToggleMobileMenu={() => setIsMobileMenuOpen((prev) => !prev)}
        />
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
