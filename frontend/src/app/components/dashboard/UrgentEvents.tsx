'use client';

import { EventListItem } from '@/app/lib/api';

interface UrgentEventsProps {
  events: EventListItem[];
  loading?: boolean;
}

export default function UrgentEvents({ events, loading = false }: UrgentEventsProps) {
  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Événements urgents</h3>
        <p className="text-gray-500 text-sm">Chargement...</p>
      </div>
    );
  }

  if (!events || events.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Événements urgents</h3>
        <p className="text-gray-500 text-sm">Aucun événement urgent en cours.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Événements urgents</h3>
      <div className="space-y-4">
        {events.map((event) => (
          <div key={event.id} className="p-4 rounded-lg bg-red-50/50 border border-red-100">
            <div className="flex items-start justify-between mb-2">
              <div>
                <h4 className="font-semibold text-gray-900 text-sm">{event.name}</h4>
                <p className="text-xs text-gray-500 mt-0.5">{event.city}</p>
              </div>
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-700 border border-red-200">
                URGENT
              </span>
            </div>

            <div className="grid grid-cols-3 gap-2 mt-3">
              <div className="text-center">
                <p className="text-lg font-bold text-gray-900">{event.staffing?.requested || 0}</p>
                <p className="text-xs text-gray-500">Requis</p>
              </div>
              <div className="text-center">
                <p className="text-lg font-bold text-green-600">{event.staffing?.selected || 0}</p>
                <p className="text-xs text-gray-500">Confirmés</p>
              </div>
              <div className="text-center">
                <p className="text-lg font-bold text-amber-600">{event.staffing?.missing || 0}</p>
                <p className="text-xs text-gray-500">Manquants</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
