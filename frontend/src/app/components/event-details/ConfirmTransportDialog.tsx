'use client';

import { useFocusTrap } from '@/app/components/ui/FocusTrap';
import { TransportConfirmationResponse, TransportConfirmationGroupResponse } from '@/app/lib/api';

interface ConfirmTransportDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  loading: boolean;
  result: TransportConfirmationResponse | null;
  error: string | null;
  groups: TransportConfirmationGroupResponse[];
}

export default function ConfirmTransportDialog({
  open,
  onClose,
  onConfirm,
  loading,
  result,
  error,
  groups,
}: ConfirmTransportDialogProps) {
  const containerRef = useFocusTrap({ onClose, closeOnEscape: true, restoreFocus: true });

  if (!open) return null;

  const totalPassengers = groups.reduce((sum, g) => sum + g.passenger_count, 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="confirm-transport-dialog-title">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div ref={containerRef} className="relative bg-white rounded-xl border border-gray-200 shadow-2xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 id="confirm-transport-dialog-title" className="text-lg font-semibold text-gray-900">Confirmer le transport</h3>
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
                Transport confirmé avec succès.
              </p>
              <p className="text-xs text-green-600 mt-1">
                {result.groups_created} groupe{result.groups_created !== 1 ? 's' : ''} et {result.passengers_created} passager{result.passengers_created !== 1 ? 's' : ''} créés.
              </p>
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
                Vous êtes sur le point d'enregistrer <span className="font-semibold">{groups.length}</span> groupe{groups.length !== 1 ? 's' : ''} de transport.
              </p>

            <div className="space-y-3">
              {groups.map((group, index) => (
                <div key={group.group_id} className="bg-gray-50 rounded-lg p-3">
                  <p className="text-sm font-semibold text-gray-900">Groupe {index + 1}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    🚗 {group.driver_name} • {group.vehicle} • {group.capacity} places
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {group.passenger_count} passager{group.passenger_count !== 1 ? 's' : ''}
                    {group.estimated_distance_km !== undefined && ` • ${group.estimated_distance_km.toFixed(1)} km estimés`}
                  </p>
                </div>
              ))}
            </div>

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
                {loading ? 'Confirmation...' : `Confirmer ${groups.length} groupe${groups.length !== 1 ? 's' : ''}`}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
