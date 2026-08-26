'use client';

import { UrgentOffer } from '@/app/lib/api';

interface UrgentOfferCardProps {
  offer: UrgentOffer;
  onAccept?: (offer: UrgentOffer) => void;
  onDecline?: (offer: UrgentOffer) => void;
  onExpire?: (offer: UrgentOffer) => void;
}

const STATUS_CONFIG = {
  PENDING: { label: 'En attente', className: 'bg-amber-50 text-amber-700 border-amber-200' },
  ACCEPTED: { label: 'Acceptée', className: 'bg-green-50 text-green-700 border-green-200' },
  DECLINED: { label: 'Refusée', className: 'bg-red-50 text-red-700 border-red-200' },
  EXPIRED: { label: 'Expirée', className: 'bg-gray-50 text-gray-700 border-gray-200' },
};

export default function UrgentOfferCard({ offer, onAccept, onDecline, onExpire }: UrgentOfferCardProps) {
  const statusConfig = STATUS_CONFIG[offer.status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG.PENDING;

  return (
    <div className="bg-white rounded-lg border border-gray-100 p-4 shadow-sm">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-gray-900">{offer.server_name}</span>
          <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${statusConfig.className}`}>
            {statusConfig.label}
          </span>
        </div>
        <span className="text-xs text-gray-500">Vague {offer.wave_number}</span>
      </div>

      <div className="space-y-1 mb-3">
        <p className="text-xs text-gray-500">Rôle : {offer.role}</p>
        {offer.score !== null && offer.score !== undefined && (
          <p className="text-xs text-gray-500">Score : {offer.score.toFixed(1)}</p>
        )}
        {offer.distance_km !== null && offer.distance_km !== undefined && (
          <p className="text-xs text-gray-500">Distance : {offer.distance_km.toFixed(1)} km</p>
        )}
        {offer.created_at && (
          <p className="text-xs text-gray-500">Envoyée : {new Date(offer.created_at).toLocaleString('fr-FR')}</p>
        )}
        {offer.expires_at && (
          <p className="text-xs text-gray-500">Expire : {new Date(offer.expires_at).toLocaleString('fr-FR')}</p>
        )}
      </div>

      {offer.status === 'PENDING' && (
        <div className="flex gap-2">
          {onAccept && (
            <button
              onClick={() => onAccept(offer)}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-green-600 text-white hover:bg-green-700 transition-colors"
            >
              Accepter
            </button>
          )}
          {onDecline && (
            <button
              onClick={() => onDecline(offer)}
              className="px-3 py-1.5 text-xs font-medium rounded-lg border border-red-200 text-red-700 hover:bg-red-50 transition-colors"
            >
              Refuser
            </button>
          )}
          {onExpire && (
            <button
              onClick={() => onExpire(offer)}
              className="px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-200 text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Expirer
            </button>
          )}
        </div>
      )}
    </div>
  );
}
