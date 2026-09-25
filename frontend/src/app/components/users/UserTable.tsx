'use client';

import Link from 'next/link';
import { UserListItem } from '@/app/lib/types';
import { USER_ROLES } from '@/app/lib/types';

interface UserTableProps {
  users: UserListItem[];
  onDrawerOpen: (user: UserListItem) => void;
}

const ROLE_BADGE: Record<string, string> = {
  ADMIN: 'bg-purple-50 text-purple-700 border-purple-200',
  MANAGER: 'bg-blue-50 text-blue-700 border-blue-200',
  STAFF: 'bg-gray-50 text-gray-700 border-gray-200',
};

function StatusBadge({ active }: { active: boolean }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
        active
          ? 'bg-green-50 text-green-700 border-green-200'
          : 'bg-red-50 text-red-700 border-red-200'
      }`}
    >
      {active ? 'Actif' : 'Inactif'}
    </span>
  );
}

function formatDate(value?: string | null) {
  if (!value) return '—';
  const date = new Date(value.endsWith('Z') ? value : `${value}Z`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString('fr-FR');
}

export default function UserTable({ users, onDrawerOpen }: UserTableProps) {
  if (users.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm">
        <p className="text-gray-500 text-sm">Aucun utilisateur ne correspond à ces critères.</p>
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
                  Email
                </th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Rôle
                </th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Statut
                </th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Créé le
                </th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Mis à jour
                </th>
                <th scope="col" className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {users.map((user) => (
                <tr key={user.id} className="hover:bg-gray-50/50 transition-colors">
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 font-medium">{user.email}</td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
                        ROLE_BADGE[user.role] || 'bg-gray-50 text-gray-700 border-gray-200'
                      }`}
                    >
                      {USER_ROLES[user.role as keyof typeof USER_ROLES] || user.role}
                    </span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <StatusBadge active={user.is_active} />
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">{formatDate(user.created_at)}</td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">{formatDate(user.updated_at)}</td>
                  <td className="px-4 py-3 whitespace-nowrap text-right">
                    <button
                      onClick={() => onDrawerOpen(user)}
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
        {users.map((user) => (
          <div key={user.id} className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
            <div className="flex items-start justify-between mb-3">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-gray-900 truncate">{user.email}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
                      ROLE_BADGE[user.role] || 'bg-gray-50 text-gray-700 border-gray-200'
                    }`}
                  >
                    {USER_ROLES[user.role as keyof typeof USER_ROLES] || user.role}
                  </span>
                  <StatusBadge active={user.is_active} />
                </div>
              </div>
              <button
                onClick={() => onDrawerOpen(user)}
                className="text-[#D4AF37] hover:text-[#B8941E] font-medium text-sm shrink-0"
              >
                Détails
              </button>
            </div>
            <div className="flex items-center justify-between pt-3 border-t border-gray-100">
              <p className="text-xs text-gray-500">Créé le {formatDate(user.created_at)}</p>
              <Link
                href={`/dashboard/users/${user.id}/edit`}
                className="text-xs text-[#D4AF37] hover:text-[#B8941E] font-medium"
              >
                Modifier
              </Link>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
