'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Header from '@/app/components/dashboard/Header';
import ServerForm from '@/app/components/servers/ServerForm';
import { useServer } from '@/app/lib/hooks';
import { useAnnouncer } from '@/app/components/ui/Announcer';
import { Spinner } from '@/app/lib/loading';

export default function EditServerPage() {
  const params = useParams();
  const serverId = params.serverId as string;
  const router = useRouter();
  const { announceSuccess, announceError } = useAnnouncer();
  const [success, setSuccess] = useState<string | null>(null);

  const { data, isLoading, error, refetch } = useServer(serverId);

  const [initialData, setInitialData] = useState<null | {
    first_name: string;
    last_name: string;
    email: string;
    phone: string;
    gender: string;
    city_id: string;
    years_experience: number;
    worker_type?: string;
    speed_score?: number;
    punctuality_score?: number;
    presentation_score?: number;
    communication_score?: number;
    teamwork_score?: number;
    discipline_score?: number;
    endurance_score?: number;
    is_active?: boolean;
    id: string;
  }>(null);

  useEffect(() => {
    if (data) {
      setInitialData({
        first_name: data.first_name,
        last_name: data.last_name,
        email: data.email,
        phone: data.phone,
        gender: data.gender,
        city_id: data.city_id,
        years_experience: data.years_experience,
        worker_type: data.worker_type,
        speed_score: data.speed_score,
        punctuality_score: data.punctuality_score,
        presentation_score: data.presentation_score,
        communication_score: data.communication_score,
        teamwork_score: data.teamwork_score,
        discipline_score: data.discipline_score,
        endurance_score: data.endurance_score,
        is_active: data.is_active,
        id: data.id,
      });
    }
  }, [data]);

  const handleSuccess = (id: string) => {
    setSuccess('Serveur modifié avec succès.');
    announceSuccess('Serveur modifié avec succès.');
    setTimeout(() => {
      router.push(`/dashboard/servers/${id}`);
    }, 1000);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Spinner size="lg" className="mx-auto mb-4 text-[#D4AF37]" />
          <p className="text-gray-500 text-sm">Chargement du serveur...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header title="Modifier le serveur" />
        <main className="p-8">
          <div className="max-w-7xl mx-auto">
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm">
              <p className="text-gray-500 text-sm mb-4">{error?.message || 'Serveur introuvable'}</p>
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
      <Header title="Modifier le serveur" />

      {success && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-sm text-green-700">
          {success}
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <ServerForm
          mode="edit"
          initialData={initialData}
          onSuccess={handleSuccess}
          onCancel={() => router.back()}
        />
      </div>
    </div>
  );
}