'use client';

import { useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import Header from '@/app/components/dashboard/Header';
import { useEventEvaluations, useCreateEvaluation, useUpdateEvaluation, useDeleteEvaluation, useEventDetail } from '@/app/lib/hooks';
import { Spinner } from '@/app/lib/loading';
import EvaluationForm from '@/app/components/evaluations/EvaluationForm';
import { EvaluationResponse } from '@/app/lib/api';
import { useAnnouncer } from '@/app/components/ui/Announcer';

export default function EventEvaluationsPage() {
  const params = useParams();
  const eventId = params.eventId as string;
  const { announceSuccess, announceError } = useAnnouncer();

  const [showForm, setShowForm] = useState(false);
  const [editingEvaluation, setEditingEvaluation] = useState<EvaluationResponse | null>(null);

  const { data: evaluations, isLoading, error, refetch } = useEventEvaluations(eventId);
  const { data: eventDetail, isLoading: eventDetailLoading } = useEventDetail(eventId);
  const createMutation = useCreateEvaluation();
  const updateMutation = useUpdateEvaluation();
  const deleteMutation = useDeleteEvaluation();

  const servers = eventDetail?.assignments
    .filter((a) => a.status === 'CONFIRMED')
    .map((a) => ({
      server_id: a.server_id,
      server_name: a.server_name,
      role: a.role,
    })) || [];

  const handleCreate = async (payload: { server_id: string; punctuality: number; work_quality: number; presentation: number; teamwork: number; client_relation: number; comment?: string | null }) => {
    try {
      await createMutation.mutateAsync({ eventId, payload });
      setShowForm(false);
      announceSuccess('Évaluation enregistrée avec succès.');
    } catch {
      announceError('Opération impossible. Veuillez réessayer.');
    }
  };

  const handleUpdate = async (evaluationId: string, payload: { punctuality?: number; work_quality?: number; presentation?: number; teamwork?: number; client_relation?: number; comment?: string | null }) => {
    try {
      await updateMutation.mutateAsync({ eventId, evaluationId, payload });
      setEditingEvaluation(null);
      announceSuccess('Évaluation mise à jour avec succès.');
    } catch {
      announceError('Opération impossible. Veuillez réessayer.');
    }
  };

  const handleDelete = async (evaluationId: string) => {
    try {
      await deleteMutation.mutateAsync({ eventId, evaluationId });
      announceSuccess('Évaluation supprimée avec succès.');
    } catch {
      announceError('Opération impossible. Veuillez réessayer.');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Header title="Évaluations" />
      <main className="p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between mb-6">
            <p className="text-gray-600">
              Évaluez les performances de l'équipe après l'événement.
            </p>
            <button
              onClick={() => setShowForm(true)}
              disabled={eventDetailLoading}
              className="inline-flex items-center px-4 py-2 bg-[#D4AF37] text-white text-sm font-medium rounded-lg hover:bg-[#B8941E] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {eventDetailLoading ? 'Chargement...' : '+ Nouvelle évaluation'}
            </button>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 text-sm text-red-700 flex items-center justify-between">
              <span>{error?.message || 'Impossible de charger les évaluations.'}</span>
              <button onClick={() => refetch()} className="underline font-medium">
                Réessayer
              </button>
            </div>
          )}

          {isLoading ? (
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm">
              <Spinner size="lg" className="mx-auto mb-4 text-[#D4AF37]" />
              <p className="text-gray-500 text-sm">Chargement des évaluations...</p>
            </div>
          ) : evaluations && evaluations.length > 0 ? (
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Serveur</th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Rôle</th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Score</th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Commentaire</th>
                    <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {evaluations.map((evaluation) => (
                    <tr key={evaluation.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{evaluation.server_name}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{evaluation.role}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-[#D4AF37]/10 text-[#D4AF37] border border-[#D4AF37]/20">
                          {((evaluation.punctuality + evaluation.work_quality + evaluation.presentation + evaluation.teamwork + evaluation.client_relation) / 5).toFixed(1)}/10
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500 max-w-xs truncate">{evaluation.comment || '—'}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button
                          onClick={() => setEditingEvaluation(evaluation)}
                          className="text-[#D4AF37] hover:text-[#B8941E] mr-3"
                        >
                          Modifier
                        </button>
                        <button
                          onClick={() => handleDelete(evaluation.id)}
                          disabled={deleteMutation.isPending}
                          className="text-red-600 hover:text-red-700 disabled:opacity-50"
                        >
                          Supprimer
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm">
              <p className="text-gray-500 text-sm">Aucune évaluation enregistrée.</p>
              <button
                onClick={() => setShowForm(true)}
                className="mt-4 inline-flex items-center px-4 py-2 bg-[#D4AF37] text-white text-sm font-medium rounded-lg hover:bg-[#B8941E] transition-colors"
              >
                Créer la première évaluation
              </button>
            </div>
          )}
        </div>
      </main>

      {showForm && (
        <EvaluationForm
          onClose={() => setShowForm(false)}
          onSave={handleCreate}
          servers={servers}
          saving={createMutation.isPending}
        />
      )}

      {editingEvaluation && (
        <EvaluationForm
          onClose={() => setEditingEvaluation(null)}
          onSave={(payload) => handleUpdate(editingEvaluation.id, payload)}
          servers={servers}
          initial={editingEvaluation}
          saving={updateMutation.isPending}
        />
      )}
    </div>
  );
}
