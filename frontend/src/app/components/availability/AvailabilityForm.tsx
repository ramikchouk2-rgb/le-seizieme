'use client';

import { useState, useEffect } from 'react';
import { useFocusTrap } from '@/app/components/ui/FocusTrap';

interface AvailabilityFormItem {
  id?: string;
  start_datetime: string;
  end_datetime: string;
  status: string;
  note?: string | null;
}

interface AvailabilityFormProps {
  serverId: string;
  item: AvailabilityFormItem | null;
  onSave: (data: { start_datetime: string; end_datetime: string; status?: string; note?: string }) => Promise<void>;
  onClose: () => void;
  loading: boolean;
}

export default function AvailabilityForm({ serverId, item, onSave, onClose, loading }: AvailabilityFormProps) {
  const [start_datetime, setStart] = useState(item?.start_datetime ? new Date(item.start_datetime).toISOString().slice(0, 16) : '');
  const [end_datetime, setEnd] = useState(item?.end_datetime ? new Date(item.end_datetime).toISOString().slice(0, 16) : '');
  const [status, setStatus] = useState(item?.status || 'AVAILABLE');
  const [note, setNote] = useState(item?.note || '');
  const [error, setError] = useState('');

  const containerRef = useFocusTrap({ onClose, closeOnEscape: true, restoreFocus: true });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await onSave({ start_datetime, end_datetime, status, note });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors de la sauvegarde.');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="availability-form-dialog-title">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div ref={containerRef} className="relative bg-white rounded-xl border border-gray-200 shadow-2xl w-full max-w-md p-6">
        <h3 id="availability-form-dialog-title" className="text-lg font-semibold text-gray-900 mb-4">
          {item ? 'Modifier la disponibilité' : 'Nouvelle disponibilité'}
        </h3>
        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-50 text-red-700 text-sm border border-red-200">
            {error}
          </div>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="availability-start" className="block text-sm font-medium text-gray-700 mb-1">Début</label>
            <input
              id="availability-start"
              type="datetime-local"
              value={start_datetime}
              onChange={(e) => setStart(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]"
              required
            />
          </div>
          <div>
            <label htmlFor="availability-end" className="block text-sm font-medium text-gray-700 mb-1">Fin</label>
            <input
              id="availability-end"
              type="datetime-local"
              value={end_datetime}
              onChange={(e) => setEnd(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]"
              required
            />
          </div>
          <div>
            <label htmlFor="availability-status" className="block text-sm font-medium text-gray-700 mb-1">Statut</label>
            <select
              id="availability-status"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]"
            >
              <option value="AVAILABLE">Disponible</option>
              <option value="UNAVAILABLE">Indisponible</option>
              <option value="RESERVED">Réservé</option>
            </select>
          </div>
          <div>
            <label htmlFor="availability-note" className="block text-sm font-medium text-gray-700 mb-1">Note</label>
            <textarea
              id="availability-note"
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
              {loading ? 'En cours...' : item ? 'Modifier' : 'Créer'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
