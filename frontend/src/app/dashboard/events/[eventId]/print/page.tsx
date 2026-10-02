'use client';

/**
 * Step 24C-D-10: the printable operational sheet for one event.
 *
 * This page reads EXACTLY ONE endpoint -- `GET /api/events/{event_id}/print-data`
 * (Step 24C-D-8B) -- through `useEventPrintData`. It deliberately does not
 * depend on the event detail page, on `useEventDetail`, or on the staffing and
 * transport endpoints: reassembling a sheet from several APIs would silently
 * drift away from the privacy rules the print contract already enforces.
 *
 * Printing is client-side via `window.print()`; no PDF is generated server-side.
 *
 * PRIVACY. This view renders the venue by ADDRESS and CITY only. The response
 * carries resolved venue `latitude`/`longitude`, and they are never read here.
 * Server GPS, attestation documents, storage paths and file ids are not part of
 * this contract at all, so they cannot be rendered.
 *
 * Authentication is not re-implemented: the route lives under /dashboard, whose
 * layout wraps every child in the existing `RouteGuard`.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';

import Header from '@/app/components/dashboard/Header';
import PrintServerPhoto from '@/app/components/event-print/PrintServerPhoto';
import { Spinner } from '@/app/lib/loading';
import { useEventPrintData } from '@/app/lib/hooks';
import { parseBackendDateTime } from '@/app/lib/datetime';
import type {
  EventPrintAssignmentResponse,
  EventPrintDataResponse,
} from '@/app/lib/types';

/* ------------------------------------------------------------ formatting */

const MONTHS_FR = [
  'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
  'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre',
];
const DAYS_FR = ['dimanche', 'lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi'];

/**
 * Deterministic French formatting.
 *
 * `toLocaleDateString` is deliberately avoided: this component is a client
 * component that Next.js still server-renders, and a server/client locale or
 * ICU difference would produce a hydration mismatch on a page whose whole job is
 * to print the same text twice.
 */
function formatDateTime(value?: string | null): string | null {
  const date = value ? parseBackendDateTime(value) : null;
  if (!date) return null;
  const day = date.getDate();
  return `${DAYS_FR[date.getDay()]} ${day} ${MONTHS_FR[date.getMonth()]} ${date.getFullYear()}`;
}

function formatTime(value?: string | null): string | null {
  const date = value ? parseBackendDateTime(value) : null;
  if (!date) return null;
  return `${String(date.getHours()).padStart(2, '0')}h${String(date.getMinutes()).padStart(2, '0')}`;
}

function formatHourDuration(minutes?: number | null): string | null {
  if (minutes === null || minutes === undefined) return null;
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest === 0 ? `${hours} h` : `${hours} h ${String(rest).padStart(2, '0')}`;
}

const GENDER_LABELS: Record<string, string> = {
  MALE: 'Homme',
  FEMALE: 'Femme',
  OTHER: 'Autre',
};

const STATUS_LABELS: Record<string, string> = {
  DRAFT: 'Brouillon',
  CONFIRMED: 'Confirmé',
  IN_PROGRESS: 'En cours',
  COMPLETED: 'Terminé',
  CANCELLED: 'Annulé',
  PROPOSED: 'Proposé',
  DECLINED: 'Refusé',
};

const PRIORITY_LABELS: Record<string, string> = {
  LOW: 'Basse',
  NORMAL: 'Normale',
  HIGH: 'Haute',
  URGENT: 'Urgente',
};

const ASSIGNMENT_STATUS_LABELS: Record<string, string> = {
  PROPOSED: 'Proposé',
  CONFIRMED: 'Confirmé',
  DECLINED: 'Refusé',
  CANCELLED: 'Annulé',
};

/** Unknown enum values fall through as the raw value rather than being hidden. */
function label(mapping: Record<string, string>, value?: string | null): string {
  if (!value) return '—';
  return mapping[value] ?? value;
}

/* -------------------------------------------------------------- fragments */

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="print-section-title print-heading">{children}</h2>;
}

function Detail({ label: text, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="print-detail">
      <dt className="print-detail-label">{text}</dt>
      <dd className="print-detail-value">{value}</dd>
    </div>
  );
}

/** Placeholder shared by every genuinely-absent optional value. */
const NOT_RECORDED = 'Non renseignée';

/* ------------------------------------------------------------------ page */

export default function EventPrintPage() {
  const params = useParams();
  const eventId = params.eventId as string;

  const { data, isLoading, error, refetch } = useEventPrintData(eventId);

  /* --------------------------------------------------------------- photos */
  /*
   * Printing waits for the photos. A photo that resolves after window.print()
   * would print blank, so the trigger below is gated on every expected photo
   * having settled.
   */
  const [settledPhotoIds, setSettledPhotoIds] = useState<ReadonlySet<string>>(
    () => new Set<string>()
  );

  const expectedPhotoIds = useMemo(() => {
    const ids = (data?.assignments ?? [])
      .filter((a) => a.profile_photo_available)
      .map((a) => a.server_id);
    return new Set(ids);
  }, [data]);

  const markPhotoSettled = useCallback((serverId: string) => {
    setSettledPhotoIds((previous) => {
      if (previous.has(serverId)) return previous;
      const next = new Set(previous);
      next.add(serverId);
      return next;
    });
  }, []);

  const photosResolved = useMemo(() => {
    if (data === undefined) return false;
    for (const id of expectedPhotoIds) {
      if (!settledPhotoIds.has(id)) return false;
    }
    return true;
  }, [data, expectedPhotoIds, settledPhotoIds]);

  /* ---------------------------------------------------------- auto print */
  /*
   * Fires once, and only after the data exists AND the photos have settled.
   * The ref guard means a re-render (or a manual "Imprimer" click) can never
   * queue a second automatic print dialog, and nothing is printed while the
   * page is still loading or has failed.
   */
  const autoPrintedRef = useRef(false);

  useEffect(() => {
    if (!data || !photosResolved || autoPrintedRef.current) return;
    autoPrintedRef.current = true;
    // A short delay lets the browser finish laying out the sheet so the dialog
    // opens on a fully painted document rather than a half-drawn one.
    const timer = window.setTimeout(() => window.print(), 300);
    return () => window.clearTimeout(timer);
  }, [data, photosResolved]);

  /* --------------------------------------------------------------- states */

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header title="Fiche d'opération" />
        <div className="p-8">
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm max-w-2xl mx-auto">
            <Spinner size="lg" className="mx-auto mb-4 text-[#D4AF37]" />
            <p className="text-gray-500 text-sm">Préparation de la fiche d'opération...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header title="Fiche d'opération" />
        <div className="p-8">
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm max-w-2xl mx-auto">
            <h2 className="text-lg font-semibold text-gray-900 mb-2">
              Fiche indisponible
            </h2>
            <p className="text-gray-500 text-sm mb-6">
              {error instanceof Error && error.message
                ? error.message
                : "Impossible de charger la fiche d'opération."}
            </p>
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={() => refetch()}
                className="inline-flex items-center px-4 py-2 bg-[#D4AF37] text-white text-sm font-medium rounded-lg hover:bg-[#B8941E] transition-colors"
              >
                Réessayer
              </button>
              <Link
                href={`/dashboard/events/${eventId}`}
                className="inline-flex items-center px-4 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-200 transition-colors"
              >
                Retour à l'événement
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const { event, requirements, assignments, transport_groups: transportGroups } =
    data as EventPrintDataResponse;

  const eventDate = formatDateTime(event.start_datetime);
  const startTime = formatTime(event.start_datetime);
  const endTime = formatTime(event.end_datetime);
  const activeTransport = transportGroups.filter((g) => g.status !== 'CANCELLED');
  const responseBudget = formatHourDuration(event.required_response_minutes);

  return (
    <div className="min-h-screen bg-gray-50">
      <Header title="Fiche d'opération" />

      {/* Toolbar: screen only. Hidden entirely under @media print. */}
      <div className="no-print px-8 pt-6">
        <div className="max-w-4xl mx-auto flex items-center justify-between gap-3 flex-wrap">
          <Link
            href={`/dashboard/events/${eventId}`}
            className="inline-flex items-center px-4 py-2 bg-white border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors"
          >
            Retour
          </Link>
          <button
            onClick={() => window.print()}
            className="inline-flex items-center px-5 py-2 bg-[#D4AF37] text-white text-sm font-medium rounded-lg hover:bg-[#B8941E] transition-colors"
          >
            Imprimer
          </button>
        </div>
      </div>

      <div className="px-4 md:px-8 py-6 print:px-0 print:py-0">
        <article className="print-sheet mx-auto max-w-4xl bg-white rounded-xl border border-gray-200 shadow-sm p-8 space-y-8 print:max-w-none print:rounded-none print:border-0 print:shadow-none print:p-0">
          {/* 1. Header / event identity */}
          <div className="print-sheet-header border-b-2 border-[#D4AF37] pb-5">
            <p className="print-brand">LE SEIZIÈME</p>
            <p className="print-doc-type">Fiche opérationnelle — Événement</p>
            <h1 className="print-event-name" data-testid="print-event-name">
              {event.name}
            </h1>
            <div className="print-header-meta">
              {eventDate && <span>{eventDate}</span>}
              {startTime && (
                <span>
                  Horaire&nbsp;: {startTime}
                  {endTime ? ` – ${endTime}` : ''}
                </span>
              )}
              <span>Statut&nbsp;: {label(STATUS_LABELS, event.status)}</span>
              {event.urgent && <span className="print-urgent">URGENT</span>}
              {!event.urgent && event.priority && (
                <span>Priorité&nbsp;: {label(PRIORITY_LABELS, event.priority)}</span>
              )}
              {event.client_name && <span>Client&nbsp;: {event.client_name}</span>}
              {event.event_type && <span>Type&nbsp;: {event.event_type}</span>}
            </div>
          </div>

          {/* 2. Event information */}
          <section className="print-section">
            <SectionTitle>Informations</SectionTitle>
            <dl className="print-details-grid">
              <Detail label="Ville" value={event.city ?? NOT_RECORDED} />
              <Detail
                label="Couverts"
                value={event.guest_count ?? NOT_RECORDED}
              />
              <Detail
                label="Temps de réponse demandé"
                value={responseBudget ?? NOT_RECORDED}
              />
              <Detail
                label="Effectif affecté"
                value={`${assignments.length} / ${requirements.reduce(
                  (sum, r) => sum + r.quantity,
                  0
                )}`}
              />
            </dl>
          </section>

          {/* 3. Venue.
              Address and city ONLY. The response also carries resolved venue
              latitude/longitude; those are internal location data and are
              deliberately not read or displayed here. */}
          <section className="print-section">
            <SectionTitle>Lieu</SectionTitle>
            <dl className="print-details-grid">
              <Detail label="Adresse" value={event.address ?? NOT_RECORDED} />
              <Detail label="Ville" value={event.city ?? NOT_RECORDED} />
            </dl>
          </section>

          {/* 4. Personnel requirements */}
          <section className="print-section">
            <SectionTitle>Besoins en personnel</SectionTitle>
            {requirements.length === 0 ? (
              <p className="print-empty">Aucun besoin en personnel défini.</p>
            ) : (
              <div className="print-table-wrap">
                <table className="print-table" data-testid="print-requirements">
                  <thead>
                    <tr>
                      <th>Rôle</th>
                      <th>Genre</th>
                      <th>Exp. min.</th>
                      <th>Niveau min. requis</th>
                      <th>Quantité</th>
                      <th>Sélectionnés</th>
                      <th>Manquants</th>
                    </tr>
                  </thead>
                  <tbody>
                    {requirements.map((req) => (
                      <tr key={req.requirement_id}>
                        <td>{req.role_name}</td>
                        <td>{req.required_gender ? label(GENDER_LABELS, req.required_gender) : '—'}</td>
                        <td>{req.minimum_experience}</td>
                        <td data-testid="print-requirement-minimum">
                          {req.required_minimum_skill_level}
                        </td>
                        <td>{req.quantity}</td>
                        <td>{req.selected}</td>
                        <td>{req.missing}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p className="print-note">
              «&nbsp;Niveau min. requis&nbsp;» est un seuil exigé par l'événement. Ce
              n'est pas le niveau réel d'un serveur&nbsp;: le niveau réel figure
              dans la section «&nbsp;Personnel affecté&nbsp;».
            </p>
          </section>

          {/* 5. Assigned personnel */}
          <section className="print-section">
            <SectionTitle>Personnel affecté</SectionTitle>
            {assignments.length === 0 ? (
              <p className="print-empty">Aucun personnel affecté pour cet événement.</p>
            ) : (
              <ul className="print-staff-list">
                {assignments.map((assignment) => (
                  <PrintStaffCard
                    key={assignment.server_id}
                    assignment={assignment}
                    onPhotoSettled={markPhotoSettled}
                  />
                ))}
              </ul>
            )}
          </section>

          {/* 6. Transport & logistics */}
          <section className="print-section">
            <SectionTitle>Transport &amp; logistique</SectionTitle>
            {activeTransport.length === 0 ? (
              <p className="print-empty">Aucun transport confirmé.</p>
            ) : (
              <ul className="print-transport-list">
                {activeTransport.map((group) => (
                  <li key={group.transport_group_id} className="print-avoid-break print-transport-card">
                    <div className="print-transport-head">
                      <span className="print-transport-driver">
                        Chauffeur&nbsp;: {group.driver_name}
                      </span>
                      <span className="print-transport-vehicle">
                        Véhicule&nbsp;: {group.vehicle}
                        {group.vehicle_type ? ` (${group.vehicle_type})` : ''}
                      </span>
                      <span>
                        Places&nbsp;: {group.passenger_count} / {group.capacity}
                      </span>
                      <span>Statut&nbsp;: {label(STATUS_LABELS, group.status)}</span>
                    </div>
                    <div className="print-transport-route">
                      <span>Départ&nbsp;: {group.departure_location_label}</span>
                      {group.departure_time && (
                        <span>Heure&nbsp;: {formatTime(group.departure_time) ?? NOT_RECORDED}</span>
                      )}
                      <span>Destination&nbsp;: {group.destination_label}</span>
                      {group.estimated_duration_minutes !== null &&
                        group.estimated_duration_minutes !== undefined && (
                          <span>Durée&nbsp;: {formatHourDuration(group.estimated_duration_minutes)}</span>
                        )}
                      {group.estimated_route_distance_km !== null &&
                        group.estimated_route_distance_km !== undefined && (
                          <span>Distance&nbsp;: {group.estimated_route_distance_km} km</span>
                        )}
                    </div>
                    {group.passengers.length > 0 && (
                      <div className="print-transport-passengers">
                        <p className="print-passengers-title">
                          Passagers ({group.passengers.length}) — hors chauffeur
                        </p>
                        <ol className="print-passengers-list">
                          {group.passengers.map((passenger) => (
                            <li key={passenger.server_id}>
                              <span className="print-passenger-order">
                                {passenger.pickup_order}.
                              </span>{' '}
                              {passenger.name}{' '}
                              <span className="print-passenger-label">
                                — {passenger.pickup_location_label}
                              </span>{' '}
                              <span className="print-passenger-status">
                                ({label(STATUS_LABELS, passenger.pickup_status)})
                              </span>
                            </li>
                          ))}
                        </ol>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* 7. Operational notes — only when the contract actually returns some. */}
          {event.notes && (
            <section className="print-section">
              <SectionTitle>Notes opérationnelles</SectionTitle>
              <p className="print-notes">{event.notes}</p>
            </section>
          )}

          <footer className="print-footer">
            <span>
              Document généré depuis les données opérationnelles de l'événement.
            </span>
            <span>Imprimeur&nbsp;: Le Seizième</span>
          </footer>
        </article>
      </div>
    </div>
  );
}

/* -------------------------------------------------------------- staff card */

function PrintStaffCard({
  assignment,
  onPhotoSettled,
}: {
  assignment: EventPrintAssignmentResponse;
  onPhotoSettled: (serverId: string) => void;
}) {
  const handlePhotoSettled = useCallback(() => {
    onPhotoSettled(assignment.server_id);
  }, [onPhotoSettled, assignment.server_id]);

  /*
   * Actual skills come from `actual_skills` (real `server_skills` rows) and are
   * rendered in their own block, clearly labelled as the server's real level.
   *
   * `required_minimum_skill_level` is the requirement threshold this assignment
   * was matched against. It is shown as a separate, explicitly labelled figure
   * so the two can never be read as one number.
   */
  const actualSkills = assignment.actual_skills ?? [];
  // The backend filters on VERIFIED, so anything else here would be a bug; the
  // guard keeps a non-verified document from ever being printed as qualified.
  const verified = (assignment.verified_attestations ?? []).filter(
    (a) => a.status === 'VERIFIED'
  );

  return (
    <li className="print-avoid-break print-staff-card" data-testid="print-staff-card">
      <div className="print-staff-head">
        <PrintServerPhoto
          serverId={assignment.server_id}
          firstName={assignment.first_name}
          lastName={assignment.last_name}
          hasProfilePhoto={assignment.profile_photo_available}
          onSettled={handlePhotoSettled}
        />
        <div className="print-staff-identity">
          <p className="print-staff-name">
            {assignment.first_name} {assignment.last_name}
          </p>
          <p className="print-staff-role">
            {assignment.role}
            {assignment.years_experience !== null &&
              assignment.years_experience !== undefined && (
                <span> — {assignment.years_experience} an(s) d'expérience</span>
              )}
          </p>
          <p className="print-staff-meta">
            Genre&nbsp;: {assignment.gender ? label(GENDER_LABELS, assignment.gender) : NOT_RECORDED}
            {' · '}
            Ville&nbsp;: {assignment.city ?? NOT_RECORDED}
            {' · '}
            Statut&nbsp;: {label(ASSIGNMENT_STATUS_LABELS, assignment.assignment_status)}
          </p>
          <p className="print-staff-meta" data-testid="print-uniform-size">
            Taille de tenue&nbsp;:{' '}
            {assignment.uniform_size ? assignment.uniform_size : NOT_RECORDED}
          </p>
        </div>
      </div>

      <div className="print-staff-columns">
        <div className="print-staff-block">
          <p className="print-block-title">Niveau minimum requis</p>
          <p className="print-block-value" data-testid="print-assignment-minimum">
            {assignment.required_minimum_skill_level}
          </p>
          <p className="print-block-hint">
            Seuil de l'exigence, pas le niveau du serveur.
          </p>
        </div>

        <div className="print-staff-block">
          <p className="print-block-title">Compétences réelles</p>
          {actualSkills.length === 0 ? (
            <p className="print-empty" data-testid="print-no-actual-skills">
              Aucune compétence enregistrée
            </p>
          ) : (
            <ul className="print-skill-list" data-testid="print-actual-skills">
              {actualSkills.map((skill) => (
                <li key={skill.skill_id}>
                  <span className="print-skill-name">{skill.skill_name}</span>
                  <span className="print-skill-level">
                    Niveau {skill.level}
                    {skill.years_experience
                      ? ` · ${skill.years_experience} an(s)`
                      : ''}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="print-staff-block">
          <p className="print-block-title">Qualifications vérifiées</p>
          {verified.length === 0 ? (
            <p className="print-empty" data-testid="print-no-attestation">
              Aucune qualification vérifiée
            </p>
          ) : (
            <ul className="print-attestation-list" data-testid="print-verified-attestations">
              {verified.map((attestation) => (
                <li key={attestation.attestation_id}>
                  <span className="print-attestation-name">
                    {attestation.qualification_name}
                  </span>
                  {attestation.verified_at && (
                    <span className="print-attestation-date">
                      {' '}
                      — vérifiée le {formatDateTime(attestation.verified_at)}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </li>
  );
}