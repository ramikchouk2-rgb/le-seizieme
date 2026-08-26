'use client';

import { ServerFilters } from '@/app/components/dashboard/types';
import { ALL_CITIES, ALL_SKILLS } from '@/app/data/servers';

interface FilterPanelProps {
  filters: ServerFilters;
  onChange: (filters: ServerFilters) => void;
  onReset: () => void;
}

export default function FilterPanel({ filters, onChange, onReset }: FilterPanelProps) {
  const update = (key: keyof ServerFilters, value: string) => {
    onChange({ ...filters, [key]: value });
  };

  const hasActiveFilters = Object.values(filters).some((v) => v !== '' && v !== 'last_name' && v !== 'asc');

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
          <label htmlFor="filter-search" className="block text-xs font-medium text-gray-500 mb-1">Rechercher</label>
          <input
            id="filter-search"
            type="text"
            value={filters.search}
            onChange={(e) => update('search', e.target.value)}
            placeholder="Nom, ville, email, compétence..."
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
          />
        </div>

        <div>
          <label htmlFor="filter-city" className="block text-xs font-medium text-gray-500 mb-1">Ville</label>
          <select
            id="filter-city"
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
          <label htmlFor="filter-gender" className="block text-xs font-medium text-gray-500 mb-1">Genre</label>
          <select
            id="filter-gender"
            value={filters.gender}
            onChange={(e) => update('gender', e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
          >
            <option value="">Tous</option>
            <option value="MALE">Homme</option>
            <option value="FEMALE">Femme</option>
          </select>
        </div>

        <div>
          <label htmlFor="filter-availability" className="block text-xs font-medium text-gray-500 mb-1">Disponibilité</label>
          <select
            id="filter-availability"
            value={filters.availability}
            onChange={(e) => update('availability', e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
          >
            <option value="">Tous</option>
            <option value="AVAILABLE">Disponible</option>
            <option value="UNAVAILABLE">Indisponible</option>
          </select>
        </div>

        <div>
          <label htmlFor="filter-worker-type" className="block text-xs font-medium text-gray-500 mb-1">Type de profil</label>
          <select
            id="filter-worker-type"
            value={filters.worker_type}
            onChange={(e) => update('worker_type', e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
          >
            <option value="">Tous</option>
            <option value="HARD_WORKER">Profil performant</option>
            <option value="BALANCED">Profil équilibré</option>
            <option value="SOFT_WORKER">Profil souple</option>
          </select>
        </div>

        <div>
          <label htmlFor="filter-vehicle" className="block text-xs font-medium text-gray-500 mb-1">Véhicule</label>
          <select
            id="filter-vehicle"
            value={filters.has_vehicle}
            onChange={(e) => update('has_vehicle', e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
          >
            <option value="">Tous</option>
            <option value="yes">Avec véhicule</option>
            <option value="no">Sans véhicule</option>
          </select>
        </div>

        <div>
          <label htmlFor="filter-transport" className="block text-xs font-medium text-gray-500 mb-1">Transport collègues</label>
          <select
            id="filter-transport"
            value={filters.can_transport}
            onChange={(e) => update('can_transport', e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
          >
            <option value="">Tous</option>
            <option value="yes">Peut transporter</option>
            <option value="no">Ne peut pas transporter</option>
          </select>
        </div>

        <div>
          <label htmlFor="filter-location" className="block text-xs font-medium text-gray-500 mb-1">Localisation</label>
          <select
            id="filter-location"
            value={filters.location_verified}
            onChange={(e) => update('location_verified', e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
          >
            <option value="">Tous</option>
            <option value="verified">Vérifiée</option>
            <option value="not_verified">Non vérifiée</option>
          </select>
        </div>

        <div>
          <label htmlFor="filter-experience" className="block text-xs font-medium text-gray-500 mb-1">Expérience</label>
          <select
            id="filter-experience"
            value={filters.experience_range}
            onChange={(e) => update('experience_range', e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
          >
            <option value="">Toutes</option>
            <option value="0-2">0 – 2 ans</option>
            <option value="3-5">3 – 5 ans</option>
            <option value="6-10">6 – 10 ans</option>
            <option value="10-">10+ ans</option>
          </select>
        </div>

        <div>
          <label htmlFor="filter-skill" className="block text-xs font-medium text-gray-500 mb-1">Compétence</label>
          <select
            id="filter-skill"
            value={filters.skill}
            onChange={(e) => update('skill', e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
          >
            <option value="">Toutes</option>
            {ALL_SKILLS.map((skill) => (
              <option key={skill} value={skill}>{skill}</option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
