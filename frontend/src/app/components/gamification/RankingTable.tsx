'use client';

import { GamificationRankingItem } from '@/app/lib/api';

interface RankingTableProps {
  rankings: GamificationRankingItem[];
  loading?: boolean;
}

export default function RankingTable({ rankings, loading = false }: RankingTableProps) {
  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Classement mensuel</h3>
        <p className="text-gray-500 text-sm">Chargement...</p>
      </div>
    );
  }

  if (!rankings || rankings.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Classement mensuel</h3>
        <p className="text-gray-500 text-sm">Aucun classement disponible pour ce mois.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">Classement mensuel</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Rang</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Serveur</th>
              <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Points</th>
              <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Présence</th>
              <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Performance</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {rankings.map((item) => (
              <tr key={item.server_id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${
                    item.rank === 1 ? 'bg-[#D4AF37] text-white' :
                    item.rank === 2 ? 'bg-gray-300 text-gray-700' :
                    item.rank === 3 ? 'bg-amber-200 text-amber-800' :
                    'bg-gray-100 text-gray-600'
                  }`}>
                    {item.rank}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {item.server_name}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-bold text-[#D4AF37]">
                  {item.total_points}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-600">
                  {item.completion_points}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-600">
                  {item.performance_points}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
