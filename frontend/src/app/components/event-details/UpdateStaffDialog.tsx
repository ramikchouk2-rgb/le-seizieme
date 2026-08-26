'use client';

import { useState, useEffect } from 'react';
import { useFocusTrap } from '@/app/components/ui/FocusTrap';
import { StaffAssignment, ASSIGNMENT_STATUSES } from '@/app/components/dashboard/types';
import { updateStaffAssignment, UpdateStaffAssignmentRequest } from '@/app/lib/api';

interface UpdateStaffDialogProps {
  onClose: () => void;
  onSave: (data: UpdateStaffAssignmentRequest) => Promise<void>;
  assignment: StaffAssignment;
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

export default function UpdateStaffDialog({
  onClose,
  onSave,
  assignment,
  requirements,
  loading = false,
}: UpdateStaffDialogProps) {
  const [role, setRole] = useState(assignment.role);
  const [status, setStatus] = useState(assignment.status);
  const [error, setError] = useState<string | null>(null);

  const containerRef = useFocusTrap({ onClose, closeOnEscape: true, restoreFocus: true });

  useEffect(() => {
    setRole(assignment.role);
    setStatus(assignment.status);
  }, [assignment]);

  const handleSubmit = async () => {
    setError(null);
    const payload: UpdateStaffAssignmentRequest = {};
    if (role !== assignment.role) {
      payload.role = role;
    }
    if (status !== assignment.status) {
      payload.assignment_status = status;
    }
    await onSave(payload);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="update-staff-dialog-title">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div ref={containerRef} className="relative bg-white rounded-xl border border-gray-200 shadow-2xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 id="update-staff-dialog-title" className="text-lg font-semibold text-gray-900">Modifier l'affectation</h3>
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
            <label htmlFor="update-staff-server" className="block text-sm font-medium text-gray-700 mb-1">Serveur</label>
            <p className="text-sm text-gray-900">
              {assignment.first_name} {assignment.last_name}
            </p>
          </div>

          <div>
            <label htmlFor="update-staff-role" className="block text-sm font-medium text-gray-700 mb-1">Rôle</label>
            <select
              id="update-staff-role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
            >
              {requirements.map((r) => (
                <option key={r.requirement_id} value={r.role_name}>
                  {r.role_name} {r.required_gender ? `(${r.required_gender === 'MALE' ? 'Hommes' : 'Femmes'})` : ''}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="update-staff-status" className="block text-sm font-medium text-gray-700 mb-1">Statut</label>
            <select
              id="update-staff-status"
              value={status}
              onChange={(e) => setStatus(e.target.value as StaffAssignment['status'])}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
            >
              {Object.entries(ASSIGNMENT_STATUSES).map(([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
          </div>
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
            disabled={loading}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-[#D4AF37] text-white hover:bg-[#B8941E] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Enregistrement...' : 'Enregistrer'}
          </button>
        </div>
      </div>
    </div>
  );
}
