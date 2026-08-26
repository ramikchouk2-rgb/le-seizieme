'use client';

import { useCallback, type ReactNode } from 'react';
import { useFocusTrap } from './FocusTrap';

interface AccessibleDialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: ReactNode;
  maxWidth?: string;
}

export default function AccessibleDialog({
  open,
  onClose,
  title,
  description,
  children,
  maxWidth = 'max-w-md',
}: AccessibleDialogProps) {
  const containerRef = useFocusTrap({ onClose, closeOnEscape: true, restoreFocus: true });

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    }
  }, [onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="dialog-title" aria-describedby={description ? 'dialog-description' : undefined}>
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div ref={containerRef} className={`relative bg-white rounded-xl border border-gray-200 shadow-2xl w-full ${maxWidth} p-6`}>
        <div className="flex items-center justify-between mb-4">
          <h3 id="dialog-title" className="text-lg font-semibold text-gray-900">{title}</h3>
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

        {description && (
          <p id="dialog-description" className="text-sm text-gray-500 mb-4">{description}</p>
        )}

        {children}
      </div>
    </div>
  );
}
