'use client';

import { useState } from 'react';
import Link from 'next/link';
import { StaffRecommendationResponse, confirmStaffAssignments, ConfirmStaffAssignmentRequest, ConfirmStaffResponse } from '@/app/lib/api';
import ConfirmStaffDialog from './ConfirmStaffDialog';
import { useAnnouncer } from '@/app/components/ui/Announcer';

interface StaffRecommendationPanelProps {
  recommendations: StaffRecommendationResponse | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  eventId: string;
  onConfirmed?: () => void;
}

const STATUS_LABELS: Record<string, string> = {
  FILLED: 'Complet',
  INSUFFICIENT_STAFF: 'Personnel insuffisant',
};

const STATUS_STYLES: Record<string, string> = {
  FILLED: 'bg-green-50 text-green-700 border-green-200',
  INSUFFICIENT_STAFF: 'bg-amber-50 text-amber-700 border-amber-200',
};

export default function StaffRecommendationPanel({
  recommendations,
  loading,
  error,
  onRetry,
  eventId,
  onConfirmed,
}: StaffRecommendationPanelProps) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [confirmResult, setConfirmResult] = useState<ConfirmStaffResponse | null>(null);
  const { announceSuccess, announceError } = useAnnouncer();

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Recommandations de staffing</h3>
        <p className="text-gray-500 text-sm">Génération des recommandations...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-xl border border-red-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Recommandations de staffing</h3>
        <p className="text-sm text-red-600 mb-3">{error}</p>
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-[#D4AF37] text-white text-sm font-medium rounded-lg hover:bg-[#B8941E] transition-colors"
        >
          Réessayer
        </button>
      </div>
    );
  }

  if (!recommendations) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Recommandations de staffing</h3>
        <p className="text-gray-500 text-sm">Aucune recommandation générée.</p>
      </div>
    );
  }

  const totalRequested = recommendations.requirements.reduce(
    (sum, req) => sum + req.requirement.quantity,
    0
  );
  const totalSelected = recommendations.total_selected;
  const totalMissing = totalRequested - totalSelected;

  const selectedAssignments: ConfirmStaffAssignmentRequest[] = [];
  for (const req of recommendations.requirements) {
    for (const candidate of req.selected) {
      selectedAssignments.push({
        server_id: candidate.server_id,
        role: req.requirement.role_name,
      });
    }
  }

  const handleConfirmClick = () => {
    setConfirmOpen(true);
    setConfirmError(null);
    setConfirmResult(null);
  };

  const handleConfirm = async () => {
    setConfirmLoading(true);
    setConfirmError(null);
    try {
      const result = await confirmStaffAssignments(eventId, selectedAssignments);
      setConfirmResult(result);
      onConfirmed?.();
      announceSuccess('Personnel confirmé avec succès.');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Impossible de confirmer l\'équipe.';
      setConfirmError(message);
      announceError('Opération impossible. Veuillez réessayer.');
    } finally {
      setConfirmLoading(false);
    }
  };

  const handleDialogClose = () => {
    if (confirmResult) {
      setConfirmOpen(false);
    } else {
      setConfirmOpen(false);
      setConfirmError(null);
    }
  };

  const dialogAssignments = confirmResult
    ? confirmResult.assignments
    : selectedAssignments.map((a) => ({ server_id: a.server_id, server_name: '', role: a.role }));

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Recommandations de staffing</h3>
        <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
          {recommendations.status}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-gray-900">{totalRequested}</p>
          <p className="text-xs text-gray-500">Postes requis</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-green-600">{totalSelected}</p>
          <p className="text-xs text-gray-500">Recommandés</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-amber-600">{totalMissing}</p>
          <p className="text-xs text-gray-500">Manquants</p>
        </div>
      </div>

      <div className="space-y-4">
        {recommendations.requirements.map((req) => {
          const requirement = req.requirement;
          const selectedCount = req.selected.length;
          const missingCount = requirement.quantity - selectedCount;

          return (
            <div key={requirement.requirement_id} className="border border-gray-100 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h4 className="text-sm font-semibold text-gray-900">
                    {requirement.role_name}
                    {requirement.required_gender && (
                      <span className="ml-2 text-xs text-gray-500">
                        ({requirement.required_gender === 'MALE' ? 'Homme' : 'Femme'})
                      </span>
                    )}
                  </h4>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {requirement.quantity} demandé • {selectedCount} sélectionné • {missingCount} manquant
                  </p>
                </div>
                <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${
                  STATUS_STYLES[req.status] || 'bg-gray-50 text-gray-700 border-gray-200'
                }`}>
                  {STATUS_LABELS[req.status] || req.status}
                </span>
              </div>

              {req.selected.length > 0 && (
                <div className="space-y-2">
                  {req.selected.map((candidate) => (
                    <div key={candidate.server_id} className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">{candidate.name}</p>
                        <p className="text-xs text-gray-500">
                          {candidate.experience_years} ans • Niveau {candidate.main_skill_level}/10 • {candidate.availability_status === 'AVAILABLE' ? 'Disponible' : 'Indisponible'}
                        </p>
                      </div>
                      <div className="text-right ml-4">
                        <p className="text-sm font-bold text-[#D4AF37]">{candidate.score?.toFixed(1) ?? '—'}</p>
                        <p className="text-xs text-gray-500">
                          {candidate.distance_km !== null && candidate.distance_km !== undefined
                            ? `${candidate.distance_km.toFixed(1)} km`
                            : '—'}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {req.candidates.length > 0 && (
                <details className="mt-2">
                  <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                    Voir tous les candidats ({req.candidates.length})
                  </summary>
                  <div className="mt-2 space-y-1">
                    {req.candidates.map((candidate) => (
                      <div key={candidate.server_id} className="flex items-center justify-between text-xs px-2 py-1 bg-white rounded border border-gray-50">
                        <span className="text-gray-700">{candidate.name}</span>
                        <span className="text-gray-500">
                          Score: {candidate.score?.toFixed(1) ?? '—'}
                          {candidate.distance_km !== null && candidate.distance_km !== undefined && ` • ${candidate.distance_km.toFixed(1)} km`}
                        </span>
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-6 flex items-center justify-between">
        <p className="text-xs text-gray-400 italic">
          Ces recommandations sont générées par le moteur de sélection. Aucune affectation n'a encore été enregistrée.
        </p>
        <button
          onClick={handleConfirmClick}
          className="px-4 py-2 bg-[#D4AF37] text-white text-sm font-medium rounded-lg hover:bg-[#B8941E] transition-colors"
        >
          Confirmer l'équipe
        </button>
      </div>

      <ConfirmStaffDialog
        open={confirmOpen}
        onClose={handleDialogClose}
        onConfirm={handleConfirm}
        loading={confirmLoading}
        result={confirmResult}
        error={confirmError}
        selectedCount={selectedAssignments.length}
        totalRequested={totalRequested}
        assignments={dialogAssignments}
      />
    </div>
  );
}

