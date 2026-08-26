'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import StatCard from '@/app/components/dashboard/StatCard';
import UpcomingEvents from '@/app/components/dashboard/UpcomingEvents';
import StaffingAlert from '@/app/components/dashboard/StaffingAlert';
import TopServers from '@/app/components/dashboard/TopServers';
import UrgentEvents from '@/app/components/dashboard/UrgentEvents';
import QuickActions from '@/app/components/dashboard/QuickActions';
import RecentActivity from '@/app/components/dashboard/RecentActivity';
import EventSelectorDialog from '@/app/components/dashboard/EventSelectorDialog';
import { useEventStats, useUpcomingEvents, useUrgentEvents, useTopServers, useRecentActivity, useServerStats } from '@/app/lib/hooks';
import { Spinner } from '@/app/lib/loading';

export default function DashboardPage() {
  const router = useRouter();
  const [staffSelectorOpen, setStaffSelectorOpen] = useState(false);
  const [transportSelectorOpen, setTransportSelectorOpen] = useState(false);
  const [urgentSelectorOpen, setUrgentSelectorOpen] = useState(false);

  const { data: eventStats, isLoading: eventStatsLoading, error: eventStatsError, refetch: refetchEventStats } = useEventStats();
  const { data: upcomingEvents, isLoading: upcomingLoading, error: upcomingError } = useUpcomingEvents(5);
  const { data: urgentEvents, isLoading: urgentLoading, error: urgentError } = useUrgentEvents(5);
  const { data: topServers, isLoading: topServersLoading, error: topServersError } = useTopServers(5);
  const { data: activities, isLoading: activitiesLoading, error: activitiesError } = useRecentActivity(10);
  const { data: serverStats, isLoading: serverStatsLoading, error: serverStatsError } = useServerStats();

  const loading = eventStatsLoading || upcomingLoading || urgentLoading || topServersLoading || activitiesLoading || serverStatsLoading;
  const error = eventStatsError?.message || upcomingError?.message || urgentError?.message || topServersError?.message || activitiesError?.message || serverStatsError?.message || null;

  const totalRequired = upcomingEvents?.items?.[0]?.staffing?.requested ?? 0;
  const totalAssigned = upcomingEvents?.items?.[0]?.staffing?.selected ?? 0;
  const remaining = totalRequired - totalAssigned;

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
      {/* Welcome Section */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Bonjour 👋</h1>
        <p className="text-gray-600 mt-2">Voici l'état actuel de votre équipe et de vos événements.</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => {
            refetchEventStats();
          }} className="underline font-medium">
            Réessayer
          </button>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total serveurs"
          value={serverStats?.total ?? 0}
          subtitle="Inscrits dans le système"
          icon="👥"
          loading={serverStatsLoading}
        />
        <StatCard
          title="Serveurs disponibles"
          value={serverStats?.available ?? 0}
          subtitle="Prêts à travailler"
          icon="✅"
          trend={{ value: 0, label: 'actuellement' }}
          loading={serverStatsLoading}
        />
        <StatCard
          title="Serveurs indisponibles"
          value={serverStats?.unavailable ?? 0}
          subtitle="En congé ou occupés"
          icon="⛔"
          loading={serverStatsLoading}
        />
        <StatCard
          title="Avec véhicule"
          value={serverStats?.with_vehicle ?? 0}
          subtitle="Peut transporter collègues"
          icon="🚗"
          loading={serverStatsLoading}
        />
      </div>

      {/* Quick Actions */}
      <QuickActions
        actions={[
          { label: 'Créer un événement', icon: '➕', description: 'Nouvel événement', variant: 'primary', href: '/dashboard/events/new' },
          { label: 'Générer une équipe', icon: '👥', description: 'Staffing', variant: 'secondary', onClick: () => setStaffSelectorOpen(true) },
          { label: 'Organiser le transport', icon: '🚗', description: 'Trajets', variant: 'secondary', onClick: () => setTransportSelectorOpen(true) },
          { label: 'Voir les urgences', icon: '⚡', description: 'Offres urgentes', variant: 'secondary', onClick: () => setUrgentSelectorOpen(true) },
          { label: 'Gamification', icon: '🏆', description: 'Classement', variant: 'secondary', href: '/dashboard/gamification' },
        ]}
      />

      {/* Upcoming Events */}
      <UpcomingEvents events={upcomingEvents?.items ?? []} loading={upcomingLoading} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Staffing Alert */}
        <StaffingAlert
          required={totalRequired}
          assigned={totalAssigned}
          remaining={remaining}
          roles={[]}
          loading={upcomingLoading}
        />

        {/* Urgent Events */}
        <UrgentEvents events={urgentEvents?.items ?? []} loading={urgentLoading} />
      </div>

      {/* Top Servers */}
      <TopServers
        rankings={topServers?.servers?.map((s) => ({
          server_name: `${s.first_name} ${s.last_name}`,
          total_points: s.monthly_points,
          rank: s.rank,
        })) ?? []}
        loading={topServersLoading}
      />

      {/* Recent Activity */}
      <RecentActivity activities={activities ?? []} loading={activitiesLoading} />

      {/* Event Selectors */}
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
