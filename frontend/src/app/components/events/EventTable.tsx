'use client';

import { EventListItem } from '@/app/lib/api';
import Link from 'next/link';
import { EVENT_STATUSES, EVENT_PRIORITIES } from '@/app/data/events';
import StaffingProgress from './StaffingProgress';

interface EventTableProps {
  events: EventListItem[];
  sortBy: string;
  sortOrder: 'asc' | 'desc';
  onSort: (field: string) => void;
}

const STATUS_STYLES: Record<string, string> = {
  PLANNED: 'bg-blue-50 text-blue-700 border-blue-200',
  STAFFING: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  CONFIRMED: 'bg-green-50 text-green-700 border-green-200',
  IN_PROGRESS: 'bg-purple-50 text-purple-700 border-purple-200',
  COMPLETED: 'bg-gray-50 text-gray-700 border-gray-200',
  CANCELLED: 'bg-red-50 text-red-700 border-red-200',
};

const PRIORITY_STYLES: Record<string, string> = {
  NORMAL: 'bg-gray-50 text-gray-700 border-gray-200',
  HIGH: 'bg-orange-50 text-orange-700 border-orange-200',
  CRITICAL: 'bg-red-50 text-red-700 border-red-200',
};

function SortIcon({ field, active, order }: { field: string; active: boolean; order: 'asc' | 'desc' }) {
  if (!active) return <span className="text-gray-300 ml-1">↕</span>;
  return <span className="text-[#D4AF37] ml-1">{order === 'asc' ? '↑' : '↓'}</span>;
}

export default function EventTable({ events, sortBy, sortOrder, onSort }: EventTableProps) {
  if (events.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm">
        <p className="text-gray-500 text-sm">Aucun événement ne correspond à ces critères.</p>
        <p className="text-gray-400 text-xs mt-1">Essayez de modifier ou réinitialiser vos filtres.</p>
      </div>
    );
  }

  const header = (label: string, field: string) => (
    <th
      className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider cursor-pointer hover:text-[#D4AF37] select-none"
      onClick={() => onSort(field)}
    >
      <div className="flex items-center">
        {label}
        <SortIcon field={field} active={sortBy === field} order={sortOrder} />
      </div>
    </th>
  );

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' });
  };

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {header('Événement', 'name')}
              {header('Ville', 'city')}
              {header('Date', 'start_datetime')}
              {header('Invités', 'guest_count')}
              {header('Statut', 'status')}
              {header('Priorité', 'priority')}
              {header('Staffing', 'staffing')}
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {events.map((event) => {
              const staffing = event.staffing || { requested: 0, selected: 0, missing: 0, percentage: 0 };
              const percentage = staffing.percentage;

              return (
                <tr key={event.id} className="hover:bg-gray-50/50 transition-colors">
                  <td className="px-4 py-4 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{event.name}</p>
                        {event.urgent && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-50 text-red-700 border border-red-200 mt-1">
                            URGENT
                          </span>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-700">{event.city}</td>
                  <td className="px-4 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{formatDate(event.start_datetime)}</div>
                    <div className="text-xs text-gray-500">{formatTime(event.start_datetime)}</div>
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-700">{event.guest_count}</td>
                  <td className="px-4 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${STATUS_STYLES[event.status] || 'bg-gray-50 text-gray-700'}`}>
                      {EVENT_STATUSES[event.status as keyof typeof EVENT_STATUSES] || event.status}
                    </span>
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${PRIORITY_STYLES[event.priority] || 'bg-gray-50 text-gray-700'}`}>
                      {EVENT_PRIORITIES[event.priority as keyof typeof EVENT_PRIORITIES] || event.priority}
                    </span>
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap">
                    <div className="w-32">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-gray-500">{staffing.selected} / {staffing.requested}</span>
                        <span className="text-xs font-medium text-gray-700">{percentage}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-1.5 overflow-hidden">
                        <div
                          className={`h-1.5 rounded-full transition-all duration-500 ${
                            percentage === 100 ? 'bg-green-500' : percentage >= 50 ? 'bg-[#D4AF37]' : 'bg-red-500'
                          }`}
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm">
                    <Link
                      href={`/dashboard/events/${event.id}`}
                      className="text-[#D4AF37] hover:text-[#B8941E] font-medium"
                    >
                      Voir
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
