'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Header from '@/app/components/dashboard/Header';
import { useUser, useDeactivateUser } from '@/app/lib/hooks';
import { useAnnouncer } from '@/app/components/ui/Announcer';
import { Spinner, PageLoading } from '@/app/lib/loading';
import DeactivateUserDialog from '@/app/components/users/DeactivateUserDialog';
import { USER_ROLES } from '@/app/lib/types';
import { useAdminGuard } from '@/app/lib/auth';

const SECTION = 'text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2';

function StatusBadge({ active }: { active: boolean }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
        active
          ? 'bg-green-50 text-green-700 border-green-200'
          : 'bg-red-50 text-red-700 border-red-200'
      }`}
    >
      {active ? 'Actif' : 'Inactif'}
    </span>
  );
}

function formatDate(value?: string | null) {
  if (!value) return '—';
  const date = new Date(value.endsWith('Z') ? value : `${value}Z`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('fr-FR');
}

export default function UserDetailPage() {
  const params = useParams();
  const router = useRouter();
  const userId = params.userId as string;
  const { isAllowed } = useAdminGuard();
  const { announceSuccess, announceError } = useAnnouncer();
  const [dialogOpen, setDialogOpen] = useState(false);
  const deactivateUser = useDeactivateUser();

  const { data: user, isLoading, error, refetch } = useUser(userId);

  const handleDeactivate = async () => {
    try {
      await deactivateUser.mutateAsync(userId);
      announceSuccess('Utilisateur désactivé.');
      setDialogOpen(false);
      router.push('/dashboard/users');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Impossible de désactiver l\'utilisateur.';
      announceError(message);
    }
  };

  if (!isAllowed) {
    return <PageLoading message="Accès restreint aux administrateurs..." />;
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Spinner size="lg" className="mx-auto mb-4 text-[#D4AF37]" />
          <p className="text-gray-500 text-sm">Chargement de l'utilisateur...</p>
        </div>
      </div>
    );
  }

  if (error || !user) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header title="Utilisateur" />
        <main className="p-8">
          <div className="max-w-7xl mx-auto">
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm">
              <p className="text-gray-500 text-sm mb-4">
                {error?.message || 'Utilisateur introuvable'}
              </p>
              <button
                onClick={() => refetch()}
                className="inline-flex items-center px-4 py-2 bg-[#D4AF37] text-white text-sm font-medium rounded-lg hover:bg-[#B8941E] transition-colors"
              >
                Réessayer
              </button>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <Header
        title={user.email}
        action={
          <div className="flex items-center gap-2">
            <button
              onClick={() => setDialogOpen(true)}
              disabled={deactivateUser.isPending}
              className="px-4 py-2 bg-red-50 text-red-600 text-sm font-medium rounded-lg border border-red-200 hover:bg-red-100 transition-colors"
            >
              Désactiver
            </button>
            <a
              href={`/dashboard/users/${user.id}/edit`}
              className="inline-flex items-center px-4 py-2 bg-[#D4AF37] text-white text-sm font-medium rounded-lg hover:bg-[#B8941E] transition-colors"
            >
              Modifier
            </a>
          </div>
        }
      />

      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm space-y-6">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-[#D4AF37]/10 flex items-center justify-center text-[#D4AF37] text-xl font-bold">
            {user.email?.[0]?.toUpperCase() || 'U'}
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{user.email}</h3>
            <p className="text-sm text-gray-500">
              {USER_ROLES[user.role as keyof typeof USER_ROLES] || user.role}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-gray-50 rounded-lg p-4">
            <p className={SECTION}>Rôle</p>
            <p className="text-sm font-medium text-gray-900">
              {USER_ROLES[user.role as keyof typeof USER_ROLES] || user.role}
            </p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className={SECTION}>Statut</p>
            <StatusBadge active={user.is_active} />
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className={SECTION}>Créé le</p>
            <p className="text-sm text-gray-900">{formatDate(user.created_at)}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className={SECTION}>Mis à jour</p>
            <p className="text-sm text-gray-900">{formatDate(user.updated_at)}</p>
          </div>
        </div>
      </div>

      <DeactivateUserDialog
        user={user}
        open={dialogOpen}
        loading={deactivateUser.isPending}
        onClose={() => setDialogOpen(false)}
        onConfirm={handleDeactivate}
      />
    </div>
  );
}
