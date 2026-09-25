'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Header from '@/app/components/dashboard/Header';
import UserForm from '@/app/components/users/UserForm';
import { useAnnouncer } from '@/app/components/ui/Announcer';

export default function NewUserPage() {
  const router = useRouter();
  const [success, setSuccess] = useState<string | null>(null);
  const { announceSuccess } = useAnnouncer();

  const handleSuccess = (userId: string) => {
    setSuccess('Utilisateur créé avec succès.');
    announceSuccess('Utilisateur créé avec succès.');
    setTimeout(() => {
      router.push(`/dashboard/users/${userId}`);
    }, 1000);
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <Header title="Nouvel utilisateur" />

      {success && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-sm text-green-700" aria-live="polite">
          {success}
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <UserForm
          mode="create"
          onSuccess={handleSuccess}
          onCancel={() => router.back()}
        />
      </div>
    </div>
  );
}
