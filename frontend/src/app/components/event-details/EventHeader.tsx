'use client';

import Link from 'next/link';
import { Event } from '@/app/components/dashboard/types';
import { EVENT_STATUSES, EVENT_PRIORITIES } from '@/app/data/events';

interface EventHeaderProps {
  event: Event;
}

export default function EventHeader({ event }: EventHeaderProps) {
  return (
    <div className="mb-8">
      <Link
        href="/dashboard/events"
        className="inline-flex items-center text-sm text-gray-500 hover:text-[#D4AF37] mb-4 transition-colors"
      >
        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Retour aux événements
      </Link>

      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 mb-1">{event.name}</h1>
          <p className="text-sm text-gray-500">{event.city}</p>
          <div className="flex items-center gap-2 mt-2">
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
              event.status === 'PLANNED' ? 'bg-blue-50 text-blue-700 border-blue-200' :
              event.status === 'STAFFING' ? 'bg-indigo-50 text-indigo-700 border-indigo-200' :
              event.status === 'CONFIRMED' ? 'bg-green-50 text-green-700 border-green-200' :
              event.status === 'IN_PROGRESS' ? 'bg-purple-50 text-purple-700 border-purple-200' :
              event.status === 'COMPLETED' ? 'bg-gray-50 text-gray-700 border-gray-200' :
              'bg-red-50 text-red-700 border-red-200'
            }`}>
              {EVENT_STATUSES[event.status as keyof typeof EVENT_STATUSES] || event.status}
            </span>
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
              event.priority === 'NORMAL' ? 'bg-gray-50 text-gray-700 border-gray-200' :
              event.priority === 'HIGH' ? 'bg-orange-50 text-orange-700 border-orange-200' :
              'bg-red-50 text-red-700 border-red-200'
            }`}>
              {EVENT_PRIORITIES[event.priority as keyof typeof EVENT_PRIORITIES] || event.priority}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            disabled
            className="px-4 py-2 bg-white text-gray-700 text-sm font-medium rounded-lg border border-gray-200 opacity-50 cursor-not-allowed"
            title="Bientôt disponible"
          >
            Recommander l'équipe
          </button>
          <button
            disabled
            className="px-4 py-2 bg-white text-gray-700 text-sm font-medium rounded-lg border border-gray-200 opacity-50 cursor-not-allowed"
            title="Bientôt disponible"
          >
            Recommander le transport
          </button>
          {event.urgent ? (
            <button
              disabled
              className="px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg opacity-50 cursor-not-allowed"
              title="Bientôt disponible"
            >
              Lancer les offres urgentes
            </button>
          ) : (
            <button
              disabled
              className="px-4 py-2 bg-gray-200 text-gray-500 text-sm font-medium rounded-lg cursor-not-allowed"
              title="Disponible uniquement pour les événements urgents"
            >
              Offres urgentes indisponibles
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
