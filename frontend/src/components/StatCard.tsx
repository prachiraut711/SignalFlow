import React from 'react';
import { LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtext?: string;
  icon: LucideIcon;
  variant?: 'default' | 'critical' | 'warning' | 'success';
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtext,
  icon: Icon,
  variant = 'default',
}) => {
  const variantStyles = {
    default: {
      border: 'border-slate-800 hover:border-slate-700',
      iconBg: 'bg-indigo-500/10 text-indigo-400',
    },
    critical: {
      border: 'border-rose-900/50 hover:border-rose-800 bg-rose-950/10',
      iconBg: 'bg-rose-500/15 text-rose-400',
    },
    warning: {
      border: 'border-amber-900/50 hover:border-amber-800 bg-amber-950/10',
      iconBg: 'bg-amber-500/15 text-amber-400',
    },
    success: {
      border: 'border-emerald-900/50 hover:border-emerald-800 bg-emerald-950/10',
      iconBg: 'bg-emerald-500/15 text-emerald-400',
    },
  }[variant];

  return (
    <div
      className={`p-5 rounded-xl border bg-slate-900/60 backdrop-blur transition-all duration-200 ${variantStyles.border}`}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
          {title}
        </span>
        <div className={`p-2 rounded-lg ${variantStyles.iconBg}`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className="text-2xl font-bold text-white tracking-tight">{value}</div>
      {subtext && (
        <div className="mt-1 text-xs text-slate-400 flex items-center gap-1">
          {subtext}
        </div>
      )}
    </div>
  );
};
