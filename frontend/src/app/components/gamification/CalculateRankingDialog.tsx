'use client';

import { useFocusTrap } from '@/app/components/ui/FocusTrap';

interface CalculateRankingDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  loading: boolean;
  year: number;
  month: number;
}

const MONTH_NAMES = [
  'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
];

export default function CalculateRankingDialog({ open, onClose, onConfirm, loading, year, month }: CalculateRankingDialogProps) {
  const containerRef = useFocusTrap({ onClose, closeOnEscape: true, restoreFocus: true });

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="calculate-ranking-dialog-title">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div ref={containerRef} className="relative bg-white rounded-xl border border-gray-200 shadow-2xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 id="calculate-ranking-dialog-title" className="text-lg font-semibold text-gray-900">Calculer le classement mensuel</h3>
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

        <p className="text-sm text-gray-600 mb-4">
          Le classement sera recalculé à partir des transactions de points du mois sélectionné.
        </p>

        <div className="bg-gray-50 rounded-lg p-3 mb-4">
          <p className="text-sm text-gray-700">
            Mois: <span className="font-semibold">{MONTH_NAMES[month - 1]} {year}</span>
          </p>
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
            {loading ? 'Calcul...' : 'Calculer'}
          </button>
        </div>
      </div>
    </div>
  );
}
