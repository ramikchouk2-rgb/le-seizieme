'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import type { EventOperationsResponse, UrgentStatus } from '@/app/lib/api';
import OperationalKpis from '@/app/components/dashboard/OperationalKpis';
import RequiredActions from '@/app/components/dashboard/RequiredActions';
import GamificationSummary from '@/app/components/dashboard/GamificationSummary';
import UpcomingEvents from '@/app/components/dashboard/UpcomingEvents';
import UrgentEvents from '@/app/components/dashboard/UrgentEvents';
import QuickActions from '@/app/components/dashboard/QuickActions';
import RecentActivity from '@/app/components/dashboard/RecentActivity';
import EventSelectorDialog from '@/app/components/dashboard/EventSelectorDialog';
import { useEventOperationsBatch, useUrgentStatusBatch } from '@/app/lib/operational-hooks';
import { useEventStats, useUpcomingEvents, useUrgentEvents, useRecentActivity, useServerStats, useMonthlyRankings, useMonthlyBonuses } from '@/app/lib/hooks';

export default function DashboardPage() {
  const router = useRouter();
  const [staffSelectorOpen, setStaffSelectorOpen] = useState(false);
  const [transportSelectorOpen, setTransportSelectorOpen] = useState(false);
  const [urgentSelectorOpen, setUrgentSelectorOpen] = useState(false);
  const [now, setNow] = useState(() => new Date());

  const { data: eventStats, isLoading: eventStatsLoading, error: eventStatsError, refetch: refetchEventStats } = useEventStats();
  const { data: upcomingEvents, isLoading: upcomingLoading, error: upcomingError, refetch: refetchUpcomingEvents } = useUpcomingEvents(5);
  const { data: urgentEventsData, isLoading: urgentLoading, error: urgentError, refetch: refetchUrgentEvents } = useUrgentEvents(5);
  const { data: activities, isLoading: activitiesLoading, error: activitiesError, refetch: refetchActivities } = useRecentActivity(10);
  const { data: serverStats, isLoading: serverStatsLoading, error: serverStatsError, refetch: refetchServerStats } = useServerStats();

  const upcomingEventIds = useMemo(() => (upcomingEvents?.items ?? []).map((event) => event.id), [upcomingEvents]);
  const urgentEventIds = useMemo(() => (urgentEventsData?.items ?? []).map((event) => event.id), [urgentEventsData]);
  const operationQueries = useEventOperationsBatch(upcomingEventIds);
  const urgentStatusQueries = useUrgentStatusBatch(urgentEventIds);

  const operations = operationQueries
    .map((query) => query.data)
    .filter((operation): operation is EventOperationsResponse => Boolean(operation));
  const urgentStatuses = urgentStatusQueries
    .map((query) => query.data)
    .filter((status): status is UrgentStatus => Boolean(status));

  const { data: ranking, isLoading: rankingLoading, error: rankingError, refetch: refetchRanking } = useMonthlyRankings(now.getFullYear(), now.getMonth() + 1);
  const { data: bonuses, isLoading: bonusesLoading, error: bonusesError, refetch: refetchBonuses } = useMonthlyBonuses(now.getFullYear(), now.getMonth() + 1);

  useEffect(() => {
    const interval = setInterval(() => setNow(new Date()), 30000);
    return () => clearInterval(interval);
  }, []);

  const loading =
    eventStatsLoading ||
    upcomingLoading ||
    urgentLoading ||
    activitiesLoading ||
    serverStatsLoading ||
    operationQueries.some((query) => query.isLoading) ||
    urgentStatusQueries.some((query) => query.isLoading) ||
    rankingLoading ||
    bonusesLoading;

  const error =
    eventStatsError?.message ||
    upcomingError?.message ||
    urgentError?.message ||
    activitiesError?.message ||
    serverStatsError?.message ||
    operationQueries.find((query) => query.error)?.error?.message ||
    urgentStatusQueries.find((query) => query.error)?.error?.message ||
    rankingError?.message ||
    bonusesError?.message ||
    null;

  const retryAll = () => {
    refetchEventStats();
    refetchUpcomingEvents();
    refetchUrgentEvents();
    refetchActivities();
    refetchServerStats();
    operationQueries.forEach((query) => query.refetch());
    urgentStatusQueries.forEach((query) => query.refetch());
    refetchRanking();
    refetchBonuses();
  };

  const operationalKpis = {
    upcomingEvents: eventStats?.upcoming_events ?? upcomingEvents?.total ?? 0,
    urgentEvents: eventStats?.urgent_events ?? urgentEventsData?.total ?? 0,
    missingPositions: eventStats?.missing_positions ?? operations.reduce((sum, operation) => sum + operation.staffing_summary.missing, 0),
    availableServers: serverStats?.available ?? 0,
    pendingOffers: urgentStatuses.reduce((sum, status) => sum + status.pending_count, 0),
    confirmedAssignments: operations.reduce((sum, operation) => sum + operation.staffing_summary.confirmed, 0),
    transportIssues: operations.reduce((sum, operation) => sum + operation.transport.unassigned_passengers, 0),
  };

  const handleGenerateStaff = (event: { id: string }) => {
    setStaffSelectorOpen(false);
    router.push(`/dashboard/events/${event.id}`);
  };

  const handleRecommendTransport = (event: { id: string }) => {
    setTransportSelectorOpen(false);
    router.push(`/dashboard/events/${event.id}`);
  };

  const handleManageUrgent = (event: { id: string }) => {
    setUrgentSelectorOpen(false);
    router.push(`/dashboard/events/${event.id}`);
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Bonjour 👋</h1>
        <p className="text-gray-600 mt-2">Voici l'état actuel de votre équipe et de vos événements.</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={retryAll} className="underline font-medium">
            Réessayer
          </button>
        </div>
      )}

      <OperationalKpis {...operationalKpis} loading={loading} />

      <QuickActions
        actions={[
          { label: 'Créer un événement', icon: '➕', description: 'Nouvel événement', variant: 'primary', href: '/dashboard/events/new' },
          { label: 'Générer une équipe', icon: '👥', description: 'Staffing', variant: 'secondary', onClick: () => setStaffSelectorOpen(true) },
          { label: 'Organiser le transport', icon: '🚗', description: 'Trajets', variant: 'secondary', onClick: () => setTransportSelectorOpen(true) },
          { label: 'Voir les urgences', icon: '⚡', description: 'Offres urgentes', variant: 'secondary', onClick: () => setUrgentSelectorOpen(true) },
          { label: 'Gamification', icon: '🏆', description: 'Classement', variant: 'secondary', href: '/dashboard/gamification' },
        ]}
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RequiredActions
          events={upcomingEvents?.items ?? []}
          operations={operations}
          urgentStatuses={urgentStatuses}
          error={error}
          onRetry={retryAll}
          now={now}
        />
        <GamificationSummary
          ranking={ranking ?? null}
          bonuses={bonuses ?? null}
          loading={rankingLoading || bonusesLoading}
          error={rankingError?.message || bonusesError?.message || null}
          onRetry={() => {
            refetchRanking();
            refetchBonuses();
          }}
        />
      </div>

      <UpcomingEvents events={upcomingEvents?.items ?? []} loading={upcomingLoading} />

      <UrgentEvents events={urgentEventsData?.items ?? []} loading={urgentLoading} />

      <RecentActivity activities={activities ?? []} loading={activitiesLoading} />

      <EventSelectorDialog
        open={staffSelectorOpen}
        onClose={() => setStaffSelectorOpen(false)}
        onSelect={handleGenerateStaff}
        title="Générer une équipe — Sélectionner un événement"
      />
      <EventSelectorDialog
        open={transportSelectorOpen}
        onClose={() => setTransportSelectorOpen(false)}
        onSelect={handleRecommendTransport}
        title="Recommander le transport — Sélectionner un événement"
      />
      <EventSelectorDialog
        open={urgentSelectorOpen}
        onClose={() => setUrgentSelectorOpen(false)}
        onSelect={handleManageUrgent}
        title="Gérer les urgences — Sélectionner un événement"
      />
    </div>
  );
}
