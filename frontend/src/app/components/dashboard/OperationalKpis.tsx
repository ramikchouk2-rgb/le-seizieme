'use client';

import StatCard from '@/app/components/dashboard/StatCard';

interface OperationalKpisProps {
  upcomingEvents: number;
  urgentEvents: number;
  missingPositions: number;
  availableServers: number;
  pendingOffers: number;
  confirmedAssignments: number;
  transportIssues: number;
  loading?: boolean;
}

export default function OperationalKpis({
  upcomingEvents,
  urgentEvents,
  missingPositions,
  availableServers,
  pendingOffers,
  confirmedAssignments,
  transportIssues,
  loading = false,
}: OperationalKpisProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-7 gap-4">
      <StatCard title="Événements à venir" value={upcomingEvents} icon="📅" loading={loading} />
      <StatCard title="Événements urgents" value={urgentEvents} icon="⚡" loading={loading} />
      <StatCard title="Postes à pourvoir" value={missingPositions} icon="📋" loading={loading} />
      <StatCard title="Serveurs disponibles" value={availableServers} icon="👥" loading={loading} />
      <StatCard title="Offres en attente" value={pendingOffers} icon="⏳" loading={loading} />
      <StatCard title="Affectations confirmées" value={confirmedAssignments} icon="✅" loading={loading} />
      <StatCard title="Transports à vérifier" value={transportIssues} icon="🚗" loading={loading} />
    </div>
  );
}
