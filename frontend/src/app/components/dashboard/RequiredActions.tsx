'use client';

import Link from 'next/link';
import { EventListItem, EventOperationsResponse, UrgentStatus } from '@/app/lib/api';

interface ActionAlert {
  priority: number;
  tone: 'urgent' | 'warning' | 'info';
  label: string;
  detail: string;
  href: string;
}

interface RequiredActionsProps {
  events: EventListItem[];
  operations: EventOperationsResponse[];
  urgentStatuses: UrgentStatus[];
  error?: string | null;
  onRetry?: () => void;
  now?: Date;
}

const EXPIRING_SOON_MS = 30 * 60 * 1000;

function eventHref(eventId: string) {
  return `/dashboard/events/${eventId}`;
}

export default function RequiredActions({
  events,
  operations,
  urgentStatuses,
  error = null,
  onRetry,
  now = new Date(),
}: RequiredActionsProps) {
  const operationsByEvent = new Map(operations.map((operation) => [operation.event_id, operation]));
  const urgentByEvent = new Map(urgentStatuses.map((status) => [status.event_id, status]));
  const alerts: ActionAlert[] = [];

  events.forEach((event) => {
    const operation = operationsByEvent.get(event.id);
    const missing = operation?.staffing_summary.missing ?? event.staffing?.missing ?? 0;
    if (missing > 0) {
      alerts.push({
        priority: 1,
        tone: 'warning',
        label: 'Staffing incomplet',
        detail: `${missing} poste${missing > 1 ? 's' : ''} restent à pourvoir`,
        href: eventHref(event.id),
      });
    }
  });

  urgentStatuses.forEach((status) => {
    const href = eventHref(status.event_id);
    if (status.pending_count > 0) {
      alerts.push({
        priority: 0,
        tone: 'urgent',
        label: 'Offres urgentes en attente',
        detail: `${status.pending_count} offre${status.pending_count > 1 ? 's' : ''} attend une réponse`,
        href,
      });
    }

    const expiring = status.offers.filter((offer) => {
      if (offer.status !== 'PENDING' || !offer.expires_at) return false;
      const expiresAt = new Date(offer.expires_at).getTime();
      const remaining = expiresAt - now.getTime();
      return remaining > 0 && remaining <= EXPIRING_SOON_MS;
    });
    if (expiring.length > 0) {
      alerts.push({
        priority: 0,
        tone: 'urgent',
        label: 'Offres proches de l’expiration',
        detail: `${expiring.length} offre${expiring.length > 1 ? 's' : ''} expire bientôt`,
        href,
      });
    }

    if (status.expired_count > 0) {
      alerts.push({
        priority: 2,
        tone: 'warning',
        label: 'Offres expirées',
        detail: `${status.expired_count} offre${status.expired_count > 1 ? 's' : ''} n’ont pas abouti`,
        href,
      });
    }

    if (status.can_generate_next_wave && status.remaining_staff > 0) {
      alerts.push({
        priority: 2,
        tone: 'info',
        label: 'Nouvelle vague disponible',
        detail: `${status.remaining_staff} poste${status.remaining_staff > 1 ? 's' : ''} peuvent être rediffusés`,
        href,
      });
    }
  });

  operations.forEach((operation) => {
    const href = `/dashboard/events/${operation.event_id}/operations`;
    if (operation.transport.unassigned_passengers > 0) {
      alerts.push({
        priority: 1,
        tone: 'warning',
        label: 'Transport incomplet',
        detail: `${operation.transport.unassigned_passengers} serveur${operation.transport.unassigned_passengers > 1 ? 's' : ''} non couvert${operation.transport.unassigned_passengers > 1 ? 's' : ''}`,
        href,
      });
    } else if (
      operation.staffing_summary.confirmed > 0 &&
      operation.transport.total_groups === 0
    ) {
      alerts.push({
        priority: 2,
        tone: 'info',
        label: 'Transport non généré',
        detail: 'Le staffing est confirmé, mais aucun groupe de transport n’est prévu',
        href,
      });
    }
  });

  alerts.sort((a, b) => a.priority - b.priority);
  const visibleAlerts = alerts.slice(0, 6);
  const hiddenCount = alerts.length - visibleAlerts.length;

  return (
    <section className="bg-white rounded-xl border border-gray-200 shadow-sm p-6" aria-live="polite">
      <div className="flex items-start justify-between gap-4 mb-5">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Actions requises</h3>
          <p className="text-sm text-gray-500 mt-1">
            {alerts.length > 0 ? `${alerts.length} situation${alerts.length > 1 ? 's' : ''} à traiter` : 'Aucune intervention nécessaire'}
          </p>
        </div>
        {alerts.length > 0 && (
          <span className="inline-flex items-center rounded-full bg-red-50 px-3 py-1 text-xs font-semibold text-red-700 border border-red-200">
            {alerts.length}
          </span>
        )}
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 flex items-center justify-between gap-3">
          <span>Impossible de charger toutes les alertes.</span>
          {onRetry && (
            <button type="button" onClick={onRetry} className="underline font-medium whitespace-nowrap">
              Réessayer
            </button>
          )}
        </div>
      )}

      {alerts.length === 0 ? (
        <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-800">
          Tout est à jour.
        </div>
      ) : (
        <ul className="space-y-3">
          {visibleAlerts.map((alert, index) => (
            <li key={`${alert.label}-${alert.detail}-${index}`}>
              <Link href={alert.href} className="group flex items-start gap-3 rounded-lg border border-gray-200 p-3 hover:border-[#D4AF37] hover:bg-[#D4AF37]/5 transition-colors">
                <span className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white ${
                  alert.tone === 'urgent' ? 'bg-red-600' : alert.tone === 'warning' ? 'bg-[#B45F06]' : 'bg-[#526D82]'
                }`}>
                  {alert.tone === 'urgent' ? '!' : alert.tone === 'warning' ? '!' : 'i'}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-semibold text-gray-900 group-hover:text-[#8A6D1D]">
                    {alert.label}
                  </span>
                  <span className="block text-sm text-gray-600 mt-0.5">{alert.detail}</span>
                  <span className="mt-1 inline-block text-xs font-medium text-[#8A6D1D]">Voir le détail →</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}

      {hiddenCount > 0 && (
        <p className="mt-3 text-xs text-gray-500">+ {hiddenCount} autre situation visible dans les événements.</p>
      )}
    </section>
  );
}
