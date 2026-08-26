'use client';

import { useState, useEffect } from 'react';
import { StaffAssignment, ASSIGNMENT_STATUSES } from '@/app/components/dashboard/types';
import {
  addStaffAssignment,
  removeStaffAssignment,
  updateStaffAssignment,
  StaffAssignmentResponse,
  AddStaffAssignmentRequest,
} from '@/app/lib/api';
import AddStaffDialog from './AddStaffDialog';
import UpdateStaffDialog from './UpdateStaffDialog';
import { useAnnouncer } from '@/app/components/ui/Announcer';

interface StaffManagementPanelProps {
  assignments: StaffAssignment[];
  eventId: string;
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
  onRefresh: () => void;
}

export default function StaffManagementPanel({
  assignments,
  eventId,
  requirements,
  onRefresh,
}: StaffManagementPanelProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [updateDialogOpen, setUpdateDialogOpen] = useState(false);
  const [selectedAssignment, setSelectedAssignment] = useState<StaffAssignment | null>(null);
  const { announceSuccess, announceError } = useAnnouncer();

  const totalRequested = requirements.reduce((sum, r) => sum + r.quantity, 0);
  const totalSelected = assignments.length;
  const totalMissing = totalRequested - totalSelected;

  const handleAdd = async (payload: AddStaffAssignmentRequest) => {
    setLoading(true);
    setError(null);
    try {
      await addStaffAssignment(eventId, payload);
      setSuccess('Serveur affecté avec succès.');
      setAddDialogOpen(false);
      onRefresh();
      announceSuccess('Serveur affecté avec succès.');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Impossible d\'affecter le serveur.';
      setError(message);
      announceError('Opération impossible. Veuillez réessayer.');
    } finally {
      setLoading(false);
    }
  };

  const handleRemove = async (assignmentId: string) => {
    setLoading(true);
    setError(null);
    try {
      await removeStaffAssignment(eventId, assignmentId);
      setSuccess('Affectation supprimée avec succès.');
      onRefresh();
      announceSuccess('Affectation supprimée avec succès.');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Impossible de supprimer l\'affectation.';
      setError(message);
      announceError('Opération impossible. Veuillez réessayer.');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (payload: { role?: string; assignment_status?: string; requirement_id?: string }) => {
    if (!selectedAssignment) return;
    setLoading(true);
    setError(null);
    try {
      await updateStaffAssignment(eventId, selectedAssignment.id, payload);
      setSuccess('Affectation modifiée avec succès.');
      setUpdateDialogOpen(false);
      setSelectedAssignment(null);
      onRefresh();
      announceSuccess('Affectation modifiée avec succès.');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Impossible de modifier l\'affectation.';
      setError(message);
      announceError('Opération impossible. Veuillez réessayer.');
    } finally {
      setLoading(false);
    }
  };

  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'CONFIRMED':
        return 'bg-green-50 text-green-700 border-green-200';
      case 'PROPOSED':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'DECLINED':
        return 'bg-red-50 text-red-700 border-red-200';
      case 'CANCELLED':
        return 'bg-gray-50 text-gray-700 border-gray-200';
      case 'COMPLETED':
        return 'bg-purple-50 text-purple-700 border-purple-200';
      default:
        return 'bg-gray-50 text-gray-700 border-gray-200';
    }
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm mb-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Équipe affectée</h3>
          <p className="text-sm text-gray-500">
            {totalSelected} / {totalRequested} postes
            {totalMissing > 0 && <span className="text-red-600 ml-2">{totalMissing} poste{totalMissing > 1 ? 's' : ''} encore à pourvoir</span>}
          </p>
        </div>
        <button
          onClick={() => setAddDialogOpen(true)}
          disabled={loading}
          className="px-3 py-1.5 text-sm font-medium rounded-lg bg-[#D4AF37] text-white hover:bg-[#B8941E] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Ajouter un serveur
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

      {assignments.length === 0 ? (
        <p className="text-sm text-gray-500">Aucun serveur affecté à cet événement.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th scope="col" className="text-left py-2 px-2 font-medium text-gray-500">Serveur</th>
                <th scope="col" className="text-left py-2 px-2 font-medium text-gray-500">Rôle</th>
                <th scope="col" className="text-left py-2 px-2 font-medium text-gray-500">Expérience</th>
                <th scope="col" className="text-left py-2 px-2 font-medium text-gray-500">Compétence</th>
                <th scope="col" className="text-left py-2 px-2 font-medium text-gray-500">Score</th>
                <th scope="col" className="text-left py-2 px-2 font-medium text-gray-500">Statut</th>
                <th scope="col" className="text-right py-2 px-2 font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody>
              {assignments.map((assignment) => (
                <tr key={assignment.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-3 px-2">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-[#D4AF37]/10 flex items-center justify-center text-[#D4AF37] text-xs font-bold">
                        {(assignment.first_name?.[0] || '?').toUpperCase()}{(assignment.last_name?.[0] || '?').toUpperCase()}
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">
                          {assignment.first_name} {assignment.last_name}
                        </p>
                        <p className="text-xs text-gray-500">{assignment.city}</p>
                      </div>
                    </div>
                  </td>
                  <td className="py-3 px-2 text-gray-700">{assignment.role}</td>
                  <td className="py-3 px-2 text-gray-700">{assignment.years_experience} ans</td>
                  <td className="py-3 px-2 text-gray-700">{assignment.skill_level}/10</td>
                  <td className="py-3 px-2 text-gray-700">
                    {assignment.score != null ? assignment.score.toFixed(1) : '-'}
                  </td>
                  <td className="py-3 px-2">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${getStatusStyle(assignment.status)}`}>
                      {ASSIGNMENT_STATUSES[assignment.status as keyof typeof ASSIGNMENT_STATUSES] || assignment.status}
                    </span>
                  </td>
                  <td className="py-3 px-2 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => {
                          setSelectedAssignment(assignment);
                          setUpdateDialogOpen(true);
                        }}
                        disabled={loading || assignment.status === 'CONFIRMED'}
                        className="p-1 text-gray-500 hover:text-[#D4AF37] rounded disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Modifier"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => handleRemove(assignment.id)}
                        disabled={loading || assignment.status === 'CONFIRMED'}
                        className="p-1 text-gray-500 hover:text-red-600 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Supprimer"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {addDialogOpen && (
        <AddStaffDialog
          eventId={eventId}
          onClose={() => setAddDialogOpen(false)}
          onSave={handleAdd}
          requirements={requirements}
          loading={loading}
        />
      )}

      {updateDialogOpen && selectedAssignment && (
        <UpdateStaffDialog
          onClose={() => {
            setUpdateDialogOpen(false);
            setSelectedAssignment(null);
          }}
          onSave={handleUpdate}
          assignment={selectedAssignment}
          requirements={requirements}
          loading={loading}
        />
      )}
    </div>
  );
}
