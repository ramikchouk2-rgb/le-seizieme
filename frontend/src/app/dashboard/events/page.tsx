'use client';

import { useState, useCallback } from 'react';
import Link from 'next/link';
import Header from '@/app/components/dashboard/Header';
import EventFiltersComponent from '@/app/components/events/EventFilters';
import EventTable from '@/app/components/events/EventTable';
import EventCard from '@/app/components/events/EventCard';
import Pagination from '@/app/components/servers/Pagination';
import { DEFAULT_EVENT_FILTERS } from '@/app/data/events';
import { EventFilters as EventFiltersType } from '@/app/components/dashboard/types';
import { useEvents, useEventStats } from '@/app/lib/hooks';
import { Spinner } from '@/app/lib/loading';

const PAGE_SIZE = 10;

export default function EventsPage() {
  const [filters, setFilters] = useState<EventFiltersType>(DEFAULT_EVENT_FILTERS);
  const [page, setPage] = useState(1);

  const { data: stats, isLoading: statsLoading } = useEventStats();
  const { data: eventsData, isLoading: eventsLoading, error: eventsError, refetch: refetchEvents } = useEvents({
    search: filters.search || undefined,
    city: filters.city || undefined,
    status: filters.status || undefined,
    priority: filters.priority || undefined,
    urgent: filters.urgent === 'urgent' ? true : filters.urgent === 'normal' ? false : undefined,
    staffing: filters.staffing || undefined,
    date_range: filters.dateRange || undefined,
    sort_by: filters.sort_by,
    sort_order: filters.sort_order,
    page,
    page_size: PAGE_SIZE,
  });

  const events = eventsData?.items ?? [];
  const total = eventsData?.total ?? 0;
  const totalPages = eventsData?.total_pages ?? 1;
  const error = eventsError?.message ?? null;

  const handleSort = useCallback((field: string) => {
    setFilters((prev) => ({
      ...prev,
      sort_by: field,
      sort_order: prev.sort_by === field && prev.sort_order === 'asc' ? 'desc' : 'asc',
    }));
    setPage(1);
  }, []);

  const handleReset = useCallback(() => {
    setFilters(DEFAULT_EVENT_FILTERS);
    setPage(1);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <Header title="Événements" />
      <main className="p-8">
        <div className="max-w-7xl mx-auto">
          <p className="text-gray-600 mb-6">
            Gérez vos événements, planifiez le staffing et suivez les opérations.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
              <p className="text-sm font-medium text-gray-500 mb-1">Total événements</p>
              <div className="text-2xl font-bold text-gray-900">
                {statsLoading ? <Spinner size="sm" /> : (stats?.total_events ?? 0)}
              </div>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
              <p className="text-sm font-medium text-gray-500 mb-1">Planifiés</p>
              <div className="text-2xl font-bold text-blue-600">
                {statsLoading ? <Spinner size="sm" /> : (stats?.planned_events ?? 0)}
              </div>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
              <p className="text-sm font-medium text-gray-500 mb-1">En cours</p>
              <div className="text-2xl font-bold text-purple-600">
                {statsLoading ? <Spinner size="sm" /> : (stats?.in_progress_events ?? 0)}
              </div>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
              <p className="text-sm font-medium text-gray-500 mb-1">Urgents</p>
              <div className="text-2xl font-bold text-red-600">
                {statsLoading ? <Spinner size="sm" /> : (stats?.urgent_events ?? 0)}
              </div>
            </div>
          </div>

          <EventFiltersComponent filters={filters} onChange={setFilters} onReset={handleReset} resultCount={total} />

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 text-sm text-red-700 flex items-center justify-between">
              <span>{error}</span>
              <button onClick={() => refetchEvents()} className="underline font-medium">
                Réessayer
              </button>
            </div>
          )}

          {eventsLoading ? (
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm">
              <Spinner size="lg" className="mx-auto mb-4 text-[#D4AF37]" />
              <p className="text-gray-500 text-sm">Chargement des événements...</p>
            </div>
          ) : (
            <>
              <EventTable
                events={events}
                onSort={handleSort}
                sortBy={filters.sort_by}
                sortOrder={filters.sort_order}
              />

              <div className="mt-4">
                <Pagination
                  page={page}
                  totalPages={totalPages}
                  total={total}
                  pageSize={PAGE_SIZE}
                  onPageChange={setPage}
                />
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
