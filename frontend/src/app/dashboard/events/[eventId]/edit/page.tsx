'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Header from '@/app/components/dashboard/Header';
import EventForm from '@/app/components/events/EventForm';
import { useEventDetail } from '@/app/lib/hooks';
import { useAnnouncer } from '@/app/components/ui/Announcer';
import { Spinner } from '@/app/lib/loading';
import { RequirementCreateRequest } from '@/app/lib/api';

export default function EditEventPage() {
  const params = useParams();
  const eventId = params.eventId as string;
  const router = useRouter();
  const { announceSuccess, announceError } = useAnnouncer();
  const [success, setSuccess] = useState<string | null>(null);
  const [initialData, setInitialData] = useState<null | {
    name: string;
    client_name: string;
    city_id: string;
    address: string;
    start_datetime: string;
    end_datetime: string;
    guest_count: number;
    event_type: string;
    alcohol_service: boolean;
    food_products_count: number;
    priority: string;
    is_urgent: boolean;
    required_response_minutes: number | undefined;
    status: string;
    notes: string;
    id: string;
  }>(null);
  const [initialRequirements, setInitialRequirements] = useState<RequirementCreateRequest[]>([]);

  const { data, isLoading, error, refetch } = useEventDetail(eventId);

  useEffect(() => {
    if (data?.event) {
      const event = data.event;
      const requirements_detail = data.requirements_detail || [];
      setInitialData({
        name: event.name,
        client_name: event.client_name,
        city_id: event.city_id,
        address: event.address,
        start_datetime: event.start_datetime,
        end_datetime: event.end_datetime,
        guest_count: event.guest_count,
        event_type: event.event_type,
        alcohol_service: event.alcohol_service,
        food_products_count: event.food_products_count,
        priority: event.priority,
        is_urgent: event.urgent,
        required_response_minutes: event.required_response_minutes ?? undefined,
        status: event.status,
        notes: event.notes ?? '',
        id: event.id,
      });
      setInitialRequirements(requirements_detail.map(r => ({
        role_name: r.role_name,
        quantity: r.quantity,
        required_gender: r.required_gender,
        minimum_experience: r.minimum_experience,
        minimum_skill_level: r.minimum_skill_level,
      })));
    }
  }, [data]);

  const handleSuccess = (id: string) => {
    setSuccess('Événement modifié avec succès.');
    announceSuccess('Événement modifié avec succès.');
    setTimeout(() => {
      router.push(`/dashboard/events/${id}`);
    }, 1000);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Spinner size="lg" className="mx-auto mb-4 text-[#D4AF37]" />
          <p className="text-gray-500 text-sm">Chargement de l'événement...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header title="Modifier l'événement" />
        <main className="p-8">
          <div className="max-w-7xl mx-auto">
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm">
              <p className="text-gray-500 text-sm mb-4">{error?.message || 'Événement introuvable'}</p>
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
      <Header title="Modifier l'événement" />

      {success && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-sm text-green-700">
          {success}
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <EventForm
          mode="edit"
          initialData={initialData}
          initialRequirements={initialRequirements}
          onSuccess={handleSuccess}
          onCancel={() => router.back()}
        />
      </div>
    </div>
  );
}