
import React from 'react';
import { LakeData } from '../types';

interface LakeDashboardProps {
  data: LakeData;
}

const StatCard: React.FC<{ label: string; value: string | number; unit?: string; color: string }> = ({ label, value, unit, color }) => (
  <div className="bg-white dark:bg-slate-800/50 backdrop-blur-md border border-slate-200 dark:border-slate-700 p-4 rounded-2xl shadow-sm dark:shadow-lg transition-all duration-300">
    <p className="text-slate-500 dark:text-slate-400 text-xs font-medium uppercase tracking-wider mb-1">{label}</p>
    <div className="flex items-baseline gap-1">
      <span className={`text-2xl font-bold ${color}`}>{value}</span>
      {unit && <span className="text-slate-400 dark:text-slate-500 text-sm font-medium">{unit}</span>}
    </div>
  </div>
);

export const LakeDashboard: React.FC<LakeDashboardProps> = ({ data }) => {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 w-full max-w-4xl mx-auto mb-8">
      <StatCard label="Temperature" value={data.temperature} unit="°C" color="text-orange-500 dark:text-orange-400" />
      <StatCard label="pH Level" value={data.ph} unit="pH" color="text-green-600 dark:text-green-400" />
      <StatCard label="Turbidity" value={data.turbidity} unit="NTU" color="text-blue-600 dark:text-blue-400" />
      <StatCard label="Oxygen (DO)" value={data.dissolvedOxygen} unit="mg/L" color="text-emerald-600 dark:text-emerald-400" />
    </div>
  );
};
