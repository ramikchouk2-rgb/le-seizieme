'use client';

import { parseBackendDateTime } from '@/app/lib/datetime';

interface AvailabilitySummaryProps {
  items: {
    id: string;
    start_datetime: string;
    end_datetime: string;
    status: string;
    conflict: boolean;
    conflict_reason?: string | null;
  }[];
}

export default function AvailabilitySummary({ items }: AvailabilitySummaryProps) {
  const upcoming = items.filter((item) => {
    const endDate = parseBackendDateTime(item.end_datetime);
    return endDate && endDate >= new Date();
  });
  const conflicts = items.filter((item) => item.conflict);
  const availableHours = upcoming
    .filter((item) => item.status === 'AVAILABLE')
    .reduce((acc, item) => {
      const start = parseBackendDateTime(item.start_datetime);
      const end = parseBackendDateTime(item.end_datetime);
      if (!start || !end) return acc;
      return acc + (end.getTime() - start.getTime()) / (1000 * 60 * 60);
    }, 0);

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Disponibilités à venir</p>
        <p className="text-2xl font-bold text-gray-900">{upcoming.length}</p>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Heures disponibles</p>
        <p className="text-2xl font-bold text-gray-900">{Math.round(availableHours)}h</p>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Conflits</p>
        <p className="text-2xl font-bold text-red-600">{conflicts.length}</p>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Total périodes</p>
        <p className="text-2xl font-bold text-gray-900">{items.length}</p>
      </div>
    </div>
  );
}
