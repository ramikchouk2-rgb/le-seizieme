'use client';

import Link from 'next/link';
import { GamificationBonus, GamificationRanking } from '@/app/lib/api';
import { Spinner } from '@/app/lib/loading';

interface GamificationSummaryProps {
  ranking?: GamificationRanking | null;
  bonuses?: GamificationBonus[] | null;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
}

export default function GamificationSummary({
  ranking,
  bonuses,
  loading = false,
  error = null,
  onRetry,
}: GamificationSummaryProps) {
  const totalBonus = (bonuses || []).reduce((sum, bonus) => sum + bonus.bonus_amount, 0);

  return (
    <section className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
      <div className="flex items-start justify-between gap-4 mb-5">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Gamification</h3>
          <p className="text-sm text-gray-500 mt-1">Performance du mois</p>
        </div>
        <Link href="/dashboard/gamification" className="text-xs font-medium text-[#8A6D1D] hover:text-[#D4AF37]">
          Voir le classement
        </Link>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-6">
          <Spinner size="sm" />
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 flex items-center justify-between gap-3">
          <span>Impossible de charger la gamification.</span>
          {onRetry && (
            <button type="button" onClick={onRetry} className="underline font-medium whitespace-nowrap">
              Réessayer
            </button>
          )}
        </div>
      )}

      {!loading && !error && !ranking && (
        <p className="text-sm text-gray-500">Aucun classement disponible pour ce mois.</p>
      )}

      {!loading && !error && ranking && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg bg-gray-50 border border-gray-200 p-3">
              <p className="text-xs text-gray-500">Points distribués</p>
              <p className="text-xl font-bold text-gray-900 mt-1">{ranking.total_points}</p>
            </div>
            <div className="rounded-lg bg-gray-50 border border-gray-200 p-3">
              <p className="text-xs text-gray-500">Serveurs classés</p>
              <p className="text-xl font-bold text-gray-900 mt-1">{ranking.total_servers}</p>
            </div>
          </div>

          <div className="rounded-lg bg-[#D4AF37]/10 border border-[#D4AF37]/20 p-3">
            <p className="text-xs text-gray-500">Top serveur</p>
            <p className="text-sm font-semibold text-gray-900 mt-1 truncate">
              {ranking.top_server || 'Aucun leader'}
            </p>
            <p className="text-xs text-[#8A6D1D] mt-1">
              {bonuses?.length ? `${bonuses.length} prime${bonuses.length > 1 ? 's' : ''} • ${totalBonus.toFixed(2)} DT` : 'Aucune prime ce mois'}
            </p>
          </div>
        </div>
      )}
    </section>
  );
}
