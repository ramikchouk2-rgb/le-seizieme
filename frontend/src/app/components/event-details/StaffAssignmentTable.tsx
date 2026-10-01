'use client';

import Link from 'next/link';
import { StaffAssignment, ASSIGNMENT_STATUSES } from '@/app/components/dashboard/types';

interface StaffAssignmentTableProps {
  assignments: StaffAssignment[];
  onSelect: (assignment: StaffAssignment) => void;
  sortBy: string;
  sortOrder: 'asc' | 'desc';
  onSort: (field: string) => void;
  roleFilter: string;
  statusFilter: string;
  availabilityFilter: string;
  /**
   * Step 24C-D-4: false when the event venue came from the city reference or the
   * global fallback, in which case distances are rendered as approximate.
   */
  hasExactLocation?: boolean;
}

const STATUS_STYLES: Record<string, string> = {
  PROPOSED: 'bg-blue-50 text-blue-700 border-blue-200',
  CONFIRMED: 'bg-green-50 text-green-700 border-green-200',
  DECLINED: 'bg-red-50 text-red-700 border-red-200',
  CANCELLED: 'bg-gray-50 text-gray-700 border-gray-200',
  COMPLETED: 'bg-purple-50 text-purple-700 border-purple-200',
};

function SortIcon({ field, active, order }: { field: string; active: boolean; order: 'asc' | 'desc' }) {
  if (!active) return <span className="text-gray-300 ml-1">↕</span>;
  return <span className="text-[#D4AF37] ml-1">{order === 'asc' ? '↑' : '↓'}</span>;
}

/**
 * A null distance means the distance is UNKNOWN, not zero. It is rendered as an
 * em dash so an unknown value is never presented as a measured "0.0 km".
 */
function formatDistance(
  distanceKm: number | null | undefined,
  approximate = false,
): string {
  if (distanceKm === null || distanceKm === undefined) return '—';
  // Step 24C-D-4: an approximate venue must never read as a measured distance.
  return `${approximate ? '≈ ' : ''}${distanceKm.toFixed(1)} km`;
}

/**
 * Comparator for the distance column. Known distances sort numerically in the
 * requested direction and unknown ones are always pushed last, so a null is
 * never ordered as if it were 0 km.
 */
function compareDistance(
  a: number | null | undefined,
  b: number | null | undefined,
  sortOrder: 'asc' | 'desc'
): number {
  const aKnown = a !== null && a !== undefined;
  const bKnown = b !== null && b !== undefined;
  if (aKnown !== bKnown) return aKnown ? -1 : 1;
  if (!aKnown) return 0;
  return sortOrder === 'asc' ? (a as number) - (b as number) : (b as number) - (a as number);
}

export default function StaffAssignmentTable({
  assignments,
  onSelect,
  sortBy,
  sortOrder,
  onSort,
  roleFilter,
  statusFilter,
  availabilityFilter,
  hasExactLocation = true,
}: StaffAssignmentTableProps) {
  let filtered = [...assignments];

  if (roleFilter) {
    filtered = filtered.filter((a) => a.role === roleFilter);
  }

  if (statusFilter) {
    filtered = filtered.filter((a) => a.status === statusFilter);
  }

  if (availabilityFilter === 'available') {
    filtered = filtered.filter((a) => a.availability_status === 'AVAILABLE');
  }

  filtered.sort((a, b) => {
    // The distance column is handled separately: an unknown distance must not
    // be collapsed to 0 and compared as a real value.
    if (sortBy === 'distance_km') {
      const ordered = compareDistance(a.distance_km, b.distance_km, sortOrder);
      if (ordered !== 0) return ordered;
      return a.last_name.localeCompare(b.last_name);
    }

    let aVal: string | number = '';
    let bVal: string | number = '';

    switch (sortBy) {
      case 'score':
        aVal = a.score ?? 0;
        bVal = b.score ?? 0;
        break;
      case 'years_experience':
        aVal = a.years_experience;
        bVal = b.years_experience;
        break;
      case 'skill_level':
        aVal = a.skill_level;
        bVal = b.skill_level;
        break;
      case 'first_name':
        aVal = a.first_name;
        bVal = b.first_name;
        break;
      case 'last_name':
        aVal = a.last_name;
        bVal = b.last_name;
        break;
      case 'role':
        aVal = a.role;
        bVal = b.role;
        break;
      case 'status':
        aVal = a.status;
        bVal = b.status;
        break;
      default:
        aVal = a.score ?? 0;
        bVal = b.score ?? 0;
    }

    if (typeof aVal === 'string' && typeof bVal === 'string') {
      return sortOrder === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    }

    return sortOrder === 'asc'
      ? (aVal as number) - (bVal as number)
      : (bVal as number) - (aVal as number);
  });

  if (filtered.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm">
        <p className="text-gray-500 text-sm">Aucun serveur affecté.</p>
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
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {header('Serveur', 'last_name')}
              {header('Rôle', 'role')}
              {header('Score', 'score')}
              {header('Distance', 'distance_km')}
              {header('Exp.', 'years_experience')}
              {header('Niveau', 'skill_level')}
              {header('Dispo.', 'availability_status')}
              {header('Statut', 'status')}
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {filtered.map((assignment) => (
              <tr
                key={assignment.id}
                className="hover:bg-gray-50/50 cursor-pointer transition-colors"
                onClick={() => onSelect(assignment)}
              >
                <td className="px-4 py-3 whitespace-nowrap">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full bg-[#D4AF37]/10 flex items-center justify-center text-[#D4AF37] text-xs font-bold">
                      {assignment.first_name[0]}{assignment.last_name[0]}
                    </div>
                    <div>
                      <Link
                        href={`/dashboard/servers/${assignment.server_id}`}
                        className="text-sm font-medium text-gray-900 hover:text-[#D4AF37] transition-colors"
                      >
                        {assignment.first_name} {assignment.last_name}
                      </Link>
                      <p className="text-xs text-gray-500">{assignment.city}</p>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                  {assignment.role}
                  {assignment.required_gender && (
                    <span className="text-xs text-gray-500 ml-1">
                      ({assignment.required_gender === 'MALE' ? 'H' : 'F'})
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <div className="flex items-center gap-2">
                    <div className="w-16 bg-gray-200 rounded-full h-1.5">
                      <div
                        className="bg-[#D4AF37] h-1.5 rounded-full"
                        style={{ width: `${assignment.score}%` }}
                      />
                    </div>
                    <span className="text-sm font-medium text-gray-900">{(assignment.score ?? 0).toFixed(1)}</span>
                  </div>
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                  {formatDistance(assignment.distance_km, !hasExactLocation)}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                  {assignment.years_experience} ans
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <div className="flex items-center gap-2">
                    <div className="w-12 bg-gray-200 rounded-full h-1.5">
                      <div
                        className="bg-[#D4AF37] h-1.5 rounded-full"
                        style={{ width: `${assignment.skill_level * 10}%` }}
                      />
                    </div>
                    <span className="text-sm text-gray-700">{assignment.skill_level}/10</span>
                  </div>
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
                    assignment.availability_status === 'AVAILABLE' ? 'bg-green-50 text-green-700 border-green-200' : 'bg-red-50 text-red-700 border-red-200'
                  }`} title={assignment.conflict_reason || undefined}>
                    {assignment.availability_status === 'AVAILABLE' ? 'Disponible' : 'Indisponible'}
                  </span>
                  {assignment.conflict && (
                    <span className="mt-1 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-orange-50 text-orange-700 border border-orange-200" title={assignment.conflict_reason || undefined}>
                      Conflit
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_STYLES[assignment.status] || 'bg-gray-50 text-gray-700'}`}>
                    {ASSIGNMENT_STATUSES[assignment.status as keyof typeof ASSIGNMENT_STATUSES] || assignment.status}
                  </span>
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm">
                  <button
                    onClick={(e) => { e.stopPropagation(); onSelect(assignment); }}
                    className="text-[#D4AF37] hover:text-[#B8941E] font-medium"
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
  );
}
