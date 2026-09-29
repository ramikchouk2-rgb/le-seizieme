'use client';

import { AuditLogFilters } from '@/app/lib/types';
import { AUDIT_LOG_ACTION_OPTIONS } from '@/app/lib/types';

interface AuditLogFiltersPanelProps {
  filters: AuditLogFilters;
  onChange: (filters: AuditLogFilters) => void;
  onReset: () => void;
}

export default function AuditLogFiltersPanel({ filters, onChange, onReset }: AuditLogFiltersPanelProps) {
  const update = (key: keyof AuditLogFilters, value: string) => {
    onChange({ ...filters, [key]: value });
  };

  const hasActiveFilters = Object.values(filters).some((v) => v !== '');

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm mb-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">Filtres</h3>
        {hasActiveFilters && (
          <button
            onClick={onReset}
            className="text-xs text-[#D4AF37] hover:text-[#B8941E] font-medium"
          >
            Réinitialiser
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="lg:col-span-2">
          <label htmlFor="filter-audit-action" className="block text-xs font-medium text-gray-500 mb-1">
            Action
          </label>
          <select
            id="filter-audit-action"
            value={filters.action}
            onChange={(e) => update('action', e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
          >
            <option value="">Toutes les actions</option>
            {AUDIT_LOG_ACTION_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="filter-audit-actor" className="block text-xs font-medium text-gray-500 mb-1">
            Acteur (ID)
          </label>
          <input
            id="filter-audit-actor"
            type="text"
            value={filters.actor_user_id}
            onChange={(e) => update('actor_user_id', e.target.value)}
            placeholder="ID utilisateur..."
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
          />
        </div>

        <div>
          <label htmlFor="filter-audit-target" className="block text-xs font-medium text-gray-500 mb-1">
            Cible (ID)
          </label>
          <input
            id="filter-audit-target"
            type="text"
            value={filters.target_user_id}
            onChange={(e) => update('target_user_id', e.target.value)}
            placeholder="ID utilisateur..."
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
          />
        </div>

        <div>
          <label htmlFor="filter-audit-after" className="block text-xs font-medium text-gray-500 mb-1">
            Après le
          </label>
          <input
            id="filter-audit-after"
            type="datetime-local"
            value={filters.created_after}
            onChange={(e) => update('created_after', e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
          />
        </div>

        <div>
          <label htmlFor="filter-audit-before" className="block text-xs font-medium text-gray-500 mb-1">
            Avant le
          </label>
          <input
            id="filter-audit-before"
            type="datetime-local"
            value={filters.created_before}
            onChange={(e) => update('created_before', e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
          />
        </div>
      </div>
    </div>
  );
}