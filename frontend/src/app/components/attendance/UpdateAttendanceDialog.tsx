'use client';

import { useState, useEffect } from 'react';
import { useFocusTrap } from '@/app/components/ui/FocusTrap';

interface UpdateAttendanceDialogProps {
  item: {
    id: string;
    server_name: string;
    role: string;
    status: string;
  } | null;
  onConfirm: (status: string, note?: string) => Promise<void>;
  onClose: () => void;
  loading: boolean;
}

export default function UpdateAttendanceDialog({ item, onConfirm, onClose, loading }: UpdateAttendanceDialogProps) {
  const [status, setStatus] = useState(item?.status || 'EXPECTED');
  const [note, setNote] = useState('');
  const [error, setError] = useState('');
  const containerRef = useFocusTrap({ onClose, closeOnEscape: true, restoreFocus: true });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await onConfirm(status, note || undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors de la mise à jour.');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="update-attendance-dialog-title">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div ref={containerRef} className="relative bg-white rounded-xl border border-gray-200 shadow-2xl w-full max-w-md p-6">
        <h3 id="update-attendance-dialog-title" className="text-lg font-semibold text-gray-900 mb-2">Corriger la présence</h3>
        <p className="text-sm text-gray-500 mb-4">
          Modifier le statut de <span className="font-medium text-gray-900">{item?.server_name}</span> ({item?.role})
        </p>
        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-50 text-red-700 text-sm border border-red-200">
            {error}
          </div>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="attendance-status" className="block text-sm font-medium text-gray-700 mb-1">Statut</label>
            <select
              id="attendance-status"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]"
            >
              <option value="EXPECTED">Attendu</option>
              <option value="PRESENT">Présent</option>
              <option value="LATE">Retard</option>
              <option value="ABSENT">Absent</option>
              <option value="EXCUSED">Excusé</option>
              <option value="LEFT">Parti</option>
            </select>
          </div>
          <div>
            <label htmlFor="attendance-note" className="block text-sm font-medium text-gray-700 mb-1">Note (optionnel)</label>
            <textarea
              id="attendance-note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]"
            />
          </div>
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
              type="submit"
              disabled={loading}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-[#D4AF37] text-white hover:bg-[#B8941E] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'En cours...' : 'Mettre à jour'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
