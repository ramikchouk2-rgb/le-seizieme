'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import Link from 'next/link';
import Header from '@/app/components/dashboard/Header';
import UserTable from '@/app/components/users/UserTable';
import UserStats from '@/app/components/users/UserStats';
import UserFiltersPanel from '@/app/components/users/UserFiltersPanel';
import UserDrawer from '@/app/components/users/UserDrawer';
import Pagination from '@/app/components/servers/Pagination';
import { useUsers, useUsersStats } from '@/app/lib/hooks';
import { useAnnouncer } from '@/app/components/ui/Announcer';
import { Spinner, PageLoading } from '@/app/lib/loading';
import { DEFAULT_USER_FILTERS } from '@/app/data/users';
import { UserListItem, UserFilters } from '@/app/lib/types';
import { useAdminGuard } from '@/app/lib/auth';

const PAGE_SIZE = 10;

export default function UsersPage() {
  const { isAllowed } = useAdminGuard();
  const [filters, setFilters] = useState<UserFilters>(DEFAULT_USER_FILTERS);
  const [page, setPage] = useState(1);
  const [drawerUser, setDrawerUser] = useState<UserListItem | null>(null);
  const { announceError } = useAnnouncer();

  const {
    data: stats,
    isLoading: statsLoading,
  } = useUsersStats();

  const queryParams = useMemo(
    () => ({
      search: filters.search || undefined,
      role: filters.role || undefined,
      is_active: filters.is_active ? filters.is_active === 'true' : undefined,
      page,
      page_size: PAGE_SIZE,
    }),
    [filters, page],
  );

  const {
    data: usersData,
    isLoading: usersLoading,
    error: usersError,
    refetch: refetchUsers,
  } = useUsers(queryParams);

  const users = usersData?.items ?? [];
  const total = usersData?.total ?? 0;
  const totalPages = usersData?.total_pages ?? 1;
  const error = usersError?.message ?? null;

  useEffect(() => {
    if (!isAllowed) {
      announceError('Accès refusé. Cette page est réservée aux administrateurs.');
    }
  }, [isAllowed, announceError]);

  const handleReset = useCallback(() => {
    setFilters(DEFAULT_USER_FILTERS);
    setPage(1);
  }, []);

  const handleFilterChange = useCallback((next: UserFilters) => {
    setFilters(next);
    setPage(1);
  }, []);

  if (!isAllowed) {
    return (
      <PageLoading message="Accès restreint aux administrateurs..." />
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header
        title="Utilisateurs"
        action={
          <Link
            href="/dashboard/users/new"
            className="inline-flex items-center px-4 py-2 bg-[#D4AF37] text-white text-sm font-medium rounded-lg hover:bg-[#B8941E] transition-colors"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
            </svg>
            Ajouter un utilisateur
          </Link>
        }
      />
      <main className="p-8">
        <div className="max-w-7xl mx-auto">
          <p className="text-gray-600 mb-6">
            Gérez les comptes utilisateurs, leurs rôles et leur statut.
          </p>

          <UserStats data={stats} loading={statsLoading} />

          <UserFiltersPanel
            filters={filters}
            onChange={handleFilterChange}
            onReset={handleReset}
          />

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 text-sm text-red-700 flex items-center justify-between">
              <span>{error}</span>
              <button onClick={() => refetchUsers()} className="underline font-medium">
                Réessayer
              </button>
            </div>
          )}

          {usersLoading ? (
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm">
              <Spinner size="lg" className="mx-auto mb-4 text-[#D4AF37]" />
              <p className="text-gray-500 text-sm">Chargement des utilisateurs...</p>
            </div>
          ) : (
            <>
              <UserTable users={users} onDrawerOpen={setDrawerUser} />

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

          <UserDrawer
            user={drawerUser}
            open={!!drawerUser}
            onClose={() => setDrawerUser(null)}
          />
        </div>
      </main>
    </div>
  );
}
