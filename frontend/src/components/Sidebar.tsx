import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  AlertOctagon,
  Activity,
  Server,
  X,
  Radio,
  Database,
  Cpu,
} from 'lucide-react';
import { HealthResponse, RedisHealthResponse } from '../lib/api';

interface SidebarProps {
  backendHealth: HealthResponse | null;
  redisHealth: RedisHealthResponse | null;
  isOpenMobile?: boolean;
  onCloseMobile?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  backendHealth,
  redisHealth,
  isOpenMobile = false,
  onCloseMobile,
}) => {
  const isBackendHealthy = backendHealth?.status === 'healthy';
  const isRedisHealthy = redisHealth?.status === 'healthy';

  const navItems = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/signals', label: 'Signals', icon: AlertOctagon },
    { to: '/events', label: 'Event Explorer', icon: Activity },
    { to: '/services', label: 'Service Explorer', icon: Server },
  ];

  const sidebarContent = (
    <div className="flex flex-col h-full bg-slate-950 border-r border-slate-800 w-64 select-none">
      {/* Brand Header */}
      <div className="flex items-center justify-between px-6 py-5 border-b border-slate-800/80">
        <NavLink to="/" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-lg shadow-indigo-600/30">
            <Radio className="w-4 h-4" />
          </div>
          <div>
            <div className="text-sm font-bold text-white tracking-tight flex items-center gap-1.5">
              SignalFlow
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-400 font-semibold border border-indigo-500/30">
                v0.1
              </span>
            </div>
            <div className="text-[11px] text-slate-400 font-medium">Event Intelligence</div>
          </div>
        </NavLink>
        {onCloseMobile && (
          <button
            onClick={onCloseMobile}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg md:hidden"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <div className="px-3 pb-2 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
          Platform
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              onClick={onCloseMobile}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-indigo-600/15 text-indigo-400 border border-indigo-500/30 font-semibold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`
              }
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* System Status Footer */}
      <div className="p-4 border-t border-slate-800/80 bg-slate-900/30">
        <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2.5">
          System Infrastructure
        </div>
        <div className="space-y-2 text-xs">
          {/* Backend Status */}
          <div className="flex items-center justify-between text-slate-300">
            <span className="flex items-center gap-2">
              <Cpu className="w-3.5 h-3.5 text-slate-400" />
              FastAPI Core
            </span>
            <span
              className={`flex items-center gap-1 font-mono text-[11px] ${
                isBackendHealthy ? 'text-emerald-400' : 'text-rose-400'
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  isBackendHealthy ? 'bg-emerald-500' : 'bg-rose-500'
                }`}
              />
              {isBackendHealthy ? 'Online' : 'Offline'}
            </span>
          </div>

          {/* Redis Buffer Status */}
          <div className="flex items-center justify-between text-slate-300">
            <span className="flex items-center gap-2">
              <Database className="w-3.5 h-3.5 text-slate-400" />
              Redis Streams
            </span>
            <span
              className={`flex items-center gap-1 font-mono text-[11px] ${
                isRedisHealthy ? 'text-emerald-400' : 'text-rose-400'
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  isRedisHealthy ? 'bg-emerald-500' : 'bg-rose-500'
                }`}
              />
              {isRedisHealthy ? 'Active' : 'Degraded'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Persistent Sidebar */}
      <aside className="hidden md:flex flex-shrink-0 h-screen sticky top-0">
        {sidebarContent}
      </aside>

      {/* Mobile Drawer Backdrop & Sidebar */}
      {isOpenMobile && (
        <div className="fixed inset-0 z-50 flex md:hidden">
          <div
            className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm transition-opacity"
            onClick={onCloseMobile}
          />
          <div className="relative z-50 flex">{sidebarContent}</div>
        </div>
      )}
    </>
  );
};
