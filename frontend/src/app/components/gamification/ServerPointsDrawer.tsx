'use client';

import { useFocusTrap } from '@/app/components/ui/FocusTrap';
import { ServerPoints } from '@/app/lib/api';

interface ServerPointsDrawerProps {
  open: boolean;
  onClose: () => void;
  server: ServerPoints | null;
  loading?: boolean;
}

const TYPE_LABELS: Record<string, string> = {
  EARNED: 'Points gagnés',
  BONUS: 'Bonus',
  COMPENSATION: 'Compensation',
  PENALTY: 'Pénalité',
  ADJUSTMENT: 'Ajustement',
};

export default function ServerPointsDrawer({ open, onClose, server, loading = false }: ServerPointsDrawerProps) {
  const containerRef = useFocusTrap({ onClose, closeOnEscape: true, restoreFocus: true });

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="server-points-drawer-title">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div ref={containerRef} className="relative bg-white rounded-xl border border-gray-200 shadow-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h3 id="server-points-drawer-title" className="text-lg font-semibold text-gray-900">{server?.server_name || 'Points du serveur'}</h3>
            <p className="text-sm text-gray-500 mt-1">
              Total: <span className="font-bold text-[#D4AF37]">{server?.total_points ?? 0}</span> points
            </p>
          </div>
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

        <div className="p-6 overflow-y-auto max-h-[60vh]">
          {loading ? (
            <p className="text-sm text-gray-500">Chargement...</p>
          ) : !server ? (
            <p className="text-sm text-gray-500">Serveur introuvable.</p>
          ) : (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-xs text-gray-500 uppercase tracking-wide">Points de présence</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">{server.completion_points}</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-xs text-gray-500 uppercase tracking-wide">Points de performance</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">{server.performance_points}</p>
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-3">Historique des transactions</h4>
                {server.transactions.length === 0 ? (
                  <p className="text-sm text-gray-500">Aucune transaction de points.</p>
                ) : (
                  <div className="space-y-2">
                    {server.transactions.map((tx) => (
                      <div key={tx.transaction_id} className="flex items-center justify-between bg-gray-50 rounded-lg px-4 py-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className={`text-sm font-bold ${tx.points >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                              {tx.points >= 0 ? '+' : ''}{tx.points}
                            </span>
                            <span className="text-xs text-gray-500 bg-gray-200 px-2 py-0.5 rounded-full">
                              {TYPE_LABELS[tx.type] || tx.type}
                            </span>
                          </div>
                          <p className="text-xs text-gray-600 mt-1 truncate">{tx.description || '-'}</p>
                          {tx.event_id && (
                            <p className="text-xs text-gray-400">Événement: {tx.event_id.slice(0, 8)}...</p>
                          )}
                        </div>
                        <div className="text-xs text-gray-400 ml-4 whitespace-nowrap">
                          {tx.created_at ? new Date(tx.created_at).toLocaleString('fr-FR') : '-'}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                <p className="text-xs text-gray-400 mt-3 italic">
                  Les transactions de points sont immuables.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
