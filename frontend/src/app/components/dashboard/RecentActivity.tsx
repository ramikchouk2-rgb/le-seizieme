'use client';

import { ActivityItem } from '@/app/lib/api';

interface RecentActivityProps {
  activities: ActivityItem[];
  loading?: boolean;
}

export default function RecentActivity({ activities, loading = false }: RecentActivityProps) {
  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Activité récente</h3>
        <p className="text-gray-500 text-sm">Chargement...</p>
      </div>
    );
  }

  if (!activities || activities.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Activité récente</h3>
        <p className="text-gray-500 text-sm">Aucune activité récente.</p>
      </div>
    );
  }

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'staff_assigned':
        return '👥';
      case 'transport_created':
        return '🚗';
      case 'urgent_offer':
        return '⚡';
      case 'points_awarded':
        return '🏆';
      case 'ranking_calculated':
        return '📊';
      case 'event_created':
        return '📅';
      default:
        return '📋';
    }
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return "À l'instant";
    if (minutes < 60) return `Il y a ${minutes} min`;
    if (hours < 24) return `Il y a ${hours} h`;
    if (days < 7) return `Il y a ${days} jour{s}`;
    return date.toLocaleDateString('fr-FR');
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Activité récente</h3>
      <div className="space-y-4">
        {activities.map((activity) => (
          <div key={activity.id} className="flex items-start gap-3">
            <div className="text-xl mt-0.5">{getActivityIcon(activity.type)}</div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-700">{activity.message}</p>
              <p className="text-xs text-gray-400 mt-0.5">{formatTime(activity.timestamp)}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
