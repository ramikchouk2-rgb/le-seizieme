'use client';

import { Event } from '@/app/components/dashboard/types';
import { getEventDurationHours } from '@/app/data/event-details';
import StatCard from '@/app/components/dashboard/StatCard';

interface EventSummaryProps {
  event: Event;
  staffing: {
    requested: number;
    selected: number;
    missing: number;
  };
}

export default function EventSummary({ event, staffing }: EventSummaryProps) {
  const duration = getEventDurationHours(event.start_datetime, event.end_datetime);

  return (
    <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
      <StatCard title="Invités" value={event.guest_count} icon="👥" />
      <StatCard title="Durée" value={`${duration}h`} icon="⏱️" />
      <StatCard title="Postes requis" value={staffing.requested} icon="📋" />
      <StatCard title="Postes couverts" value={staffing.selected} icon="✅" />
      <StatCard title="Postes manquants" value={staffing.missing} icon="⚠️" />
    </div>
  );
}
