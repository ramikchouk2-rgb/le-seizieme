'use client';

import { useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import Header from '@/app/components/dashboard/Header';
import EventHeader from '@/app/components/event-details/EventHeader';
import EventSummary from '@/app/components/event-details/EventSummary';
import StaffingOverview from '@/app/components/event-details/StaffingOverview';
import RequirementBoard from '@/app/components/event-details/RequirementBoard';
import StaffAssignmentDrawer from '@/app/components/event-details/StaffAssignmentDrawer';
import MissingStaffPanel from '@/app/components/event-details/MissingStaffPanel';
import EventDetailActions from '@/app/components/event-details/EventDetailActions';
import StaffingScore from '@/app/components/event-details/StaffingScore';
import { useEventDetail, useGenerateStaffRecommendations, useGenerateTransportRecommendation, useUpdateEventStatus, useAwardCompletionPoints, useAwardPerformancePoints } from '@/app/lib/hooks';
import { StaffAssignment, ASSIGNMENT_STATUSES, Event as AppEvent, EventDetailData } from '@/app/components/dashboard/types';
import { StaffRecommendationResponse, TransportRecommendationResponse } from '@/app/lib/api';
import StaffRecommendationPanel from '@/app/components/event-details/StaffRecommendationPanel';
import TransportRecommendationPanel from '@/app/components/event-details/TransportRecommendationPanel';
import UrgentStaffingPanel from '@/app/components/event-details/UrgentStaffingPanel';
import GamificationPanel from '@/app/components/event-details/GamificationPanel';
import StaffManagementPanel from '@/app/components/event-details/StaffManagementPanel';
import ConfirmEventStatusDialog from '@/app/components/event-details/ConfirmEventStatusDialog';
import { Spinner } from '@/app/lib/loading';
import { useAnnouncer } from '@/app/components/ui/Announcer';

type LoadingState = 'loading' | 'error' | 'success' | 'not_found';

export default function EventDetailPage() {
  const params = useParams();
  const router = useRouter();
  const eventId = params.eventId as string;
  const { announceSuccess, announceError } = useAnnouncer();

  const [selectedAssignment, setSelectedAssignment] = useState<StaffAssignment | null>(null);
  const [statusDialog, setStatusDialog] = useState<{ open: boolean; title: string; description: string; confirmLabel: string; status: string } | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const { data, isLoading, error, refetch } = useEventDetail(eventId);
  const generateStaffMutation = useGenerateStaffRecommendations();
  const generateTransportMutation = useGenerateTransportRecommendation();
  const updateStatusMutation = useUpdateEventStatus();
  const awardCompletionMutation = useAwardCompletionPoints();
  const awardPerformanceMutation = useAwardPerformancePoints();

  const [recommendations, setRecommendations] = useState<StaffRecommendationResponse | null>(null);
  const [recommendationError, setRecommendationError] = useState<string | null>(null);
  const [transportRecommendation, setTransportRecommendation] = useState<TransportRecommendationResponse | null>(null);
  const [transportError, setTransportError] = useState<string | null>(null);

  const transportConfirmed = data?.transport && data.transport.total_groups > 0;

  const handleGenerateTeam = async () => {
    setRecommendationError(null);
    try {
      const result = await generateStaffMutation.mutateAsync(eventId);
      setRecommendations(result);
      announceSuccess('Équipe générée avec succès.');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Impossible de générer les recommandations.';
      setRecommendationError(message);
      setRecommendations(null);
      announceError('Opération impossible. Veuillez réessayer.');
    }
  };

  const handleRecommendTransport = async () => {
    setTransportError(null);
    try {
      const result = await generateTransportMutation.mutateAsync(eventId);
      setTransportRecommendation(result);
      announceSuccess('Transport recommandé avec succès.');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Impossible de générer la recommandation de transport.';
      setTransportError(message);
      setTransportRecommendation(null);
      announceError('Opération impossible. Veuillez réessayer.');
    }
  };

  const handleStatusChange = async (newStatus: string) => {
    setStatusMessage(null);
    try {
      await updateStatusMutation.mutateAsync({ eventId, payload: { status: newStatus } });
      setStatusMessage(`Statut mis à jour: ${newStatus}`);
      announceSuccess(`Événement ${newStatus.toLowerCase()} avec succès.`);
      await refetch();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Impossible de mettre à jour le statut.';
      setStatusMessage(message);
      announceError('Opération impossible. Veuillez réessayer.');
    }
  };

  const handleStatusDialog = (title: string, description: string, confirmLabel: string, status: string) => {
    setStatusDialog({ open: true, title, description, confirmLabel, status });
  };

  const handleStatusDialogClose = () => {
    setStatusDialog(null);
  };

  const handleStatusDialogConfirm = async () => {
    if (statusDialog) {
      await handleStatusChange(statusDialog.status);
      handleStatusDialogClose();
    }
  };

  const handleAwardCompletion = async () => {
    try {
      await awardCompletionMutation.mutateAsync(eventId);
      await refetch();
      announceSuccess('Points de présence attribués avec succès.');
    } catch {
      announceError('Opération impossible. Veuillez réessayer.');
    }
  };

  const handleAwardPerformance = async () => {
    try {
      await awardPerformanceMutation.mutateAsync(eventId);
      await refetch();
      announceSuccess('Points de performance attribués avec succès.');
    } catch {
      announceError('Opération impossible. Veuillez réessayer.');
    }
  };

  if (isLoading) {
    return <PageLoading message="Chargement de l'événement..." />;
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header title="Événement" />
        <main className="p-8">
          <div className="max-w-7xl mx-auto">
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm">
              <p className="text-gray-500 text-sm mb-4">{error?.message || 'Événement introuvable'}</p>
              <button
                onClick={() => refetch()}
                className="inline-flex items-center px-4 py-2 bg-[#D4AF37] text-white text-sm font-medium rounded-lg hover:bg-[#B8941E] transition-colors"
              >
                Réessayer
              </button>
            </div>
          </div>
        </main>
      </div>
    );
  }

  const { event, staffing, assignments, requirements_detail } = data;

  const eventWithRequirements = {
    ...event,
    requirements: requirements_detail.map((r: { role_name: string; quantity: number; required_gender: string | null; minimum_experience: number; minimum_skill_level: number; selected: number; missing: number }) => ({
      role_name: r.role_name,
      quantity: r.quantity,
      required_gender: r.required_gender,
      minimum_experience: r.minimum_experience,
      minimum_skill_level: r.minimum_skill_level,
      accepted: r.selected,
      remaining: r.missing,
    })),
  } as AppEvent;

  // Count confirmed staff (assignments with CONFIRMED status)
  const confirmedStaffCount = assignments?.filter(a => a.status === 'CONFIRMED').length ?? 0;

  return (
    <div className="min-h-screen bg-gray-50">
      <Header title="Événement" />
      <main className="p-8">
        <div className="max-w-7xl mx-auto">
          <EventHeader event={eventWithRequirements} onEdit={() => router.push(`/dashboard/events/${eventId}/edit`)} />

          <nav className="flex items-center gap-1 mb-6 bg-white rounded-xl border border-gray-200 p-1 shadow-sm" aria-label="Sous-pages de l'événement">
            <Link
              href={`/dashboard/events/${eventId}/attendance`}
              className="flex-1 text-center px-4 py-2 text-sm font-medium rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Présences
            </Link>
            <Link
              href={`/dashboard/events/${eventId}/evaluations`}
              className="flex-1 text-center px-4 py-2 text-sm font-medium rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Évaluations
            </Link>
            <Link
              href={`/dashboard/events/${eventId}/operations`}
              className="flex-1 text-center px-4 py-2 text-sm font-medium rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Opérations
            </Link>
            <Link
              href={`/dashboard/events/${eventId}/report`}
              className="flex-1 text-center px-4 py-2 text-sm font-medium rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Rapport
            </Link>
          </nav>

          {statusMessage && (
            <div className="mb-6 bg-green-50 border border-green-200 rounded-xl p-4 text-sm text-green-700">
              {statusMessage}
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <EventSummary event={eventWithRequirements} staffing={staffing} />
              <StaffingOverview staffing={staffing} />
              <MissingStaffPanel requirements={requirements_detail} />

              <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Actions rapides</h3>
                <div className="flex flex-wrap gap-3">
                  <button
                    onClick={handleGenerateTeam}
                    disabled={generateStaffMutation.isPending}
                    className="inline-flex items-center px-4 py-2 bg-[#D4AF37] text-white text-sm font-medium rounded-lg hover:bg-[#B8941E] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {generateStaffMutation.isPending && <Spinner size="sm" className="mr-2 text-white" />}
                    Générer l'équipe
                  </button>
                  <button
                    onClick={handleRecommendTransport}
                    disabled={generateTransportMutation.isPending}
                    className="inline-flex items-center px-4 py-2 border border-[#D4AF37] text-[#D4AF37] text-sm font-medium rounded-lg hover:bg-[#D4AF37]/10 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {generateTransportMutation.isPending && <Spinner size="sm" className="mr-2" />}
                    Recommander le transport
                  </button>
                  {event.status === 'COMPLETED' && (
                    <>
                      <button
                        onClick={handleAwardCompletion}
                        disabled={awardCompletionMutation.isPending}
                        className="inline-flex items-center px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {awardCompletionMutation.isPending && <Spinner size="sm" className="mr-2" />}
                        Attribuer points de présence
                      </button>
                      <button
                        onClick={handleAwardPerformance}
                        disabled={awardPerformanceMutation.isPending}
                        className="inline-flex items-center px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {awardPerformanceMutation.isPending && <Spinner size="sm" className="mr-2" />}
                        Attribuer points de performance
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Workflow Progression */}
              <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm mb-4">
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold ${
                      confirmedStaffCount > 0 ? 'bg-green-500' : 'bg-gray-300'
                    }`}>
                      {confirmedStaffCount > 0 ? '✓' : '1'}
                    </div>
                    <span className="text-sm font-medium text-gray-900">Staffing</span>
                    {confirmedStaffCount > 0 && (
                      <span className="text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded-full">
                        {confirmedStaffCount} confirmé{confirmedStaffCount !== 1 ? 's' : ''}
                      </span>
                    )}
                  </div>
                  <div className="flex-1 h-0.5 bg-gray-200" />
                  <div className="flex items-center gap-2">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold ${
                      transportConfirmed ? 'bg-green-500' : (transportRecommendation ? 'bg-[#D4AF37]' : 'bg-gray-300')
                    }`}>
                      {transportConfirmed ? '✓' : (transportRecommendation ? '2' : '2')}
                    </div>
                    <span className="text-sm font-medium text-gray-900">Transport</span>
                    {transportConfirmed && (
                      <span className="text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded-full">
                        Confirmé
                      </span>
                    )}
                    {transportRecommendation && !transportConfirmed && (
                      <span className="text-xs text-[#D4AF37] bg-[#D4AF37]/10 px-2 py-0.5 rounded-full">
                        Recommandé
                      </span>
                    )}
                    {confirmedStaffCount === 0 && !transportRecommendation && (
                      <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
                        En attente
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <StaffRecommendationPanel
                recommendations={recommendations}
                loading={generateStaffMutation.isPending}
                error={recommendationError}
                onRetry={handleGenerateTeam}
                eventId={eventId}
                onConfirmed={async () => { await refetch(); setRecommendations(null); }}
              />

              <TransportRecommendationPanel
                recommendation={transportRecommendation}
                loading={generateTransportMutation.isPending}
                error={transportError}
                onRetry={handleRecommendTransport}
                eventId={eventId}
                onConfirmed={async () => { await refetch(); setTransportRecommendation(null); }}
                confirmedStaffCount={confirmedStaffCount}
              />
              
              {/* Confirmed Transport Plan Display */}
              {transportConfirmed && data?.transport?.groups && data.transport.groups.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                    <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Plan de transport confirmé
                  </h3>
                  <p className="text-sm text-gray-500 mb-4">
                    {data.transport.total_groups} véhicule{data.transport.total_groups !== 1 ? 's' : ''} • 
                    {data.transport.total_passengers} passager{data.transport.total_passengers !== 1 ? 's' : ''} transporté{data.transport.total_passengers !== 1 ? 's' : ''}
                  </p>
                  <div className="space-y-4">
                    {data.transport.groups.map((group: any, index: number) => (
                      <div key={group.group_id} className="border border-gray-100 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-3">
                          <span className="text-sm font-semibold text-gray-900">Véhicule {index + 1}</span>
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border bg-green-50 text-green-700 border-green-200">
                            Confirmé
                          </span>
                        </div>
                        <div className="bg-gray-50 rounded-lg p-3 mb-3">
                          <p className="text-sm font-medium text-gray-900">Conducteur</p>
                          <Link
                            href={`/dashboard/servers/${group.driver_server_id}`}
                            className="text-sm text-gray-700 hover:text-[#D4AF37] transition-colors"
                          >
                            {group.driver_name}
                          </Link>
                          <p className="text-xs text-gray-500 mt-1">
                            {group.vehicle} • {group.capacity} places • {group.passenger_count} passager{group.passenger_count !== 1 ? 's' : ''}
                          </p>
                          {group.estimated_distance_km !== undefined && group.estimated_distance_km !== null && (
                            <p className="text-xs text-gray-500 mt-1">
                              Distance estimée : {group.estimated_distance_km.toFixed(1)} km
                            </p>
                          )}
                        </div>
                        <div className="mb-3">
                          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Passagers</p>
                          <div className="space-y-2">
                            {group.passengers && group.passengers.length > 0 ? group.passengers.map((passenger: any) => (
                              <div key={passenger.server_id} className="flex items-center justify-between bg-white rounded-lg px-3 py-2 border border-gray-50">
                                <div className="flex items-center gap-2">
                                  <span className="w-5 h-5 rounded-full bg-[#D4AF37]/10 flex items-center justify-center text-xs font-bold text-[#D4AF37]">
                                    {passenger.pickup_order}
                                  </span>
                                  <Link
                                    href={`/dashboard/servers/${passenger.server_id}`}
                                    className="text-sm text-gray-700 hover:text-[#D4AF37] transition-colors"
                                  >
                                    {passenger.name}
                                  </Link>
                                </div>
                                <span className="text-xs text-gray-500 capitalize">{passenger.pickup_status || 'En attente'}</span>
                              </div>
                            )) : (
                              <p className="text-xs text-gray-500">Aucun passager dans ce groupe.</p>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <UrgentStaffingPanel eventId={eventId} eventUrgent={event.urgent} />

              <GamificationPanel />
            </div>

            <div className="space-y-6">
              <EventDetailActions
                onGenerateTeam={handleGenerateTeam}
                onRecommendTransport={handleRecommendTransport}
                onLaunchUrgentOffers={() => {}}
                onViewStaffing={() => {}}
                onAwardCompletion={handleAwardCompletion}
                onAwardPerformance={handleAwardPerformance}
                onPlanEvent={() => handleStatusDialog('Planifier', 'Confirmer la planification de cet événement?', 'Planifier', 'PLANNED')}
                onConfirmEvent={() => handleStatusDialog('Confirmer', 'Confirmer cet événement?', 'Confirmer', 'CONFIRMED')}
                onStartEvent={() => handleStatusDialog('Démarrer', 'Démarrer cet événement?', 'Démarrer', 'IN_PROGRESS')}
                onCompleteEvent={() => handleStatusDialog('Terminer', 'Marquer cet événement comme terminé?', 'Terminer', 'COMPLETED')}
                onCancelEvent={() => handleStatusDialog('Annuler', 'Annuler cet événement?', 'Annuler', 'CANCELLED')}
                isUrgent={event.urgent}
                eventStatus={event.status}
                generatingTeam={generateStaffMutation.isPending}
                generatingTransport={generateTransportMutation.isPending}
                transportConfirmed={transportConfirmed}
                awardingCompletion={awardCompletionMutation.isPending}
                awardingPerformance={awardPerformanceMutation.isPending}
                statusLoading={updateStatusMutation.isPending}
              />
              <StaffingScore assignments={assignments} />
              <RequirementBoard requirements={requirements_detail} eventId={eventId} onRefresh={refetch} />
              <StaffManagementPanel
                assignments={assignments}
                eventId={eventId}
                requirements={requirements_detail}
                onRefresh={refetch}
              />
            </div>
          </div>
        </div>
      </main>

      {selectedAssignment && (
        <StaffAssignmentDrawer
          assignment={selectedAssignment}
          onClose={() => setSelectedAssignment(null)}
        />
      )}

      {statusDialog?.open && (
        <ConfirmEventStatusDialog
          open={statusDialog.open}
          title={statusDialog.title}
          description={statusDialog.description}
          confirmLabel={statusDialog.confirmLabel}
          onConfirm={handleStatusDialogConfirm}
          onClose={handleStatusDialogClose}
          loading={updateStatusMutation.isPending}
        />
      )}
    </div>
  );
}

function PageLoading({ message }: { message: string }) {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <Spinner size="lg" className="mx-auto mb-4 text-[#D4AF37]" />
        <p className="text-gray-500 text-sm">{message}</p>
      </div>
    </div>
  );
}
