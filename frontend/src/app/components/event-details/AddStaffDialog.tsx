'use client';

import { useState, useEffect, useCallback } from 'react';
import { AddStaffAssignmentRequest, getEligibleStaff, EligibleStaffResponse } from '@/app/lib/api';
import { useFocusTrap } from '@/app/components/ui/FocusTrap';

interface AddStaffDialogProps {
  eventId: string;
  onClose: () => void;
  onSave: (data: AddStaffAssignmentRequest) => Promise<void>;
  requirements: {
    requirement_id: string;
    role_name: string;
    quantity: number;
    required_gender: string | null;
    minimum_experience: number;
    minimum_skill_level: number;
    selected: number;
    missing: number;
  }[];
  loading?: boolean;
}

export default function AddStaffDialog({ eventId, onClose, onSave, requirements, loading = false }: AddStaffDialogProps) {
  const [selectedRequirementId, setSelectedRequirementId] = useState('');
  const [search, setSearch] = useState('');
  const [eligibleStaff, setEligibleStaff] = useState<EligibleStaffResponse[]>([]);
  const [loadingStaff, setLoadingStaff] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedServer, setSelectedServer] = useState<EligibleStaffResponse | null>(null);

  const containerRef = useFocusTrap({ onClose, closeOnEscape: true, restoreFocus: true });

  const selectedRequirement = requirements.find((r) => r.requirement_id === selectedRequirementId);
  const remainingSpots = selectedRequirement ? selectedRequirement.quantity - selectedRequirement.selected : 0;

  useEffect(() => {
    async function loadEligible() {
      if (!selectedRequirementId) {
        setEligibleStaff([]);
        return;
      }
      setLoadingStaff(true);
      setError(null);
      try {
        const data = await getEligibleStaff(
          eventId,
          search || undefined,
          selectedRequirement?.role_name || undefined,
        );
        setEligibleStaff(data);
      } catch {
        setError('Impossible de charger les serveurs éligibles.');
        setEligibleStaff([]);
      } finally {
        setLoadingStaff(false);
      }
    }
    loadEligible();
  }, [selectedRequirementId, search, eventId, selectedRequirement?.role_name]);

  const handleSubmit = async () => {
    if (!selectedRequirementId || !selectedServer) return;
    await onSave({
      server_id: selectedServer.server_id,
      requirement_id: selectedRequirementId,
      role: selectedRequirement?.role_name || '',
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="add-staff-dialog-title">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div ref={containerRef} className="relative bg-white rounded-xl border border-gray-200 shadow-2xl w-full max-w-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 id="add-staff-dialog-title" className="text-lg font-semibold text-gray-900">Ajouter un serveur</h3>
          <button
            onClick={onClose}
            aria-label="Fermer"
            className="p-1 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
            {error}
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label htmlFor="add-staff-requirement" className="block text-sm font-medium text-gray-700 mb-1">Poste</label>
            <select
              id="add-staff-requirement"
              value={selectedRequirementId}
              onChange={(e) => {
                setSelectedRequirementId(e.target.value);
                setSelectedServer(null);
              }}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
            >
              <option value="">Sélectionner un poste</option>
              {requirements
                .filter((r) => r.missing > 0)
                .map((r) => (
                  <option key={r.requirement_id} value={r.requirement_id}>
                    {r.role_name} {r.required_gender ? `(${r.required_gender === 'MALE' ? 'Hommes' : 'Femmes'})` : ''} — {r.selected}/{r.quantity} affectés
                  </option>
                ))}
            </select>
            {selectedRequirement && (
              <p className="text-xs text-gray-500 mt-1">
                {remainingSpots} place{remainingSpots > 1 ? 's' : ''} restante{remainingSpots > 1 ? 's' : ''}
              </p>
            )}
          </div>

          {selectedRequirementId && (
            <>
              <div>
                <label htmlFor="add-staff-search" className="block text-sm font-medium text-gray-700 mb-1">Rechercher un serveur</label>
                <input
                  id="add-staff-search"
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Nom, ville..."
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
                />
              </div>

              <div className="max-h-64 overflow-y-auto border border-gray-200 rounded-lg">
                {loadingStaff ? (
                  <p className="text-sm text-gray-500 p-4 text-center">Chargement...</p>
                ) : eligibleStaff.length === 0 ? (
                  <p className="text-sm text-gray-500 p-4 text-center">Aucun serveur éligible trouvé.</p>
                ) : (
                  <div className="divide-y divide-gray-100">
                    {eligibleStaff.map((staff) => (
                      <div
                        key={staff.server_id}
                        onClick={() => setSelectedServer(staff)}
                        className={`p-3 cursor-pointer hover:bg-gray-50 ${
                          selectedServer?.server_id === staff.server_id ? 'bg-[#D4AF37]/10' : ''
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-sm font-medium text-gray-900">{staff.server_name}</p>
                            <p className="text-xs text-gray-500">
                              {staff.city} • {staff.years_experience} ans • Niveau {staff.skill_level}/10
                            </p>
                          </div>
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
                            staff.availability_status === 'AVAILABLE'
                              ? 'bg-green-50 text-green-700 border-green-200'
                              : 'bg-red-50 text-red-700 border-red-200'
                          }`}>
                            {staff.availability_status === 'AVAILABLE' ? 'Disponible' : 'Indisponible'}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        <div className="flex justify-end gap-2 pt-4">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Annuler
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading || !selectedRequirementId || !selectedServer}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-[#D4AF37] text-white hover:bg-[#B8941E] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Ajout en cours...' : 'Confirmer l\'affectation'}
          </button>
        </div>
      </div>
    </div>
  );
}
