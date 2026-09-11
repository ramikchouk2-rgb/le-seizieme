'use client';

import Link from 'next/link';
import { ServerListItem } from '@/app/components/dashboard/types';

interface ServerTableProps {
  servers: ServerListItem[];
  sortBy: string;
  sortOrder: 'asc' | 'desc';
  onSort: (field: string) => void;
}

const BADGE_COLORS: Record<string, string> = {
  AVAILABLE: 'bg-green-50 text-green-700 border-green-200',
  UNAVAILABLE: 'bg-red-50 text-red-700 border-red-200',
  MALE: 'bg-blue-50 text-blue-700 border-blue-200',
  FEMALE: 'bg-pink-50 text-pink-700 border-pink-200',
  HARD_WORKER: 'bg-purple-50 text-purple-700 border-purple-200',
  BALANCED: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  SOFT_WORKER: 'bg-orange-50 text-orange-700 border-orange-200',
};

const LABELS: Record<string, Record<string, string>> = {
  gender: { MALE: 'Homme', FEMALE: 'Femme' },
  worker_type: { HARD_WORKER: 'Profil performant', BALANCED: 'Profil équilibré', SOFT_WORKER: 'Profil souple' },
  availability_status: { AVAILABLE: 'Disponible', UNAVAILABLE: 'Indisponible' },
};

function SortIcon({ field, active, order }: { field: string; active: boolean; order: 'asc' | 'desc' }) {
  if (!active) return <span className="text-gray-300 ml-1">↕</span>;
  return <span className="text-[#D4AF37] ml-1">{order === 'asc' ? '↑' : '↓'}</span>;
}

export default function ServerTable({ servers, sortBy, sortOrder, onSort }: ServerTableProps) {
  if (servers.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm">
        <p className="text-gray-500 text-sm">Aucun serveur ne correspond à ces critères.</p>
      </div>
    );
  }

  const header = (label: string, field: string) => (
    <th
      scope="col"
      className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider cursor-pointer hover:text-[#D4AF37] select-none"
      onClick={() => onSort(field)}
    >
      <div className="flex items-center">
        {label}
        <SortIcon field={field} active={sortBy === field} order={sortOrder} />
      </div>
    </th>
  );

  return (
    <>
      {/* Desktop table */}
      <div className="hidden lg:block bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {header('Serveur', 'first_name')}
                {header('Genre', 'gender')}
                {header('Ville', 'city')}
                {header('Exp.', 'years_experience')}
                {header('Profil', 'worker_type')}
                {header('Compétence', 'main_skill_level')}
                {header('Véhicule', 'has_vehicle')}
                {header('Transport', 'can_transport_coworkers')}
                {header('Dispo.', 'availability_status')}
                {header('Localisation', 'location_verified')}
                {header('Points', 'monthly_points')}
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {servers.map((server) => (
                <tr
                  key={server.id}
                  className="hover:bg-gray-50/50 transition-colors"
                >
                  <td className="px-4 py-3 whitespace-nowrap">
                    <Link
                      href={`/dashboard/servers/${server.id}`}
                      className="flex items-center gap-2"
                    >
                      <div className="w-8 h-8 rounded-full bg-[#D4AF37]/10 flex items-center justify-center text-[#D4AF37] text-xs font-bold">
                        {server.first_name[0]}{server.last_name[0]}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {server.first_name} {server.last_name}
                        </p>
                      </div>
                    </Link>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${BADGE_COLORS[server.gender] || 'bg-gray-50 text-gray-700'}`}>
                      {LABELS.gender[server.gender] || server.gender}
                    </span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">{server.city}</td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">{server.years_experience} ans</td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${BADGE_COLORS[server.worker_type] || 'bg-gray-50 text-gray-700'}`}>
                      {LABELS.worker_type[server.worker_type] || server.worker_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{server.main_skill}</div>
                    <div className="text-xs text-gray-500">Niveau {server.main_skill_level}/10</div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                    {server.vehicle ? (
                      <span className="text-gray-900">{server.vehicle.brand} {server.vehicle.model}</span>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm">
                    {server.vehicle ? (
                      server.vehicle.can_transport_coworkers ? (
                        <span className="text-green-600">Oui</span>
                      ) : (
                        <span className="text-red-600">Non</span>
                      )
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${BADGE_COLORS[server.availability_status] || 'bg-gray-50 text-gray-700'}`}>
                      {LABELS.availability_status[server.availability_status] || server.availability_status}
                    </span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {server.location_verified ? (
                      <span className="inline-flex items-center gap-1 text-xs text-green-600">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        Vérifiée
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-xs text-gray-400">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                        Non vérifiée
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-[#D4AF37]">
                    {server.monthly_points} pts
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm">
                    <Link
                      href={`/dashboard/servers/${server.id}`}
                      className="text-[#D4AF37] hover:text-[#B8941E] font-medium"
                    >
                      Profil
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Mobile cards */}
      <div className="lg:hidden space-y-4">
        {servers.map((server) => (
          <Link
            key={server.id}
            href={`/dashboard/servers/${server.id}`}
            className="block bg-white rounded-xl border border-gray-200 p-4 shadow-sm"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-[#D4AF37]/10 flex items-center justify-center text-[#D4AF37] text-sm font-bold">
                  {server.first_name[0]}{server.last_name[0]}
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-900">
                    {server.first_name} {server.last_name}
                  </p>
                  <p className="text-xs text-gray-500">{server.city} • {server.years_experience} ans</p>
                </div>
              </div>
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${BADGE_COLORS[server.availability_status] || 'bg-gray-50 text-gray-700'}`}>
                {LABELS.availability_status[server.availability_status] || server.availability_status}
              </span>
            </div>

            <div className="flex flex-wrap gap-2 mb-3">
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${BADGE_COLORS[server.gender] || 'bg-gray-50 text-gray-700'}`}>
                {LABELS.gender[server.gender] || server.gender}
              </span>
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${BADGE_COLORS[server.worker_type] || 'bg-gray-50 text-gray-700'}`}>
                {LABELS.worker_type[server.worker_type] || server.worker_type}
              </span>
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border bg-gray-50 text-gray-700">
                {server.main_skill} Nv.{server.main_skill_level}
              </span>
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-gray-100">
              <div className="text-xs text-gray-500">
                {server.vehicle ? (
                  <span>{server.vehicle.brand} {server.vehicle.model} • {server.vehicle.can_transport_coworkers ? 'Transport ✅' : 'Sans transport'}</span>
                ) : (
                  <span>Sans véhicule</span>
                )}
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm font-semibold text-[#D4AF37]">{server.monthly_points} pts</span>
                <span className="text-xs bg-[#D4AF37] text-white px-3 py-1.5 rounded-lg font-medium">
                  Profil
                </span>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </>
  );
}
