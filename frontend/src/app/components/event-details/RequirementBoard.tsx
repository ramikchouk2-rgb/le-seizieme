'use client';

import { useState } from 'react';
import { RequirementDetail, RequirementCreateRequest, RequirementUpdateRequest, createEventRequirement, updateEventRequirement, deleteEventRequirement } from '@/app/lib/api';
import RequirementForm from './RequirementForm';
import DeleteRequirementDialog from './DeleteRequirementDialog';
import { useAnnouncer } from '@/app/components/ui/Announcer';

interface RequirementBoardProps {
  requirements: RequirementDetail[];
  eventId: string;
  onRefresh?: () => void;
}

export default function RequirementBoard({ requirements, eventId, onRefresh }: RequirementBoardProps) {
  const [showForm, setShowForm] = useState(false);
  const [editingRequirement, setEditingRequirement] = useState<RequirementDetail | null>(null);
  const [deletingRequirement, setDeletingRequirement] = useState<RequirementDetail | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const { announceSuccess, announceError } = useAnnouncer();

  const getStatus = (selected: number, quantity: number) => {
    if (selected === quantity) return 'COMPLET';
    if (selected === 0 && quantity > 0) return 'CRITIQUE';
    return 'INCOMPLET';
  };

  const getStatusStyles = (status: string) => {
    switch (status) {
      case 'COMPLET':
        return 'bg-green-50 text-green-700 border-green-200';
      case 'CRITIQUE':
        return 'bg-red-50 text-red-700 border-red-200';
      default:
        return 'bg-amber-50 text-amber-700 border-amber-200';
    }
  };

  const handleSave = async (data: RequirementCreateRequest | RequirementUpdateRequest) => {
    setSaving(true);
    setError(null);
    try {
      if (editingRequirement) {
        await updateEventRequirement(eventId, editingRequirement.requirement_id, data);
        setSuccess('Poste modifié avec succès.');
        announceSuccess('Poste modifié avec succès.');
      } else {
        await createEventRequirement(eventId, data as RequirementCreateRequest);
        setSuccess('Poste ajouté avec succès.');
        announceSuccess('Poste ajouté avec succès.');
      }
      setShowForm(false);
      setEditingRequirement(null);
      onRefresh?.();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Impossible d\'enregistrer le poste.';
      setError(message);
      announceError('Opération impossible. Veuillez réessayer.');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deletingRequirement) return;
    setDeleting(true);
    setError(null);
    try {
      await deleteEventRequirement(eventId, deletingRequirement.requirement_id);
      setSuccess('Poste supprimé avec succès.');
      setDeletingRequirement(null);
      onRefresh?.();
      announceSuccess('Poste supprimé avec succès.');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Impossible de supprimer le poste.';
      setError(message);
      announceError('Opération impossible. Veuillez réessayer.');
    } finally {
      setDeleting(false);
    }
  };

  const handleEdit = (req: RequirementDetail) => {
    setEditingRequirement(req);
    setShowForm(true);
  };

  const handleAdd = () => {
    setEditingRequirement(null);
    setShowForm(true);
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm mb-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Postes requis</h3>
        <button
          onClick={handleAdd}
          className="px-3 py-1.5 text-sm font-medium rounded-lg bg-[#D4AF37] text-white hover:bg-[#B8941E] transition-colors"
        >
          Ajouter un poste
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
          {error}
        </div>
      )}

      {success && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-600">
          {success}
        </div>
      )}

      {requirements.length === 0 ? (
        <p className="text-sm text-gray-500">Aucun poste requis pour cet événement.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {requirements.map((req) => {
            const status = getStatus(req.selected, req.quantity);
            const percentage = req.quantity > 0 ? Math.round((req.selected / req.quantity) * 100) : 0;

            return (
              <div key={req.requirement_id} className="bg-gray-50 rounded-lg p-4">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h4 className="text-sm font-semibold text-gray-900">
                      {req.role_name}
                      {req.required_gender && (
                        <span className="text-gray-500 ml-1">
                          — {req.required_gender === 'MALE' ? 'Hommes' : req.required_gender === 'FEMALE' ? 'Femmes' : req.required_gender}
                        </span>
                      )}
                    </h4>
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border mt-1 ${getStatusStyles(status)}`}>
                      {status}
                    </span>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-gray-900">{req.selected} / {req.quantity}</p>
                    <div className="flex gap-1 mt-1">
                      <button
                        onClick={() => handleEdit(req)}
                        className="p-1 text-gray-500 hover:text-[#D4AF37] rounded"
                        title="Modifier"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => setDeletingRequirement(req)}
                        className="p-1 text-gray-500 hover:text-red-600 rounded"
                        title="Supprimer"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>

                <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden mb-3">
                  <div
                    className={`h-2 rounded-full transition-all duration-500 ${
                      percentage === 100 ? 'bg-green-500' : percentage >= 50 ? 'bg-[#D4AF37]' : 'bg-red-500'
                    }`}
                    style={{ width: `${percentage}%` }}
                  />
                </div>

                <div className="space-y-1 text-xs text-gray-600">
                  <div className="flex items-center justify-between">
                    <span>Postes manquants</span>
                    <span className="font-medium text-red-600">{req.missing}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Exp. minimum</span>
                    <span>{req.minimum_experience} ans</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Compétence min.</span>
                    <span>{req.minimum_skill_level}/10</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {showForm && (
        <RequirementForm
          onClose={() => {
            setShowForm(false);
            setEditingRequirement(null);
          }}
          onSave={handleSave}
          initial={editingRequirement ? {
            role_name: editingRequirement.role_name,
            quantity: editingRequirement.quantity,
            minimum_skill_level: editingRequirement.minimum_skill_level,
            minimum_experience: editingRequirement.minimum_experience,
            required_gender: editingRequirement.required_gender,
          } : undefined}
          saving={saving}
        />
      )}

      {deletingRequirement && (
        <DeleteRequirementDialog
          open={!!deletingRequirement}
          onClose={() => setDeletingRequirement(null)}
          onConfirm={handleDelete}
          loading={deleting}
          requirementName={deletingRequirement.role_name}
        />
      )}
    </div>
  );
}
