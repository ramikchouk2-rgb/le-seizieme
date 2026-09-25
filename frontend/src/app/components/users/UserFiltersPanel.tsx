'use client';

import { UserFilters } from '@/app/lib/types';
import { USER_ROLE_OPTIONS } from '@/app/data/users';

interface UserFiltersProps {
  filters: UserFilters;
  onChange: (filters: UserFilters) => void;
  onReset: () => void;
}

export default function UserFiltersPanel({ filters, onChange, onReset }: UserFiltersProps) {
  const update = (key: keyof UserFilters, value: string) => {
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

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="lg:col-span-2">
          <label htmlFor="filter-user-search" className="block text-xs font-medium text-gray-500 mb-1">
            Rechercher
          </label>
          <input
            id="filter-user-search"
            type="search"
            value={filters.search}
            onChange={(e) => update('search', e.target.value)}
            placeholder="Email..."
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
          />
        </div>

        <div>
          <label htmlFor="filter-user-role" className="block text-xs font-medium text-gray-500 mb-1">
            Rôle
          </label>
          <select
            id="filter-user-role"
            value={filters.role}
            onChange={(e) => update('role', e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
          >
            <option value="">Tous les rôles</option>
            {USER_ROLE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="filter-user-active" className="block text-xs font-medium text-gray-500 mb-1">
            Statut
          </label>
          <select
            id="filter-user-active"
            value={filters.is_active}
            onChange={(e) => update('is_active', e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
          >
            <option value="">Tous</option>
            <option value="true">Actif</option>
            <option value="false">Inactif</option>
          </select>
        </div>
      </div>
    </div>
  );
}
