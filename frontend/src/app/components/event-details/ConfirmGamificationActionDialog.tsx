'use client';

import { useFocusTrap } from '@/app/components/ui/FocusTrap';

interface ConfirmGamificationActionDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  loading: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
}

export default function ConfirmGamificationActionDialog({
  open,
  onClose,
  onConfirm,
  loading,
  title,
  message,
  confirmLabel = 'Confirmer',
}: ConfirmGamificationActionDialogProps) {
  const containerRef = useFocusTrap({ onClose, closeOnEscape: true, restoreFocus: true });

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="gamification-dialog-title">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div ref={containerRef} className="relative bg-white rounded-xl border border-gray-200 shadow-2xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 id="gamification-dialog-title" className="text-lg font-semibold text-gray-900">{title}</h3>
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

        <p className="text-sm text-gray-600 mb-4">{message}</p>

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
            {loading ? 'Traitement...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
