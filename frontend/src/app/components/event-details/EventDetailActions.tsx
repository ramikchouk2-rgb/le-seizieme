'use client';

interface EventDetailActionsProps {
  onGenerateTeam: () => void;
  onRecommendTransport: () => void;
  onLaunchUrgentOffers: () => void;
  onViewStaffing: () => void;
  onAwardCompletion: () => void;
  onAwardPerformance: () => void;
  onPlanEvent?: () => void;
  onConfirmEvent?: () => void;
  onStartEvent?: () => void;
  onCompleteEvent?: () => void;
  onCancelEvent?: () => void;
  isUrgent: boolean;
  eventStatus?: string;
  generatingTeam?: boolean;
  generatingTransport?: boolean;
  transportConfirmed?: boolean;
  awardingCompletion?: boolean;
  awardingPerformance?: boolean;
  statusLoading?: boolean;
}

export default function EventDetailActions({
  onGenerateTeam,
  onRecommendTransport,
  onLaunchUrgentOffers,
  onViewStaffing,
  onAwardCompletion,
  onAwardPerformance,
  onPlanEvent,
  onConfirmEvent,
  onStartEvent,
  onCompleteEvent,
  onCancelEvent,
  isUrgent,
  eventStatus = 'PLANNED',
  generatingTeam = false,
  generatingTransport = false,
  transportConfirmed = false,
  awardingCompletion = false,
  awardingPerformance = false,
  statusLoading = false,
}: EventDetailActionsProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm mb-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Actions</h3>
      <div className="grid grid-cols-2 gap-2">
        {eventStatus === 'PLANNED' && onPlanEvent && (
          <button
            onClick={onPlanEvent}
            disabled={statusLoading}
            className="px-3 py-2 text-sm font-medium rounded-lg border border-[#D4AF37] text-[#D4AF37] hover:bg-[#D4AF37]/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {statusLoading ? 'Mise à jour...' : 'Planifier'}
          </button>
        )}
        {eventStatus === 'STAFFING' && onConfirmEvent && (
          <button
            onClick={onConfirmEvent}
            disabled={statusLoading}
            className="px-3 py-2 text-sm font-medium rounded-lg border border-[#D4AF37] text-[#D4AF37] hover:bg-[#D4AF37]/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {statusLoading ? 'Confirmation...' : 'Confirmer l\'événement'}
          </button>
        )}
        {eventStatus === 'CONFIRMED' && onStartEvent && (
          <button
            onClick={onStartEvent}
            disabled={statusLoading}
            className="px-3 py-2 text-sm font-medium rounded-lg border border-[#D4AF37] text-[#D4AF37] hover:bg-[#D4AF37]/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {statusLoading ? 'Mise à jour...' : 'Démarrer l\'événement'}
          </button>
        )}
        {eventStatus === 'IN_PROGRESS' && onCompleteEvent && (
          <button
            onClick={onCompleteEvent}
            disabled={statusLoading}
            className="px-3 py-2 text-sm font-medium rounded-lg border border-[#D4AF37] text-[#D4AF37] hover:bg-[#D4AF37]/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {statusLoading ? 'Clôture...' : 'Marquer comme terminé'}
          </button>
        )}
        {(eventStatus === 'PLANNED' || eventStatus === 'STAFFING' || eventStatus === 'CONFIRMED' || eventStatus === 'IN_PROGRESS') && onCancelEvent && (
          <button
            onClick={onCancelEvent}
            disabled={statusLoading}
            className="px-3 py-2 text-sm font-medium rounded-lg border border-red-300 text-red-700 hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {statusLoading ? 'Annulation...' : 'Annuler l\'événement'}
          </button>
        )}
        <button
          onClick={onGenerateTeam}
          disabled={generatingTeam}
          className="px-3 py-2 text-sm font-medium rounded-lg border border-[#D4AF37] text-[#D4AF37] hover:bg-[#D4AF37]/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {generatingTeam ? 'Génération...' : 'Générer l\'équipe'}
        </button>
        {transportConfirmed ? (
          <button
            disabled
            className="px-3 py-2 text-sm font-medium rounded-lg border border-green-200 text-green-700 opacity-50 cursor-not-allowed"
            title="Transport confirmé"
          >
            Transport confirmé
          </button>
        ) : (
          <button
            onClick={onRecommendTransport}
            disabled={generatingTransport}
            className="px-3 py-2 text-sm font-medium rounded-lg border border-[#D4AF37] text-[#D4AF37] hover:bg-[#D4AF37]/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {generatingTransport ? 'Analyse...' : 'Recommander le transport'}
          </button>
        )}
        {isUrgent ? (
          <button
            onClick={onLaunchUrgentOffers}
            disabled
            className="px-3 py-2 text-sm font-medium rounded-lg border border-red-200 text-red-700 opacity-50 cursor-not-allowed"
            title="Bientôt disponible"
          >
            Lancer les offres urgentes
          </button>
        ) : (
          <button
            disabled
            className="px-3 py-2 text-sm font-medium rounded-lg border border-gray-200 text-gray-500 cursor-not-allowed"
            title="Disponible uniquement pour les événements urgents"
          >
            Offres urgentes indisponibles
          </button>
        )}
        <button
          onClick={onViewStaffing}
          disabled
          className="px-3 py-2 text-sm font-medium rounded-lg border border-gray-200 text-gray-700 opacity-50 cursor-not-allowed"
          title="Bientôt disponible"
        >
          Voir le staffing
        </button>
        <button
          onClick={onAwardCompletion}
          disabled={awardingCompletion}
          className="px-3 py-2 text-sm font-medium rounded-lg border border-[#D4AF37] text-[#D4AF37] hover:bg-[#D4AF37]/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {awardingCompletion ? 'Attribution...' : 'Attribuer les points de présence'}
        </button>
        <button
          onClick={onAwardPerformance}
          disabled={awardingPerformance}
          className="px-3 py-2 text-sm font-medium rounded-lg border border-[#D4AF37] text-[#D4AF37] hover:bg-[#D4AF37]/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {awardingPerformance ? 'Attribution...' : 'Attribuer les points de performance'}
        </button>
      </div>
      <p className="text-xs text-gray-400 mt-2 italic">
        {transportConfirmed
          ? 'Transport enregistré.'
          : generatingTransport
            ? 'Analyse du transport en cours...'
            : generatingTeam
              ? 'Recommandation en cours...'
              : 'Gérez le cycle de vie de l\'événement ou générez des recommandations.'}
      </p>
    </div>
  );
}
