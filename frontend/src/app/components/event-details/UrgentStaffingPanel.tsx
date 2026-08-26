'use client';

import { useState, useEffect } from 'react';
import { UrgentStatus, UrgentOffer, getUrgentStatus, generateUrgentOffers, acceptUrgentOffer, declineUrgentOffer, expireUrgentOffer, UrgentActionResponse } from '@/app/lib/api';
import UrgentOfferCard from './UrgentOfferCard';
import ConfirmUrgentActionDialog from './ConfirmUrgentActionDialog';
import { useAnnouncer } from '@/app/components/ui/Announcer';

interface UrgentStaffingPanelProps {
  eventId: string;
  eventUrgent: boolean;
}

export default function UrgentStaffingPanel({ eventId, eventUrgent }: UrgentStaffingPanelProps) {
  const [status, setStatus] = useState<UrgentStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogConfig, setDialogConfig] = useState<{
    title: string;
    message: string;
    confirmLabel: string;
    onConfirm: () => void;
    offer?: UrgentOffer;
  } | null>(null);
  const { announceSuccess, announceError } = useAnnouncer();

  const loadStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getUrgentStatus(eventId);
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible de charger le statut urgent.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (eventUrgent) {
      loadStatus();
    }
  }, [eventId, eventUrgent]);

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      await generateUrgentOffers(eventId);
      await loadStatus();
      announceSuccess('Offres urgentes générées avec succès.');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Impossible de générer la vague.';
      setError(message);
      announceError('Opération impossible. Veuillez réessayer.');
    } finally {
      setGenerating(false);
    }
  };

  const handleAction = async (action: 'accept' | 'decline' | 'expire', offer: UrgentOffer) => {
    setActionLoading(offer.offer_id);
    setDialogOpen(false);
    try {
      let result: UrgentActionResponse;
      if (action === 'accept') {
        result = await acceptUrgentOffer(eventId, offer.offer_id);
        announceSuccess('Offre acceptée avec succès.');
      } else if (action === 'decline') {
        result = await declineUrgentOffer(eventId, offer.offer_id);
        announceSuccess('Offre refusée avec succès.');
      } else {
        result = await expireUrgentOffer(eventId, offer.offer_id);
        announceSuccess('Offre expirée avec succès.');
      }
      setStatus(result.urgent_status);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Impossible de traiter cette action.';
      setError(message);
      announceError('Opération impossible. Veuillez réessayer.');
    } finally {
      setActionLoading(null);
    }
  };

  const openDialog = (config: typeof dialogConfig) => {
    setDialogConfig(config);
    setDialogOpen(true);
  };

  if (!eventUrgent) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Staffing urgent</h3>
        <p className="text-sm text-gray-500">Cet événement n'est pas urgent.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Staffing urgent</h3>
        <p className="text-sm text-gray-500">Chargement du statut urgent...</p>
      </div>
    );
  }

  if (error && !status) {
    return (
      <div className="bg-white rounded-xl border border-red-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Staffing urgent</h3>
        <p className="text-sm text-red-600 mb-3">{error}</p>
        <button
          onClick={loadStatus}
          className="px-4 py-2 bg-[#D4AF37] text-white text-sm font-medium rounded-lg hover:bg-[#B8941E] transition-colors"
        >
          Réessayer
        </button>
      </div>
    );
  }

  if (!status) {
    return null;
  }

  const pendingOffers = status.offers.filter(o => o.status === 'PENDING');

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Staffing urgent</h3>
          <p className="text-sm text-gray-500 mt-1">
            {status.wave_number > 0
              ? `Vague ${status.wave_number}`
              : 'Aucune vague générée'}
          </p>
        </div>
        {status.can_generate_next_wave && (
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="px-4 py-2 bg-[#D4AF37] text-white text-sm font-medium rounded-lg hover:bg-[#B8941E] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {generating ? 'Génération...' : 'Générer la prochaine vague'}
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-gray-900">{status.offers_sent}</p>
          <p className="text-xs text-gray-500">Offres envoyées</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-amber-600">{status.pending_count}</p>
          <p className="text-xs text-gray-500">En attente</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-green-600">{status.accepted_count}</p>
          <p className="text-xs text-gray-500">Acceptées</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-red-600">{status.declined_count + status.expired_count}</p>
          <p className="text-xs text-gray-500">Refusées / Expirées</p>
        </div>
      </div>

      <div className="bg-gray-50 rounded-lg p-4 mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Personnel confirmé</span>
          <span className="text-sm font-bold text-gray-900">
            {status.total_staff_confirmed} / {status.total_staff_needed}
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-[#D4AF37] h-2 rounded-full transition-all"
            style={{
              width: `${status.total_staff_needed > 0 ? (status.total_staff_confirmed / status.total_staff_needed) * 100 : 0}%`,
            }}
          />
        </div>
        <p className="text-xs text-gray-500 mt-1">
          Personnel restant : {status.remaining_staff}
        </p>
      </div>

      {status.requirements.length > 0 && (
        <div className="mb-6">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Détail par rôle</p>
          <div className="space-y-2">
            {status.requirements.map((req) => (
              <div key={req.role} className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2">
                <span className="text-sm text-gray-700">{req.role}</span>
                <span className={`text-xs font-medium ${req.remaining > 0 ? 'text-red-600' : 'text-green-600'}`}>
                  {req.accepted}/{req.requested} {req.remaining > 0 ? `(${req.remaining} manquant)` : 'COMPLET'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {status.offers.length > 0 && (
        <div className="mb-6">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Offres de la vague actuelle</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {status.offers.map((offer) => (
              <UrgentOfferCard
                key={offer.offer_id}
                offer={offer}
                onAccept={(o) =>
                  openDialog({
                    title: 'Confirmer l\'affectation',
                    message: 'Vous êtes sur le point d\'accepter cette offre urgente. Le serveur sera assigné à l\'événement.',
                    confirmLabel: 'Accepter',
                    offer: o,
                    onConfirm: () => handleAction('accept', o),
                  })
                }
                onDecline={(o) =>
                  openDialog({
                    title: 'Refuser cette offre ?',
                    message: 'Cette action est irréversible. Le serveur ne recevra plus cette offre.',
                    confirmLabel: 'Refuser',
                    offer: o,
                    onConfirm: () => handleAction('decline', o),
                  })
                }
                onExpire={(o) =>
                  openDialog({
                    title: 'Expirer cette offre ?',
                    message: 'Cette action marquera l\'offre comme expirée.',
                    confirmLabel: 'Expirer',
                    offer: o,
                    onConfirm: () => handleAction('expire', o),
                  })
                }
              />
            ))}
          </div>
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      <ConfirmUrgentActionDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onConfirm={() => dialogConfig?.onConfirm()}
        loading={!!actionLoading}
        title={dialogConfig?.title || ''}
        message={dialogConfig?.message || ''}
        confirmLabel={dialogConfig?.confirmLabel || 'Confirmer'}
        offer={dialogConfig?.offer || null}
      />
    </div>
  );
}
