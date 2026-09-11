'use client';

import { useState, useEffect } from 'react';
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
  const [selectedServers, setSelectedServers] = useState<Set<string>>(new Set());
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

  // Initialize selected servers from backend recommendations
  const initializeSelection = () => {
    const initial = new Set<string>();
    for (const req of recommendations.requirements) {
      for (const candidate of req.selected) {
        initial.add(candidate.server_id);
      }
    }
    setSelectedServers(initial);
  };

  // Run initialization once
  const [initialized, setInitialized] = useState(false);
  if (!initialized) {
    initializeSelection();
    setInitialized(true);
  }

  const totalRequested = recommendations.requirements.reduce(
    (sum, req) => sum + req.requirement.quantity,
    0
  );
  const totalSelected = selectedServers.size;
  const totalMissing = totalRequested - totalSelected;

  const selectedAssignments: ConfirmStaffAssignmentRequest[] = [];
  for (const req of recommendations.requirements) {
    for (const candidate of req.selected) {
      if (selectedServers.has(candidate.server_id)) {
        selectedAssignments.push({
          server_id: candidate.server_id,
          role: req.requirement.role_name,
        });
      }
    }
    // Also check candidates that might have been manually selected
    for (const candidate of req.candidates) {
      if (selectedServers.has(candidate.server_id) && !req.selected.some(s => s.server_id === candidate.server_id)) {
        selectedAssignments.push({
          server_id: candidate.server_id,
          role: req.requirement.role_name,
        });
      }
    }
  }

  const toggleServerSelection = (serverId: string, requirementId: string) => {
    setSelectedServers(prev => {
      const next = new Set(prev);
      if (next.has(serverId)) {
        next.delete(serverId);
      } else {
        // Check if we're at capacity for this requirement
        const req = recommendations.requirements.find(r => r.requirement.requirement_id === requirementId);
        if (req) {
          const currentSelected = req.selected.filter(s => next.has(s.server_id)).length;
          const manuallySelected = req.candidates.filter(c => next.has(c.server_id) && !req.selected.some(s => s.server_id === c.server_id)).length;
          if (currentSelected + manuallySelected >= req.requirement.quantity) {
            // At capacity, don't add
            return prev;
          }
        }
        next.add(serverId);
      }
      return next;
    });
  };

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
          <p className="text-xs text-gray-500">Sélectionnés</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-amber-600">{totalMissing}</p>
          <p className="text-xs text-gray-500">Manquants</p>
        </div>
      </div>

      <div className="space-y-4">
        {recommendations.requirements.map((req) => {
          const requirement = req.requirement;
          const selectedCount = req.selected.filter(s => selectedServers.has(s.server_id)).length;
          const manuallySelectedCount = req.candidates.filter(c => selectedServers.has(c.server_id) && !req.selected.some(s => s.server_id === c.server_id)).length;
          const totalForReq = selectedCount + manuallySelectedCount;
          const missingCount = requirement.quantity - totalForReq;

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
                    {requirement.quantity} demandé • {totalForReq} sélectionné • {missingCount} manquant
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
                  {req.selected.map((candidate) => {
                    const isSelected = selectedServers.has(candidate.server_id);
                    return (
                      <div key={candidate.server_id} className={`flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2 ${isSelected ? 'bg-green-50 border border-green-100' : ''}`}>
                        <div className="flex items-center gap-3 flex-1 min-w-0">
                          <button
                            onClick={() => toggleServerSelection(candidate.server_id, requirement.requirement_id)}
                            className={`w-4 h-4 rounded border-2 flex-shrink-0 ${isSelected ? 'bg-[#D4AF37] border-[#D4AF37]' : 'border-gray-300'} text-white focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30`}
                            aria-label={isSelected ? 'Désélectionner' : 'Sélectionner'}
                          >
                            {isSelected && (
                              <svg className="w-3 h-3 mx-auto my-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                              </svg>
                            )}
                          </button>
                          <Link
                            href={`/dashboard/servers/${candidate.server_id}`}
                            className="flex-1 min-w-0"
                          >
                            <p className="text-sm font-medium text-gray-900 truncate">{candidate.name}</p>
                            <p className="text-xs text-gray-500">
                              {candidate.experience_years} ans • Niveau {candidate.main_skill_level}/10 • {candidate.availability_status === 'AVAILABLE' ? 'Disponible' : 'Indisponible'}
                            </p>
                          </Link>
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
                    );
                  })}
                </div>
              )}

              {req.candidates.length > 0 && (
                <details className="mt-2">
                  <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                    Voir tous les candidats ({req.candidates.length})
                  </summary>
                  <div className="mt-2 space-y-1">
                    {req.candidates.map((candidate) => {
                      const isSelected = selectedServers.has(candidate.server_id);
                      const isAlreadySelected = req.selected.some(s => s.server_id === candidate.server_id);
                      const canSelect = !isSelected && (selectedCount + manuallySelectedCount < requirement.quantity || isAlreadySelected);
                      
                      return (
                        <div key={candidate.server_id} className={`flex items-center justify-between text-xs px-2 py-1 bg-white rounded border border-gray-50 ${isSelected ? 'bg-green-50 border-green-100' : ''}`}>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => !isAlreadySelected && toggleServerSelection(candidate.server_id, requirement.requirement_id)}
                              disabled={!canSelect && !isSelected}
                              className={`w-4 h-4 rounded border-2 flex-shrink-0 ${isSelected ? 'bg-[#D4AF37] border-[#D4AF37]' : 'border-gray-300'} text-white focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 disabled:opacity-50 disabled:cursor-not-allowed`}
                              aria-label={isSelected ? 'Désélectionner' : 'Sélectionner'}
                            >
                              {isSelected && (
                                <svg className="w-3 h-3 mx-auto my-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                </svg>
                              )}
                            </button>
                            <Link
                              href={`/dashboard/servers/${candidate.server_id}`}
                              className="text-gray-700 hover:text-[#D4AF37] truncate"
                            >
                              {candidate.name}
                            </Link>
                          </div>
                          <span className="text-gray-500">
                            Score: {candidate.score?.toFixed(1) ?? '—'}
                            {candidate.distance_km !== null && candidate.distance_km !== undefined && ` • ${candidate.distance_km.toFixed(1)} km`}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </details>
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-6 flex items-center justify-between">
        <p className="text-xs text-gray-400 italic">
          Ces recommandations sont générées par le moteur de sélection. Cliquez sur un serveur pour le sélectionner/désélectionner.
        </p>
        <button
          onClick={handleConfirmClick}
          disabled={totalSelected === 0}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            totalSelected === 0
              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
              : 'bg-[#D4AF37] text-white hover:bg-[#B8941E]'
          }`}
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

