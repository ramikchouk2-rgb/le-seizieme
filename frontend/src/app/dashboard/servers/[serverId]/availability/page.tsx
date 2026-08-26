'use client';

import { useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import Header from '@/app/components/dashboard/Header';
import AvailabilityHeader from '@/app/components/availability/AvailabilityHeader';
import AvailabilitySummary from '@/app/components/availability/AvailabilitySummary';
import AvailabilityCalendar from '@/app/components/availability/AvailabilityCalendar';
import AvailabilityList from '@/app/components/availability/AvailabilityList';
import AvailabilityForm from '@/app/components/availability/AvailabilityForm';
import DeleteAvailabilityDialog from '@/app/components/availability/DeleteAvailabilityDialog';
import { useServerAvailability, useCreateServerAvailability, useUpdateServerAvailability, useDeleteServerAvailability } from '@/app/lib/hooks';
import { Spinner } from '@/app/lib/loading';
import { useAnnouncer } from '@/app/components/ui/Announcer';

type LoadingState = 'loading' | 'error' | 'success';

const STATUS_STYLES: Record<string, string> = {
  AVAILABLE: 'bg-green-50 text-green-700 border-green-200',
  UNAVAILABLE: 'bg-red-50 text-red-700 border-red-200',
  RESERVED: 'bg-yellow-50 text-yellow-700 border-yellow-200',
};

export default function ServerAvailabilityPage() {
  const params = useParams();
  const serverId = params.serverId as string;
  const { announceSuccess, announceError } = useAnnouncer();

  const [showForm, setShowForm] = useState(false);
  const [editingItem, setEditingItem] = useState<{ id: string; start_datetime: string; end_datetime: string; status: string; note?: string | null } | null>(null);
  const [deletingItem, setDeletingItem] = useState<{ id: string; start_datetime: string; end_datetime: string; status: string } | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: availabilityData, isLoading, error, refetch } = useServerAvailability(serverId);
  const createMutation = useCreateServerAvailability();
  const updateMutation = useUpdateServerAvailability();
  const deleteMutation = useDeleteServerAvailability();

  const items = availabilityData?.items ?? [];

  const handleCreate = async (data: { start_datetime: string; end_datetime: string; status?: string; note?: string }) => {
    try {
      await createMutation.mutateAsync({ serverId, payload: data });
      setShowForm(false);
      announceSuccess('Disponibilité créée avec succès.');
    } catch {
      announceError('Opération impossible. Veuillez réessayer.');
    }
  };

  const handleUpdate = async (data: { start_datetime?: string; end_datetime?: string; status?: string; note?: string }) => {
    if (!editingItem) return;
    try {
      await updateMutation.mutateAsync({ serverId, availabilityId: editingItem.id, payload: data });
      setEditingItem(null);
      announceSuccess('Disponibilité mise à jour avec succès.');
    } catch {
      announceError('Opération impossible. Veuillez réessayer.');
    }
  };

  const handleDelete = async () => {
    if (!deletingItem) return;
    try {
      await deleteMutation.mutateAsync({ serverId, availabilityId: deletingItem.id });
      setDeletingItem(null);
      announceSuccess('Disponibilité supprimée avec succès.');
    } catch {
      announceError('Opération impossible. Veuillez réessayer.');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Header title="Disponibilités" />
      <main className="p-8">
        <div className="max-w-7xl mx-auto">
          <AvailabilityHeader serverId={serverId} />

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 text-sm text-red-700 flex items-center justify-between">
              <span>{error?.message || 'Impossible de charger les disponibilités.'}</span>
              <button onClick={() => refetch()} className="underline font-medium">
                Réessayer
              </button>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              {isLoading ? (
                <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm">
                  <Spinner size="lg" className="mx-auto mb-4 text-[#D4AF37]" />
                  <p className="text-gray-500 text-sm">Chargement des disponibilités...</p>
                </div>
              ) : (
                <AvailabilityList
                  items={items}
                  onEdit={setEditingItem}
                  onDelete={setDeletingItem}
                  statusStyles={STATUS_STYLES}
                />
              )}
            </div>

            <div className="space-y-6">
              <AvailabilitySummary items={items} />
              <AvailabilityCalendar items={items} />
              <button
                onClick={() => setShowForm(true)}
                className="w-full inline-flex items-center justify-center px-4 py-2 bg-[#D4AF37] text-white text-sm font-medium rounded-lg hover:bg-[#B8941E] transition-colors"
              >
                + Nouvelle disponibilité
              </button>
            </div>
          </div>

          {showForm && (
            <AvailabilityForm
              serverId={serverId}
              item={null}
              onSave={handleCreate}
              onClose={() => setShowForm(false)}
              loading={createMutation.isPending}
            />
          )}

          {editingItem && (
            <AvailabilityForm
              serverId={serverId}
              item={editingItem}
              onSave={handleUpdate}
              onClose={() => setEditingItem(null)}
              loading={updateMutation.isPending}
            />
          )}

          {deletingItem && (
            <DeleteAvailabilityDialog
              item={deletingItem}
              onConfirm={handleDelete}
              onClose={() => setDeletingItem(null)}
              loading={deleteMutation.isPending}
            />
          )}
        </div>
      </main>
    </div>
  );
}
