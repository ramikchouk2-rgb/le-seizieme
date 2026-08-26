'use client';

import { GamificationBonus } from '@/app/lib/api';

interface BonusPanelProps {
  bonuses: GamificationBonus[];
  loading?: boolean;
}

export default function BonusPanel({ bonuses, loading = false }: BonusPanelProps) {
  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Primes mensuelles</h3>
        <p className="text-gray-500 text-sm">Chargement...</p>
      </div>
    );
  }

  if (!bonuses || bonuses.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Primes mensuelles</h3>
        <p className="text-gray-500 text-sm">Aucune prime attribuée pour ce mois.</p>
      </div>
    );
  }

  const totalBonus = bonuses.reduce((sum, b) => sum + b.bonus_amount, 0);

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">Primes mensuelles</h3>
        <span className="text-sm font-medium text-[#D4AF37]">
          Total: {totalBonus.toFixed(2)} DT
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Serveur</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Rang</th>
              <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Points</th>
              <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Prime</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Règle</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {bonuses.map((bonus) => (
              <tr key={bonus.server_id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {bonus.server_name}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                  {bonus.rank}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-600">
                  {bonus.points}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-bold text-[#D4AF37]">
                  {bonus.bonus_amount.toFixed(2)} DT
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                  {bonus.rule || '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
