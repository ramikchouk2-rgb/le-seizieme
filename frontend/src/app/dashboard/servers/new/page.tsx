'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Header from '@/app/components/dashboard/Header';
import ServerForm from '@/app/components/servers/ServerForm';
import { useAnnouncer } from '@/app/components/ui/Announcer';

export default function NewServerPage() {
  const router = useRouter();
  const [success, setSuccess] = useState<string | null>(null);
  const { announceSuccess } = useAnnouncer();

  const handleSuccess = (serverId: string) => {
    setSuccess('Serveur créé avec succès.');
    announceSuccess('Serveur créé avec succès.');
    setTimeout(() => {
      router.push(`/dashboard/servers/${serverId}`);
    }, 1000);
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <Header title="Nouveau serveur" />

      {success && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-sm text-green-700">
          {success}
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <ServerForm mode="create" onSuccess={handleSuccess} onCancel={() => router.back()} />
      </div>
    </div>
  );
}