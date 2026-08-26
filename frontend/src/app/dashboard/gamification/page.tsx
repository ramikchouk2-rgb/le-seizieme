'use client';

import { useState, useCallback, useEffect } from 'react';
import Header from '@/app/components/dashboard/Header';
import RankingTable from '@/app/components/gamification/RankingTable';
import TopServerCard from '@/app/components/gamification/TopServerCard';
import BonusPanel from '@/app/components/gamification/BonusPanel';
import ServerPointsDrawer from '@/app/components/gamification/ServerPointsDrawer';
import CalculateRankingDialog from '@/app/components/gamification/CalculateRankingDialog';
import { useMonthlyRankings, useMonthlyBonuses, useCalculateRankings, useServerPoints } from '@/app/lib/hooks';
import { Spinner } from '@/app/lib/loading';
import { useAnnouncer } from '@/app/components/ui/Announcer';

const MONTH_NAMES = [
  'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
];

export default function GamificationPage() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedServerId, setSelectedServerId] = useState<string | null>(null);
  const [calculateDialogOpen, setCalculateDialogOpen] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const { announceSuccess, announceError } = useAnnouncer();

  const { data: rankings, isLoading: rankingsLoading, error: rankingsError, refetch: refetchRankings } = useMonthlyRankings(year, month);
  const { data: bonuses, isLoading: bonusesLoading, error: bonusesError, refetch: refetchBonuses } = useMonthlyBonuses(year, month);
  const calculateMutation = useCalculateRankings();
  const { data: selectedServer, isLoading: serverPointsLoading } = useServerPoints(selectedServerId || '');

  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => setSuccess(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [success]);

  const handleCalculate = useCallback(async () => {
    try {
      await calculateMutation.mutateAsync({ year, month });
      setSuccess('Classement calculé avec succès.');
      setCalculateDialogOpen(false);
      announceSuccess('Classement mensuel calculé avec succès.');
    } catch {
      announceError('Opération impossible. Veuillez réessayer.');
    }
  }, [calculateMutation, year, month, announceSuccess, announceError]);

  const handleViewServerPoints = useCallback((serverId: string) => {
    setDrawerOpen(true);
    setSelectedServerId(serverId);
  }, []);

  const error = rankingsError?.message || bonusesError?.message || null;

  const totalPoints = rankings?.total_points || 0;
  const totalServers = rankings?.total_servers || 0;
  const topServer = rankings?.rankings?.[0];

  const years = Array.from({ length: 5 }, (_, i) => now.getFullYear() - 2 + i);

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <Header title="Gamification & Performance" />

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700 flex items-center justify-between">
          <span>{error}</span>
          <div className="flex gap-2">
            <button onClick={() => { refetchRankings(); refetchBonuses(); }} className="underline font-medium">
              Réessayer
            </button>
          </div>
        </div>
      )}

      {success && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-sm text-green-700" aria-live="polite">
          {success}
        </div>
      )}

      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="flex gap-3">
          <select
            value={month}
            onChange={(e) => setMonth(Number(e.target.value))}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
          >
            {MONTH_NAMES.map((name, idx) => (
              <option key={idx + 1} value={idx + 1}>{name}</option>
            ))}
          </select>
          <select
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
          >
            {years.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>
        <button
          onClick={() => setCalculateDialogOpen(true)}
          disabled={calculateMutation.isPending}
          className="px-4 py-2 bg-[#D4AF37] text-white text-sm font-medium rounded-lg hover:bg-[#B8941E] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {calculateMutation.isPending ? 'Calcul...' : 'Calculer le classement'}
        </button>
      </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Total points</p>
            <div className="text-2xl font-bold text-gray-900 mt-1">
              {rankingsLoading ? <Spinner size="sm" /> : totalPoints}
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Serveurs classés</p>
            <div className="text-2xl font-bold text-gray-900 mt-1">
              {rankingsLoading ? <Spinner size="sm" /> : totalServers}
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Leader</p>
            <div className="text-2xl font-bold text-gray-900 mt-1 truncate">
              {rankingsLoading ? <Spinner size="sm" /> : (topServer?.server_name || '-')}
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Bonus total</p>
            <div className="text-2xl font-bold text-[#D4AF37] mt-1">
              {bonusesLoading ? <Spinner size="sm" /> : `${(bonuses || []).reduce((sum, b) => sum + b.bonus_amount, 0).toFixed(2)} DT`}
            </div>
          </div>
        </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <RankingTable
            rankings={rankings?.rankings || []}
            loading={rankingsLoading}
          />
        </div>
        <div className="space-y-6">
          <TopServerCard
            topServer={topServer || null}
            loading={rankingsLoading}
          />
          <BonusPanel
            bonuses={bonuses || []}
            loading={bonusesLoading}
          />
        </div>
      </div>

      <CalculateRankingDialog
        open={calculateDialogOpen}
        onClose={() => setCalculateDialogOpen(false)}
        onConfirm={handleCalculate}
        loading={calculateMutation.isPending}
        year={year}
        month={month}
      />

      <ServerPointsDrawer
        open={drawerOpen}
        onClose={() => { setDrawerOpen(false); setSelectedServerId(null); }}
        server={selectedServer || null}
        loading={serverPointsLoading}
      />
    </div>
  );
}
