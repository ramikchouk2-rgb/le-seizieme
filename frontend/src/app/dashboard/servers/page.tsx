'use client';

import { useState, useCallback } from 'react';
import Header from '@/app/components/dashboard/Header';
import FilterPanel from '@/app/components/servers/FilterPanel';
import ServerTable from '@/app/components/servers/ServerTable';
import Pagination from '@/app/components/servers/Pagination';
import ServerDrawer from '@/app/components/servers/ServerDrawer';
import { DEFAULT_FILTERS } from '@/app/data/servers';
import { useServers, useServerStats, useServer } from '@/app/lib/hooks';
import { ServerFilters, ServerListItem, ServerProfile } from '@/app/lib/types';
import { Spinner } from '@/app/lib/loading';

const PAGE_SIZE = 10;

export default function ServersPage() {
  const [filters, setFilters] = useState<ServerFilters>(DEFAULT_FILTERS);
  const [page, setPage] = useState(1);
  const [selectedServer, setSelectedServer] = useState<ServerListItem | null>(null);

  const { data: stats, isLoading: statsLoading } = useServerStats();
  const { data: serversData, isLoading: serversLoading, error: serversError, refetch: refetchServers } = useServers(filters, page, PAGE_SIZE);
  const { data: profile, isLoading: profileLoading } = useServer(selectedServer?.id || '');

  const servers = serversData?.servers ?? [];
  const total = serversData?.total ?? 0;
  const totalPages = serversData?.total_pages ?? 1;
  const error = serversError?.message ?? null;

  const handleSort = useCallback((field: string) => {
    setFilters((prev) => ({
      ...prev,
      sort_by: field,
      sort_order: prev.sort_by === field && prev.sort_order === 'asc' ? 'desc' : 'asc',
    }));
    setPage(1);
  }, []);

  const handleSelect = useCallback((server: ServerListItem) => {
    setSelectedServer(server);
  }, []);

  const handleReset = useCallback(() => {
    setFilters(DEFAULT_FILTERS);
    setPage(1);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <Header title="Serveurs" />
      <main className="p-8">
        <div className="max-w-7xl mx-auto">
          <p className="text-gray-600 mb-6">
            Gérez votre équipe, leurs compétences, disponibilités et moyens de transport.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
              <p className="text-sm font-medium text-gray-500 mb-1">Total serveurs</p>
              <div className="text-2xl font-bold text-gray-900">
                {statsLoading ? <Spinner size="sm" /> : (stats?.total ?? 0)}
              </div>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
              <p className="text-sm font-medium text-gray-500 mb-1">Disponibles</p>
              <div className="text-2xl font-bold text-green-600">
                {statsLoading ? <Spinner size="sm" /> : (stats?.available ?? 0)}
              </div>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
              <p className="text-sm font-medium text-gray-500 mb-1">Indisponibles</p>
              <div className="text-2xl font-bold text-red-600">
                {statsLoading ? <Spinner size="sm" /> : (stats?.unavailable ?? 0)}
              </div>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
              <p className="text-sm font-medium text-gray-500 mb-1">Avec véhicule</p>
              <div className="text-2xl font-bold text-[#D4AF37]">
                {statsLoading ? <Spinner size="sm" /> : (stats?.with_vehicle ?? 0)}
              </div>
            </div>
          </div>

          <FilterPanel filters={filters} onChange={setFilters} onReset={handleReset} />

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 text-sm text-red-700 flex items-center justify-between">
              <span>{error}</span>
              <button onClick={() => refetchServers()} className="underline font-medium">
                Réessayer
              </button>
            </div>
          )}

          {serversLoading ? (
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm">
              <Spinner size="lg" className="mx-auto mb-4 text-[#D4AF37]" />
              <p className="text-gray-500 text-sm">Chargement des serveurs...</p>
            </div>
          ) : (
            <>
              <ServerTable
                servers={servers}
                onSelect={handleSelect}
                sortBy={filters.sort_by}
                sortOrder={filters.sort_order}
                onSort={handleSort}
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

      <ServerDrawer
        server={selectedServer}
        profile={profile ?? null}
        loading={profileLoading}
        onClose={() => { setSelectedServer(null); }}
      />
    </div>
  );
}
