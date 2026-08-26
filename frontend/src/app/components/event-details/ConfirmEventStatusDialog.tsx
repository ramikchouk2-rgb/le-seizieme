'use client';

import { useState } from 'react';
import { useFocusTrap } from '@/app/components/ui/FocusTrap';

interface ConfirmEventStatusDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => Promise<void>;
  title: string;
  description: string;
  confirmLabel: string;
  cancelLabel?: string;
  loading?: boolean;
}

export default function ConfirmEventStatusDialog({
  open,
  onClose,
  onConfirm,
  title,
  description,
  confirmLabel,
  cancelLabel = 'Annuler',
  loading = false,
}: ConfirmEventStatusDialogProps) {
  const containerRef = useFocusTrap({ onClose, closeOnEscape: true, restoreFocus: true });
  const [localLoading, setLocalLoading] = useState(false);

  if (!open) return null;

  const handleConfirm = async () => {
    setLocalLoading(true);
    try {
      await onConfirm();
    } finally {
      setLocalLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="confirm-dialog-title">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div ref={containerRef} className="relative bg-white rounded-xl border border-gray-200 shadow-2xl w-full max-w-md p-6">
        <h3 id="confirm-dialog-title" className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
        <p className="text-sm text-gray-500 mb-6">{description}</p>

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={localLoading || loading}
            className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {cancelLabel}
          </button>
          <button
            onClick={handleConfirm}
            disabled={localLoading || loading}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-[#D4AF37] text-white hover:bg-[#B8941E] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {localLoading || loading ? 'En cours...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
