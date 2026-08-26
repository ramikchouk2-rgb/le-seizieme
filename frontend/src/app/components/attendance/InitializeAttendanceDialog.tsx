'use client';

import { useState } from 'react';
import { useFocusTrap } from '@/app/components/ui/FocusTrap';

interface InitializeAttendanceDialogProps {
  onConfirm: () => Promise<void>;
  onClose: () => void;
  loading: boolean;
}

export default function InitializeAttendanceDialog({ onConfirm, onClose, loading }: InitializeAttendanceDialogProps) {
  const [error, setError] = useState('');
  const containerRef = useFocusTrap({ onClose, closeOnEscape: true, restoreFocus: true });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await onConfirm();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors de l\'initialisation.');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="initialize-attendance-dialog-title">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div ref={containerRef} className="relative bg-white rounded-xl border border-gray-200 shadow-2xl w-full max-w-md p-6">
        <h3 id="initialize-attendance-dialog-title" className="text-lg font-semibold text-gray-900 mb-2">Initialiser les présences</h3>
        <p className="text-sm text-gray-500 mb-4">
          Cette action va créer les enregistrements de présence pour tout le personnel confirmé de l'événement.
          Cette opération est idempotente : elle ne créera pas de doublons.
        </p>
        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-50 text-red-700 text-sm border border-red-200">
            {error}
          </div>
        )}
        <div className="flex justify-end gap-2">
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
            {loading ? 'Initialisation...' : 'Initialiser'}
          </button>
        </div>
      </div>
    </div>
  );
}
