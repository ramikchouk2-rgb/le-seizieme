'use client';

import { UserListItem, UserListResponse } from '@/app/lib/types';
import { Spinner } from '@/app/lib/loading';

interface UserStatsProps {
  data: UserListResponse | undefined;
  loading: boolean;
}

const ROLE_BADGE: Record<string, string> = {
  ADMIN: 'bg-purple-50 text-purple-700 border-purple-200',
  MANAGER: 'bg-blue-50 text-blue-700 border-blue-200',
  STAFF: 'bg-gray-50 text-gray-700 border-gray-200',
};

export default function UserStats({ data, loading }: UserStatsProps) {
  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const active = items.filter((u) => u.is_active).length;
  const inactive = items.length - active;
  const admins = items.filter((u) => u.role === 'ADMIN').length;
  const managers = items.filter((u) => u.role === 'MANAGER').length;
  const staff = items.filter((u) => u.role === 'STAFF').length;
  const activeAdmins = items.filter((u) => u.role === 'ADMIN' && u.is_active).length;

  const cards: { label: string; value: number; color: string }[] = [
    { label: 'Total utilisateurs', value: total, color: 'text-gray-900' },
    { label: 'Utilisateurs actifs', value: active, color: 'text-green-600' },
    { label: 'Utilisateurs inactifs', value: inactive, color: 'text-red-600' },
    { label: 'Administrateurs (actifs)', value: activeAdmins, color: 'text-gray-900' },
    { label: 'Managers', value: managers, color: 'text-gray-900' },
    { label: 'Serveurs', value: staff, color: 'text-gray-900' },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-6">
      {cards.map((card) => (
        <div
          key={card.label}
          className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm"
        >
          <p className="text-sm font-medium text-gray-500 mb-1">{card.label}</p>
          <div className={`text-2xl font-bold ${card.color}`}>
            {loading ? <Spinner size="sm" /> : card.value}
          </div>
        </div>
      ))}
    </div>
  );
}
