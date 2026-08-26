'use client';

import { EventListItem } from '@/app/lib/api';
import Link from 'next/link';
import { EVENT_STATUSES, EVENT_PRIORITIES } from '@/app/data/events';
import StaffingProgress from './StaffingProgress';

interface EventCardProps {
  event: EventListItem;
}

export default function EventCard({ event }: EventCardProps) {
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' });
  };

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  };

  const requested = event.staffing?.requested ?? 0;
  const selected = event.staffing?.selected ?? 0;
  const missing = event.staffing?.missing ?? 0;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-gray-900 truncate">{event.name}</h3>
          <p className="text-xs text-gray-500 mt-0.5">{event.city}</p>
        </div>
        <div className="flex items-center gap-2 ml-3">
          {event.urgent && (
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-50 text-red-700 border border-red-200">
              URGENT
            </span>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 mb-3">
        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
          event.status === 'PLANNED' ? 'bg-blue-50 text-blue-700 border-blue-200' :
          event.status === 'STAFFING' ? 'bg-indigo-50 text-indigo-700 border-indigo-200' :
          event.status === 'CONFIRMED' ? 'bg-green-50 text-green-700 border-green-200' :
          event.status === 'IN_PROGRESS' ? 'bg-purple-50 text-purple-700 border-purple-200' :
          event.status === 'COMPLETED' ? 'bg-gray-50 text-gray-700 border-gray-200' :
          'bg-red-50 text-red-700 border-red-200'
        }`}>
          {EVENT_STATUSES[event.status as keyof typeof EVENT_STATUSES] || event.status}
        </span>
        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
          event.priority === 'NORMAL' ? 'bg-gray-50 text-gray-700 border-gray-200' :
          event.priority === 'HIGH' ? 'bg-orange-50 text-orange-700 border-orange-200' :
          'bg-red-50 text-red-700 border-red-200'
        }`}>
          {EVENT_PRIORITIES[event.priority as keyof typeof EVENT_PRIORITIES] || event.priority}
        </span>
      </div>

      <div className="space-y-2 text-xs text-gray-600 mb-4">
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <span>{formatDate(event.start_datetime)} · {formatTime(event.start_datetime)}</span>
        </div>
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
          <span>{event.guest_count} invités</span>
        </div>
      </div>

      <div className="mb-4">
        <StaffingProgress requested={requested} selected={selected} missing={missing} showLabel={true} />
      </div>

      <Link
        href={`/dashboard/events/${event.id}`}
        className="block w-full py-2 px-4 bg-[#D4AF37] text-white text-sm font-medium rounded-lg hover:bg-[#B8941E] transition-colors text-center"
      >
        Voir
      </Link>
    </div>
  );
}
