'use client';

import type { EventFilters as EventFiltersType } from '@/app/components/dashboard/types';
import { ALL_CITIES, EVENT_STATUSES, EVENT_PRIORITIES, EVENT_DATE_RANGES } from '@/app/data/events';

interface EventFiltersProps {
  filters: EventFiltersType;
  onChange: (filters: EventFiltersType) => void;
  onReset: () => void;
  resultCount: number;
}

export default function EventFiltersComponent({ filters, onChange, onReset, resultCount }: EventFiltersProps) {
  const update = (key: keyof EventFiltersType, value: string) => {
    onChange({ ...filters, [key]: value });
  };

  const hasActiveFilters = Object.values(filters).some((v) => v !== '' && v !== 'start_datetime' && v !== 'asc');

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">Filtres</h3>
          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
            {resultCount} résultat{resultCount !== 1 ? 's' : ''}
          </span>
        </div>
        {hasActiveFilters && (
          <button
            onClick={onReset}
            className="text-xs text-[#D4AF37] hover:text-[#B8941E] font-medium"
          >
            Réinitialiser
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <label htmlFor="event-filter-search" className="block text-xs font-medium text-gray-500 mb-1">Rechercher</label>
          <input
            id="event-filter-search"
            type="text"
            value={filters.search}
            onChange={(e) => update('search', e.target.value)}
            placeholder="Nom de l'événement, ville..."
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
          />
        </div>

        <div>
          <label htmlFor="event-filter-city" className="block text-xs font-medium text-gray-500 mb-1">Ville</label>
          <select
            id="event-filter-city"
            value={filters.city}
            onChange={(e) => update('city', e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
          >
            <option value="">Toutes les villes</option>
            {ALL_CITIES.map((city) => (
              <option key={city} value={city}>{city}</option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="event-filter-status" className="block text-xs font-medium text-gray-500 mb-1">Statut</label>
          <select
            id="event-filter-status"
            value={filters.status}
            onChange={(e) => update('status', e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
          >
            <option value="">Tous</option>
            <option value="PLANNED">Planifié</option>
            <option value="CONFIRMED">Confirmé</option>
            <option value="IN_PROGRESS">En cours</option>
            <option value="COMPLETED">Terminé</option>
            <option value="CANCELLED">Annulé</option>
          </select>
        </div>

        <div>
          <label htmlFor="event-filter-priority" className="block text-xs font-medium text-gray-500 mb-1">Priorité</label>
          <select
            id="event-filter-priority"
            value={filters.priority}
            onChange={(e) => update('priority', e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
          >
            <option value="">Toutes</option>
            <option value="NORMAL">Normal</option>
            <option value="HIGH">Haute</option>
            <option value="CRITICAL">Critique</option>
          </select>
        </div>

        <div>
          <label htmlFor="event-filter-type" className="block text-xs font-medium text-gray-500 mb-1">Type</label>
          <select
            id="event-filter-type"
            value={filters.urgent}
            onChange={(e) => update('urgent', e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
          >
            <option value="">Tous</option>
            <option value="urgent">Urgents</option>
            <option value="normal">Normaux</option>
          </select>
        </div>

        <div>
          <label htmlFor="event-filter-staffing" className="block text-xs font-medium text-gray-500 mb-1">Staffing</label>
          <select
            id="event-filter-staffing"
            value={filters.staffing}
            onChange={(e) => update('staffing', e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
          >
            <option value="">Tous</option>
            <option value="complete">Complet</option>
            <option value="incomplete">Incomplet</option>
          </select>
        </div>

        <div>
          <label htmlFor="event-filter-date" className="block text-xs font-medium text-gray-500 mb-1">Date</label>
          <select
            id="event-filter-date"
            value={filters.dateRange}
            onChange={(e) => update('dateRange', e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
          >
            <option value="">Tous</option>
            <option value="UPCOMING">À venir</option>
            <option value="TODAY">Aujourd'hui</option>
            <option value="PAST">Passés</option>
          </select>
        </div>
      </div>
    </div>
  );
}
