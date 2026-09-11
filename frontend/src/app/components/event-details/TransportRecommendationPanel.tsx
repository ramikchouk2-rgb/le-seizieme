'use client';

import { useState, useMemo } from 'react';
import Link from 'next/link';
import { TransportRecommendationResponse, confirmTransportRecommendation, TransportConfirmationRequest, TransportConfirmationResponse, TransportConfirmationGroupResponse } from '@/app/lib/api';
import ConfirmTransportDialog from './ConfirmTransportDialog';
import { useAnnouncer } from '@/app/components/ui/Announcer';

interface TransportRecommendationPanelProps {
  recommendation: TransportRecommendationResponse | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  eventId: string;
  onConfirmed?: () => void;
  confirmedStaffCount?: number;
}

const CONSTRAINT_ITEMS = [
  { label: 'Chauffeur sélectionné pour l\'événement', check: (r: TransportRecommendationResponse) => r.drivers.length > 0 },
  { label: 'Véhicule actif et disponible', check: (r: TransportRecommendationResponse) => r.drivers.some(d => d.capacity > 0) },
  { label: 'Transport de collègues autorisé', check: (r: TransportRecommendationResponse) => r.drivers.some(d => d.can_transport_coworkers) },
  { label: 'Capacité respectée', check: (r: TransportRecommendationResponse) => r.passengers.length <= r.drivers.reduce((sum, d) => sum + d.available_seats, 0) },
  { label: 'Passagers disponibles', check: (r: TransportRecommendationResponse) => r.total_assigned > 0 || r.total_unassigned > 0 },
  { label: 'Rayon maximum respecté', check: (r: TransportRecommendationResponse) => r.passengers.every(p => p.distance_from_driver_km <= 20) },
  { label: 'Ordre de pickup optimisé', check: (r: TransportRecommendationResponse) => {
    const orders = r.passengers.map(p => p.pickup_order);
    return orders.length === 0 || orders.every((o, i) => o === i + 1);
  }},
  { label: 'Aucun passager en double', check: (r: TransportRecommendationResponse) => {
    const ids = r.passengers.map(p => p.server_id);
    return new Set(ids).size === ids.length;
  }},
];

export default function TransportRecommendationPanel({
  recommendation,
  loading,
  error,
  onRetry,
  eventId,
  onConfirmed,
  confirmedStaffCount = 0,
}: TransportRecommendationPanelProps) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [confirmResult, setConfirmResult] = useState<TransportConfirmationResponse | null>(null);
  const { announceSuccess, announceError } = useAnnouncer();

  const totalCapacity = useMemo(() => 
    recommendation?.drivers.reduce((sum, d) => sum + d.available_seats, 0) ?? 0, 
    [recommendation]
  );
  const totalVehicles = useMemo(() => 
    recommendation?.drivers.length ?? 0, 
    [recommendation]
  );
  const coveredStaff = useMemo(() => 
    (recommendation?.total_assigned ?? 0) + (recommendation?.drivers.length ?? 0), 
    [recommendation]
  );

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Transport recommandé</h3>
        <p className="text-gray-500 text-sm">Analyse des chauffeurs et des trajets...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-xl border border-red-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Transport recommandé</h3>
        <p className="text-sm text-red-600 mb-3">{error}</p>
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-[#D4AF37] text-white text-sm font-medium rounded-lg hover:bg-[#B8941E] transition-colors"
        >
          Réessayer
        </button>
      </div>
    );
  }

  // No recommendation yet
  if (!recommendation) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Transport recommandé</h3>
        {confirmedStaffCount === 0 ? (
          <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
            <p className="text-sm text-blue-800 mb-2">
              <strong>Aucun transport recommandé pour le moment.</strong>
            </p>
            <p className="text-xs text-blue-700">
              Confirmez d'abord les serveurs avant de générer le plan de transport.
            </p>
          </div>
        ) : (
          <p className="text-gray-500 text-sm">Cliquez sur « Recommander le transport » pour générer un plan.</p>
        )}
      </div>
    );
  }

  const hasGroups = recommendation.drivers.length > 0;

  const handleConfirmClick = () => {
    setConfirmOpen(true);
    setConfirmError(null);
    setConfirmResult(null);
  };

  const handleConfirm = async () => {
    if (!recommendation || recommendation.drivers.length === 0) return;
    setConfirmLoading(true);
    setConfirmError(null);
    try {
      const passengersByDriver: { [key: string]: { server_id: string; pickup_order: number }[] } = {};
      recommendation.passengers.forEach((p, idx) => {
        let passengerIndex = 0;
        let driverIndex = 0;
        for (let d = 0; d < recommendation.drivers.length; d++) {
          const driverAvailableSeats = recommendation.drivers[d].available_seats;
          if (idx >= passengerIndex && idx < passengerIndex + driverAvailableSeats) {
            driverIndex = d;
            break;
          }
          passengerIndex += driverAvailableSeats;
        }
        const driverId = recommendation.drivers[driverIndex].server_id;
        if (!passengersByDriver[driverId]) passengersByDriver[driverId] = [];
        passengersByDriver[driverId].push({
          server_id: p.server_id,
          pickup_order: p.pickup_order,
        });
      });

      const groups = recommendation.drivers.map(d => ({
        driver_server_id: d.server_id,
        passengers: passengersByDriver[d.server_id] || [],
      }));

      const request: TransportConfirmationRequest = { groups };
      const result = await confirmTransportRecommendation(eventId, request);
      setConfirmResult(result);
      onConfirmed?.();
      announceSuccess('Transport confirmé avec succès.');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Impossible de confirmer le transport.';
      setConfirmError(message);
      announceError('Opération impossible. Veuillez réessayer.');
    } finally {
      setConfirmLoading(false);
    }
  };

  const dialogGroups = confirmResult
    ? confirmResult.groups.map((g: TransportConfirmationGroupResponse) => ({
        group_id: g.group_id,
        driver_name: g.driver_name,
        vehicle: g.vehicle,
        capacity: g.capacity,
        passenger_count: g.passenger_count,
        estimated_distance_km: g.estimated_distance_km,
      }))
    : recommendation.drivers.map((d) => ({
        group_id: d.server_id,
        driver_name: d.name,
        vehicle: d.vehicle,
        capacity: d.capacity,
        passenger_count: 0,
        estimated_distance_km: undefined,
      }));

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Transport recommandé</h3>
          <p className="text-sm text-gray-500 mt-1">
            Organisation automatique des trajets selon la disponibilité, la capacité et la distance.
          </p>
        </div>
        <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
          Rayon max. 20 km
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-6 gap-4 mb-6">
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-gray-900">{confirmedStaffCount}</p>
          <p className="text-xs text-gray-500">Serveurs confirmés</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-gray-900">{totalVehicles}</p>
          <p className="text-xs text-gray-500">Véhicules proposés</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-gray-900">{totalVehicles}</p>
          <p className="text-xs text-gray-500">Chauffeurs</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-green-600">{recommendation?.total_assigned ?? 0}</p>
          <p className="text-xs text-gray-500">Passagers transportés</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-blue-600">{totalCapacity}</p>
          <p className="text-xs text-gray-500">Capacité totale</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-amber-600">{recommendation?.total_unassigned ?? 0}</p>
          <p className="text-xs text-gray-500">Non affectés</p>
        </div>
      </div>

      {!hasGroups ? (
        <div className="bg-amber-50 rounded-lg p-4 border border-amber-200">
          <p className="text-sm text-amber-800">
            <strong>Aucun transport ne peut être recommandé pour le moment.</strong>
          </p>
          <p className="text-xs text-amber-700 mt-1">
            {recommendation.transport_status === 'NO_SELECTED_STAFF' 
              ? 'Aucun serveur confirmé pour cet événement.' 
              : 'Aucun chauffeur éligible (véhicule, capacité, ou distance).'}
          </p>
        </div>
      ) : (
        <>
          <div className="space-y-4 mb-6">
            {recommendation.drivers.map((driver, index) => {
              const groupPassengersList = recommendation.passengers.filter((p, i) => {
                let passengerIndex = 0;
                for (let d = 0; d < index; d++) {
                  const driverAvailableSeats = recommendation.drivers[d].available_seats;
                  if (i >= passengerIndex && i < passengerIndex + driverAvailableSeats) {
                    return false;
                  }
                  passengerIndex += driverAvailableSeats;
                }
                return i >= passengerIndex && i < passengerIndex + driver.available_seats;
              });

              const remainingCapacity = driver.available_seats - groupPassengersList.length;
              const isAtCapacity = remainingCapacity <= 0;

              return (
                <div key={driver.server_id} className="border border-gray-100 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-gray-900">Groupe {index + 1}</span>
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${
                        driver.can_transport_coworkers
                          ? 'bg-green-50 text-green-700 border-green-200'
                          : 'bg-gray-50 text-gray-700 border-gray-200'
                      }`}>
                        {driver.can_transport_coworkers ? 'Transport autorisé' : 'Transport non autorisé'}
                      </span>
                      {isAtCapacity && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border bg-red-50 text-red-700 border-red-200">
                          Capacité atteinte
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="bg-gray-50 rounded-lg p-3 mb-3">
                    <p className="text-sm font-medium text-gray-900">Chauffeur</p>
                    <Link
                      href={`/dashboard/servers/${driver.server_id}`}
                      className="text-sm text-gray-700 hover:text-[#D4AF37] transition-colors"
                    >
                      {driver.name}
                    </Link>
                    <p className="text-xs text-gray-500 mt-1">
                      {driver.vehicle} • {driver.capacity} places • {driver.available_seats} passagers max.
                    </p>
                    <p className="text-xs text-gray-500">
                      Places restantes : {remainingCapacity} / {driver.available_seats}
                    </p>
                  </div>

                  <div className="mb-3">
                    <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Passagers</p>
                    <div className="space-y-2">
                      {groupPassengersList.length > 0 ? groupPassengersList.map((passenger) => (
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
                          <span className="text-xs text-gray-500">
                            {passenger.distance_from_driver_km.toFixed(1)} km
                          </span>
                        </div>
                      )) : (
                        <p className="text-xs text-gray-500">Aucun passager dans ce groupe.</p>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {recommendation.unassigned_passengers.length > 0 && (
            <div className="mb-6">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Passagers non affectés</p>
              <div className="space-y-2">
                {recommendation.unassigned_passengers.map((passenger) => (
                  <div key={passenger.server_id} className="flex items-center justify-between bg-amber-50 rounded-lg px-3 py-2 border border-amber-100">
                    <Link
                      href={`/dashboard/servers/${passenger.server_id}`}
                      className="text-sm text-gray-700 hover:text-[#D4AF37] transition-colors"
                    >
                      {passenger.name}
                    </Link>
                    <span className="text-xs text-amber-700">{passenger.reason}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="mb-4">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Contraintes respectées</p>
            <div className="flex flex-wrap gap-2">
              {CONSTRAINT_ITEMS.map((item) => {
                const passed = item.check(recommendation);
                return (
                  <span
                    key={item.label}
                    className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium border ${
                      passed
                        ? 'bg-green-50 text-green-700 border-green-200'
                        : 'bg-gray-50 text-gray-500 border-gray-200'
                    }`}
                  >
                    {passed ? '✓' : '○'} {item.label}
                  </span>
                );
              })}
            </div>
          </div>
        </>
      )}

      {hasGroups && !confirmResult && (
        <div className="mt-6 flex justify-end">
          <button
            onClick={handleConfirmClick}
            className="px-4 py-2 bg-[#D4AF37] text-white text-sm font-medium rounded-lg hover:bg-[#B8941E] transition-colors"
          >
            Confirmer le transport
          </button>
        </div>
      )}

      {confirmResult && (
        <div className="mt-6">
          <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-sm font-medium text-green-800">
              Transport confirmé avec succès.
            </p>
          </div>
        </div>
      )}

      <p className="text-xs text-gray-400 italic">
        Ces recommandations sont générées par le moteur de transport. Aucune affectation n'a encore été enregistrée.
      </p>

      <ConfirmTransportDialog
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        onConfirm={handleConfirm}
        loading={confirmLoading}
        result={confirmResult}
        error={confirmError}
        groups={dialogGroups}
      />
    </div>
  );
}
