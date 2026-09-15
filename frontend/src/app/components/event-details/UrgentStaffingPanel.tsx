'use client';

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { UrgentStatus, UrgentOffer, getUrgentStatus, generateUrgentOffers, acceptUrgentOffer, declineUrgentOffer, expireUrgentOffer, UrgentActionResponse } from '@/app/lib/api';
import UrgentOfferCard from './UrgentOfferCard';
import ConfirmUrgentActionDialog from './ConfirmUrgentActionDialog';
import { useAnnouncer } from '@/app/components/ui/Announcer';

interface UrgentStaffingPanelProps {
  eventId: string;
  eventUrgent: boolean;
}

const WAVE_STATUS_LABELS: Record<string, string> = {
  PENDING: 'En cours',
  ACCEPTED: 'Acceptée',
  DECLINED: 'Refusée',
  EXPIRED: 'Expirée',
};

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
      const interval = setInterval(loadStatus, 30000);
      return () => clearInterval(interval);
    }
  }, [eventId, eventUrgent]);

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      await generateUrgentOffers(eventId);
      await loadStatus();
      announceSuccess('Vague lancée avec succès.');
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
        announceSuccess('Offre acceptée avec succès. Serveur assigné.');
      } else if (action === 'decline') {
        result = await declineUrgentOffer(eventId, offer.offer_id);
        announceSuccess('Offre refusée.');
      } else {
        result = await expireUrgentOffer(eventId, offer.offer_id);
        announceSuccess('Offre expirée.');
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

  const openGenerateDialog = () => {
    if (!status) return;
    const remaining = status.remaining_staff;
    const deadline = `${15} min`;
    setDialogConfig({
      title: 'Lancer une nouvelle vague ?',
      message: `Vous êtes sur le point de lancer la vague ${status.wave_number + 1}. Les offres seront envoyées aux serveurs éligibles pour les ${remaining} poste${remaining > 1 ? 's' : ''} restant${remaining > 1 ? 's' : ''}.`,
      confirmLabel: 'Lancer la vague',
      onConfirm: handleGenerate,
    });
    setDialogOpen(true);
  };

  const openActionDialog = (action: 'accept' | 'decline' | 'expire', offer: UrgentOffer) => {
    const labels = { accept: 'Accepter', decline: 'Refuser', expire: 'Expirer' };
    const messages = {
      accept: 'Confirmer l\'affectation de ce serveur ? Il sera assigné à l\'événement et l\'offre sera marquée comme acceptée.',
      decline: 'Refuser cette offre ? Cette action est irréversible. Le serveur ne recevra plus cette offre.',
      expire: 'Expirer cette offre ? Elle sera marquée comme expirée.',
    };
    setDialogConfig({
      title: messages[action],
      message: messages[action],
      confirmLabel: labels[action],
      offer,
      onConfirm: () => handleAction(action, offer),
    });
    setDialogOpen(true);
  };

  if (!eventUrgent) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Staffing urgent</h3>
        <p className="text-sm text-gray-500">Cet événement n'est pas marqué comme urgent.</p>
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
  const currentWaveOffers = status.offers.filter(o => o.wave_number === status.wave_number);

  const getTimeRemaining = (expiresAt: string | null) => {
    if (!expiresAt) return null;
    const now = new Date();
    const expiry = new Date(expiresAt);
    const diff = expiry.getTime() - now.getTime();
    if (diff <= 0) return { expired: true, text: 'Expirée' };
    const minutes = Math.floor(diff / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);
    return { expired: false, text: minutes > 0 ? `${minutes} min ${seconds}s` : `${seconds}s` };
  };

  const acceptanceRate = status.offers_sent > 0
    ? Math.round((status.accepted_count / status.offers_sent) * 100)
    : 0;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
          <h3 className="text-lg font-semibold text-gray-900">Staffing urgent</h3>
        </div>
        <div className="flex items-center gap-2">
          {status.wave_number > 0 && (
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-[#D4AF37] text-white">
              Vague {status.wave_number}
            </span>
          )}
          {status.wave_number === 0 && (
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
              Aucune vague
            </span>
          )}
        </div>
      </div>

      {status.wave_number === 0 && status.can_generate_next_wave && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
          <p className="text-sm text-blue-800 mb-2">
            <strong>Aucune vague de recrutement n'a encore été lancée.</strong>
          </p>
          <p className="text-xs text-blue-700 mb-3">
            Il y a {status.remaining_staff} poste{status.remaining_staff > 1 ? 's' : ''} à pourvoir. Cliquez sur « Lancer la première vague » pour commencer.
          </p>
          <button
            onClick={openGenerateDialog}
            disabled={generating}
            className="px-4 py-2 bg-[#D4AF37] text-white text-sm font-medium rounded-lg hover:bg-[#B8941E] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {generating ? 'Génération...' : 'Lancer la première vague'}
          </button>
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
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
          <p className="text-2xl font-bold text-red-600">{status.declined_count}</p>
          <p className="text-xs text-gray-500">Refusées</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-gray-600">{status.expired_count}</p>
          <p className="text-xs text-gray-500">Expirées</p>
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
        <div className="flex items-center justify-between mt-2">
          <p className="text-xs text-gray-500">
            Personnel restant : {status.remaining_staff}
          </p>
          <p className="text-xs text-gray-500">
            Taux d'acceptation : {acceptanceRate}%
          </p>
        </div>
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

      {status.waves && status.waves.length > 0 && (
        <div className="mb-6">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Historique des vagues</p>
          <div className="space-y-2">
            {status.waves.map((wave) => (
              <div key={wave.wave_number} className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2">
                <div className="flex items-center gap-3">
                  <span className={`text-sm font-medium ${wave.wave_number === status.wave_number ? 'text-[#D4AF37]' : 'text-gray-700'}`}>
                    Vague {wave.wave_number}
                  </span>
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border bg-blue-50 text-blue-700 border-blue-200">
                    {WAVE_STATUS_LABELS.PENDING}
                  </span>
                </div>
                <div className="flex items-center gap-4 text-xs text-gray-500">
                  <span>Envoyées: {wave.offers_sent}</span>
                  <span className="text-amber-600">En attente: {wave.pending}</span>
                  <span className="text-green-600">Acceptées: {wave.accepted}</span>
                  <span className="text-red-600">Refusées: {wave.declined}</span>
                  <span className="text-gray-600">Expirées: {wave.expired}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {status.can_generate_next_wave && status.wave_number > 0 && (
        <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <p className="text-sm text-amber-800 mb-2">
            <strong>Postes restants : {status.remaining_staff}</strong>
          </p>
          <p className="text-xs text-amber-700 mb-3">
            La vague actuelle n'a plus d'offres en attente. Vous pouvez lancer la prochaine vague.
          </p>
          <button
            onClick={openGenerateDialog}
            disabled={generating}
            className="px-4 py-2 bg-[#D4AF37] text-white text-sm font-medium rounded-lg hover:bg-[#B8941E] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {generating ? 'Génération...' : `Lancer la vague ${status.wave_number + 1}`}
          </button>
        </div>
      )}

      {status.offers.length > 0 && (
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Offres de la vague actuelle</p>
            {status.pending_count > 0 && (
              <p className="text-xs text-gray-500">
                {currentWaveOffers.map(o => {
                  const time = getTimeRemaining(o.expires_at);
                  return time && !time.expired ? time.text : '';
                }).filter(Boolean).join(', ') || 'En cours'}
              </p>
            )}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {currentWaveOffers.map((offer) => (
              <UrgentOfferCard
                key={offer.offer_id}
                offer={offer}
                timeRemaining={getTimeRemaining(offer.expires_at)}
                onAccept={(o) => openActionDialog('accept', o)}
                onDecline={(o) => openActionDialog('decline', o)}
                onExpire={(o) => openActionDialog('expire', o)}
              />
            ))}
          </div>
        </div>
      )}

      {status.remaining_staff === 0 && status.total_staff_needed > 0 && (
        <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg text-center">
          <p className="text-sm font-medium text-green-800">
            ✓ Staffing complet - Tous les postes sont pourvus
          </p>
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
        loading={!!actionLoading || generating}
        title={dialogConfig?.title || ''}
        message={dialogConfig?.message || ''}
        confirmLabel={dialogConfig?.confirmLabel || 'Confirmer'}
        offer={dialogConfig?.offer || null}
      />
    </div>
  );
}
