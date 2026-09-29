'use client';

import { AuditLogItem } from '@/app/lib/types';

interface AuditLogTableProps {
  items: AuditLogItem[];
  onDrawerOpen: (item: AuditLogItem) => void;
}

function ActionBadge({ action }: { action: string }) {
  const colors: Record<string, string> = {
    USER_CREATED: 'bg-green-50 text-green-700 border-green-200',
    USER_UPDATED: 'bg-blue-50 text-blue-700 border-blue-200',
    USER_DEACTIVATED: 'bg-red-50 text-red-700 border-red-200',
  };

  const labels: Record<string, string> = {
    USER_CREATED: 'Utilisateur créé',
    USER_UPDATED: 'Utilisateur mis à jour',
    USER_DEACTIVATED: 'Utilisateur désactivé',
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
        colors[action] || 'bg-gray-50 text-gray-700 border-gray-200'
      }`}
    >
      {labels[action] || action}
    </span>
  );
}

function formatDateTime(value?: string | null) {
  if (!value) return '—';
  const date = new Date(value.endsWith('Z') ? value : `${value}Z`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatDetail(detail: Record<string, unknown> | null): string {
  if (!detail || Object.keys(detail).length === 0) return '—';
  const keys = Object.keys(detail).slice(0, 3);
  const preview = keys.map((k) => `${k}: ${String(detail[k]).slice(0, 30)}`).join(', ');
  return keys.length < Object.keys(detail).length ? `${preview}...` : preview;
}

export default function AuditLogTable({ items, onDrawerOpen }: AuditLogTableProps) {
  if (items.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm">
        <p className="text-gray-500 text-sm">Aucune entrée de journal d'audit ne correspond à ces critères.</p>
      </div>
    );
  }

  return (
    <>
      <div className="hidden lg:block bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Date / Heure
                </th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Action
                </th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Acteur
                </th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Cible
                </th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Détail
                </th>
                <th scope="col" className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {items.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50/50 transition-colors">
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">{formatDateTime(item.created_at)}</td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <ActionBadge action={item.action} />
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                    {item.actor_email || item.actor_user_id || '—'}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                    {item.target_email || item.target_user_id || '—'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500 max-w-xs truncate">
                    {formatDetail(item.detail)}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-right">
                    <button
                      onClick={() => onDrawerOpen(item)}
                      className="text-[#D4AF37] hover:text-[#B8941E] font-medium text-sm"
                    >
                      Détails
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="lg:hidden space-y-4">
        {items.map((item) => (
          <div key={item.id} className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
            <div className="flex items-start justify-between mb-3">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-gray-900 truncate">{formatDateTime(item.created_at)}</p>
                <div className="flex items-center gap-2 mt-1">
                  <ActionBadge action={item.action} />
                </div>
              </div>
              <button
                onClick={() => onDrawerOpen(item)}
                className="text-[#D4AF37] hover:text-[#B8941E] font-medium text-sm shrink-0"
              >
                Détails
              </button>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs text-gray-500 mb-3">
              <div>
                <span className="font-medium">Acteur: </span>
                {item.actor_email || item.actor_user_id || '—'}
              </div>
              <div>
                <span className="font-medium">Cible: </span>
                {item.target_email || item.target_user_id || '—'}
              </div>
            </div>
            <div className="pt-3 border-t border-gray-100">
              <p className="text-xs text-gray-500">
                <span className="font-medium">Détail: </span>
                {formatDetail(item.detail)}
              </p>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}