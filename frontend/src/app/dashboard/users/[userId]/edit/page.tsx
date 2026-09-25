'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Header from '@/app/components/dashboard/Header';
import UserForm from '@/app/components/users/UserForm';
import { useUser } from '@/app/lib/hooks';
import { useAnnouncer } from '@/app/components/ui/Announcer';
import { Spinner, PageLoading } from '@/app/lib/loading';
import { UserListItem } from '@/app/lib/types';
import { useAdminGuard } from '@/app/lib/auth';

export default function EditUserPage() {
  const params = useParams();
  const router = useRouter();
  const userId = params.userId as string;
  const { isAllowed } = useAdminGuard();
  const { announceSuccess, announceError } = useAnnouncer();
  const [success, setSuccess] = useState<string | null>(null);

  const { data: user, isLoading, error } = useUser(userId);

  const handleSuccess = () => {
    setSuccess('Modifications enregistrées avec succès.');
    announceSuccess('Utilisateur modifié avec succès.');
    setTimeout(() => router.push('/dashboard/users'), 1000);
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
        <Header title="Modifier l'utilisateur" />
        <main className="p-8">
          <div className="max-w-7xl mx-auto">
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm">
              <p className="text-gray-500 text-sm mb-4">
                {error?.message || 'Utilisateur introuvable'}
              </p>
              <button
                onClick={() => router.push('/dashboard/users')}
                className="inline-flex items-center px-4 py-2 bg-[#D4AF37] text-white text-sm font-medium rounded-lg hover:bg-[#B8941E] transition-colors"
              >
                Retour à la liste
              </button>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <Header title={`Modifier ${user.email}`} />

      {success && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-sm text-green-700" aria-live="polite">
          {success}
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <UserForm
          mode="edit"
          initialData={{
            id: user.id,
            email: user.email,
            role: user.role,
            is_active: user.is_active,
          } as UserListItem}
          onSuccess={handleSuccess}
          onCancel={() => router.push('/dashboard/users')}
        />
      </div>
    </div>
  );
}
