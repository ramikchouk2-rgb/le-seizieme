'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import Header from '@/app/components/dashboard/Header';
import AuditLogTable from '@/app/components/users/AuditLogTable';
import AuditLogFiltersPanel from '@/app/components/users/AuditLogFiltersPanel';
import AuditLogDrawer from '@/app/components/users/AuditLogDrawer';
import Pagination from '@/app/components/servers/Pagination';
import { useAuditLogs } from '@/app/lib/hooks';
import { useAnnouncer } from '@/app/components/ui/Announcer';
import { Spinner, PageLoading } from '@/app/lib/loading';
import { DEFAULT_AUDIT_LOG_FILTERS } from '@/app/data/audit-log';
import { AuditLogItem, AuditLogFilters } from '@/app/lib/types';
import { useAdminGuard } from '@/app/lib/auth';

const PAGE_SIZE = 20;

export default function AuditLogPage() {
  const { isAllowed } = useAdminGuard();
  const [filters, setFilters] = useState<AuditLogFilters>(DEFAULT_AUDIT_LOG_FILTERS);
  const [page, setPage] = useState(1);
  const [drawerItem, setDrawerItem] = useState<AuditLogItem | null>(null);
  const { announceError } = useAnnouncer();

  const queryParams = useMemo(
    () => ({
      action: filters.action || undefined,
      actor_user_id: filters.actor_user_id || undefined,
      target_user_id: filters.target_user_id || undefined,
      created_after: filters.created_after || undefined,
      created_before: filters.created_before || undefined,
      page,
      page_size: PAGE_SIZE,
    }),
    [filters, page],
  );

  const {
    data: auditLogData,
    isLoading: auditLogLoading,
    error: auditLogError,
    refetch: refetchAuditLog,
  } = useAuditLogs(queryParams);

  const items = auditLogData?.items ?? [];
  const total = auditLogData?.total ?? 0;
  const totalPages = auditLogData?.total_pages ?? 1;
  const error = auditLogError?.message ?? null;

  useEffect(() => {
    if (!isAllowed) {
      announceError('Accès refusé. Cette page est réservée aux administrateurs.');
    }
  }, [isAllowed, announceError]);

  const handleReset = useCallback(() => {
    setFilters(DEFAULT_AUDIT_LOG_FILTERS);
    setPage(1);
  }, []);

  const handleFilterChange = useCallback((next: AuditLogFilters) => {
    setFilters(next);
    setPage(1);
  }, []);

  if (!isAllowed) {
    return <PageLoading message="Accès restreint aux administrateurs..." />;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header title="Journal d'audit" />
      <main className="p-8">
        <div className="max-w-7xl mx-auto">
          <p className="text-gray-600 mb-6">
            Consultez l'historique des actions administratives : gestion des
            utilisateurs, photos de profil et attestations professionnelles.
          </p>

          <AuditLogFiltersPanel
            filters={filters}
            onChange={handleFilterChange}
            onReset={handleReset}
          />

          <div className="bg-white rounded-xl border border-gray-200 px-5 py-3 shadow-sm mb-6 flex items-center gap-3">
            <span className="text-sm font-medium text-gray-500">Total</span>
            {auditLogLoading ? (
              <Spinner size="sm" className="text-[#D4AF37]" />
            ) : (
              <span className="text-sm font-semibold text-gray-900">
                {total} {total > 1 ? 'entrées' : 'entrée'} au total
              </span>
            )}
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 text-sm text-red-700 flex items-center justify-between">
              <span>{error}</span>
              <button onClick={() => refetchAuditLog()} className="underline font-medium">
                Réessayer
              </button>
            </div>
          )}

          {auditLogLoading ? (
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm">
              <Spinner size="lg" className="mx-auto mb-4 text-[#D4AF37]" />
              <p className="text-gray-500 text-sm">Chargement du journal d'audit...</p>
            </div>
          ) : (
            <>
              <AuditLogTable items={items} onDrawerOpen={setDrawerItem} />

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

          <AuditLogDrawer
            item={drawerItem}
            open={!!drawerItem}
            onClose={() => setDrawerItem(null)}
          />
        </div>
      </main>
    </div>
  );
}