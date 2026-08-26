'use client';

import { GamificationRankingItem } from '@/app/lib/api';

interface TopServerCardProps {
  topServer: GamificationRankingItem | null;
  loading?: boolean;
}

export default function TopServerCard({ topServer, loading = false }: TopServerCardProps) {
  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Serveur du mois</h3>
        <p className="text-gray-500 text-sm">Chargement...</p>
      </div>
    );
  }

  if (!topServer) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Serveur du mois</h3>
        <p className="text-gray-500 text-sm">Aucun classement disponible.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <div className="flex items-center gap-4">
        <div className="w-16 h-16 rounded-full bg-[#D4AF37] flex items-center justify-center text-white text-2xl font-bold">
          {topServer.rank}
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900">{topServer.server_name}</h3>
          <p className="text-sm text-gray-500">Rang {topServer.rank} • {topServer.total_points} points</p>
          <div className="flex gap-4 mt-2">
            <div className="text-xs text-gray-600">
              <span className="font-medium">Présence:</span> {topServer.completion_points}
            </div>
            <div className="text-xs text-gray-600">
              <span className="font-medium">Performance:</span> {topServer.performance_points}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
