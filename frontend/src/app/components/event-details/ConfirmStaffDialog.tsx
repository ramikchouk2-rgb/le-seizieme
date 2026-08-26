'use client';

import { useState } from 'react';
import { useFocusTrap } from '@/app/components/ui/FocusTrap';
import { ConfirmStaffResponse, ConfirmStaffAssignmentResponse } from '@/app/lib/api';

interface ConfirmStaffDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  loading: boolean;
  result: ConfirmStaffResponse | null;
  error: string | null;
  selectedCount: number;
  totalRequested: number;
  assignments: ConfirmStaffAssignmentResponse[];
}

export default function ConfirmStaffDialog({
  open,
  onClose,
  onConfirm,
  loading,
  result,
  error,
  selectedCount,
  totalRequested,
  assignments,
}: ConfirmStaffDialogProps) {
  const containerRef = useFocusTrap({ onClose, closeOnEscape: true, restoreFocus: true });

  if (!open) return null;

  const covered = assignments.length;
  const missing = totalRequested - covered;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="confirm-staff-dialog-title">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div ref={containerRef} className="relative bg-white rounded-xl border border-gray-200 shadow-2xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 id="confirm-staff-dialog-title" className="text-lg font-semibold text-gray-900">Confirmer l'équipe</h3>
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
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {result ? (
          <div className="space-y-4">
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
              <p className="text-sm font-medium text-green-800">
                Équipe confirmée avec succès.
              </p>
              <p className="text-xs text-green-600 mt-1">
                {result.created_count} affectation{result.created_count !== 1 ? 's' : ''} créée{result.created_count !== 1 ? 's' : ''}.
              </p>
              {result.missing_positions > 0 && (
                <p className="text-xs text-amber-600 mt-1">
                  Attention : {result.missing_positions} poste{result.missing_positions !== 1 ? 's' : ''} restent à pourvoir.
                </p>
              )}
            </div>
            <div className="flex justify-end">
              <button
                onClick={onClose}
                className="px-4 py-2 bg-[#D4AF37] text-white text-sm font-medium rounded-lg hover:bg-[#B8941E] transition-colors"
              >
                Fermer
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              Vous êtes sur le point d'affecter <span className="font-semibold">{selectedCount}</span> serveur{selectedCount !== 1 ? 's' : ''} à cet événement.
            </p>

            <div className="grid grid-cols-3 gap-3">
              <div className="bg-gray-50 rounded-lg p-3 text-center">
                <p className="text-xl font-bold text-gray-900">{selectedCount}</p>
                <p className="text-xs text-gray-500">Sélectionné{selectedCount !== 1 ? 's' : ''}</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3 text-center">
                <p className="text-xl font-bold text-green-600">{covered}/{totalRequested}</p>
                <p className="text-xs text-gray-500">Postes couverts</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3 text-center">
                <p className="text-xl font-bold text-amber-600">{missing}</p>
                <p className="text-xs text-gray-500">Manquant{missing !== 1 ? 's' : ''}</p>
              </div>
            </div>

            {missing > 0 && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                <p className="text-xs text-amber-700">
                  Attention : {missing} poste{missing !== 1 ? 's' : ''} restent à pourvoir.
                </p>
              </div>
            )}

            <div className="flex justify-end gap-2">
              <button
                onClick={onClose}
                disabled={loading}
                className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Annuler
              </button>
              <button
                onClick={onConfirm}
                disabled={loading}
                className="px-4 py-2 text-sm font-medium rounded-lg bg-[#D4AF37] text-white hover:bg-[#B8941E] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? 'Confirmation...' : `Confirmer ${selectedCount} affectation${selectedCount !== 1 ? 's' : ''}`}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
