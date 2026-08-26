'use client';

import { useState, useEffect } from 'react';
import { useFocusTrap } from '@/app/components/ui/FocusTrap';

interface DeleteAvailabilityDialogProps {
  item: {
    id: string;
    start_datetime: string;
    end_datetime: string;
    status: string;
  };
  onConfirm: () => Promise<void>;
  onClose: () => void;
  loading: boolean;
}

export default function DeleteAvailabilityDialog({ item, onConfirm, onClose, loading }: DeleteAvailabilityDialogProps) {
  const [localLoading, setLocalLoading] = useState(false);
  const containerRef = useFocusTrap({ onClose, closeOnEscape: true, restoreFocus: true });

  const handleConfirm = async () => {
    setLocalLoading(true);
    try {
      await onConfirm();
    } finally {
      setLocalLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="delete-availability-dialog-title">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div ref={containerRef} className="relative bg-white rounded-xl border border-gray-200 shadow-2xl w-full max-w-md p-6">
        <h3 id="delete-availability-dialog-title" className="text-lg font-semibold text-gray-900 mb-2">Supprimer la disponibilité</h3>
        <p className="text-sm text-gray-500 mb-6">
          Voulez-vous vraiment supprimer cette disponibilité du{' '}
          {new Date(item.start_datetime).toLocaleDateString('fr-FR')} au{' '}
          {new Date(item.end_datetime).toLocaleDateString('fr-FR')} ?
        </p>
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={localLoading || loading}
            className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Annuler
          </button>
          <button
            onClick={handleConfirm}
            disabled={localLoading || loading}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {localLoading || loading ? 'Suppression...' : 'Supprimer'}
          </button>
        </div>
      </div>
    </div>
  );
}
