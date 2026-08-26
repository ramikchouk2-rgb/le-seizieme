'use client';

import { useState, useCallback, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import Header from '@/app/components/dashboard/Header';
import { useEventOperations } from '@/app/lib/hooks';
import { Spinner } from '@/app/lib/loading';

type LoadingState = 'loading' | 'error' | 'success' | 'not_found';

const STATUS_MESSAGES: Record<string, { label: string; color: string }> = {
  PLANNED: { label: 'Événement non opérationnel', color: 'text-gray-500' },
  STAFFING: { label: 'Staffing en préparation', color: 'text-indigo-500' },
  CONFIRMED: { label: 'Événement prêt', color: 'text-green-600' },
  IN_PROGRESS: { label: 'Événement en cours', color: 'text-purple-600' },
  COMPLETED: { label: 'Événement terminé', color: 'text-gray-500' },
  CANCELLED: { label: 'Événement annulé', color: 'text-red-600' },
};

const ALERT_SEVERITY_STYLES: Record<string, string> = {
  CRITICAL: 'bg-red-50 text-red-700 border-red-200',
  WARNING: 'bg-orange-50 text-orange-700 border-orange-200',
  INFO: 'bg-blue-50 text-blue-700 border-blue-200',
};

const REQUIREMENT_STATUS_STYLES: Record<string, string> = {
  COMPLET: 'bg-green-50 text-green-700 border-green-200',
  PARTIEL: 'bg-orange-50 text-orange-700 border-orange-200',
  CRITIQUE: 'bg-red-50 text-red-700 border-red-200',
};

export default function EventOperationsPage() {
  const params = useParams();
  const eventId = params.eventId as string;

  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const { data, isLoading, error, refetch } = useEventOperations(eventId);

  useEffect(() => {
    if (data) {
      setLastUpdated(new Date());
    }
  }, [data]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header title="Mode opérationnel" />
        <main className="p-8">
          <div className="max-w-7xl mx-auto">
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm">
              <Spinner size="lg" className="mx-auto mb-4 text-[#D4AF37]" />
              <p className="text-gray-500 text-sm">Chargement du mode opérationnel...</p>
            </div>
          </div>
        </main>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header title="Mode opérationnel" />
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

  const statusInfo = STATUS_MESSAGES[data.status] || STATUS_MESSAGES.PLANNED;

  return (
    <div className="min-h-screen bg-gray-50">
      <Header title="Mode opérationnel" />
      <main className="p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{data.event_name}</h1>
              <p className="text-sm text-gray-500">{data.city} • {data.date}</p>
            </div>
            <div className="text-right">
              <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${statusInfo.color} bg-opacity-10`}>
                {statusInfo.label}
              </span>
              {lastUpdated && (
                <p className="text-xs text-gray-400 mt-1">
                  Mis à jour: {lastUpdated.toLocaleTimeString('fr-FR')}
                </p>
              )}
            </div>
          </div>

          {data.alerts && data.alerts.length > 0 && (
            <div className="space-y-3 mb-6">
              {data.alerts.map((alert, index) => (
                <div key={index} className={`p-4 rounded-xl border ${ALERT_SEVERITY_STYLES[alert.severity] || ALERT_SEVERITY_STYLES.INFO}`}>
                  <p className="text-sm font-medium">{alert.message}</p>
                </div>
              ))}
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Staffing</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Postes requis</span>
                  <span className="text-sm font-medium text-gray-900">{data.staffing_summary.requested}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Assignés</span>
                  <span className="text-sm font-medium text-gray-900">{data.staffing_summary.assigned}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Confirmés</span>
                  <span className="text-sm font-medium text-green-600">{data.staffing_summary.confirmed}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Manquants</span>
                  <span className="text-sm font-medium text-red-600">{data.staffing_summary.missing}</span>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Transport</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Groupes confirmés</span>
                  <span className="text-sm font-medium text-gray-900">{data.transport.total_groups}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Passagers</span>
                  <span className="text-sm font-medium text-gray-900">{data.transport.total_passengers}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Non assignés</span>
                  <span className="text-sm font-medium text-red-600">{data.transport.unassigned_passengers}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Exigences</h3>
            <div className="space-y-3">
              {data.requirements.map((req) => (
                <div key={req.requirement_id} className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{req.role_name}</p>
                    <p className="text-xs text-gray-500">{req.quantity} postes • Exp: {req.minimum_experience} ans • Niveau: {req.minimum_skill_level}/10</p>
                  </div>
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${REQUIREMENT_STATUS_STYLES[req.status] || REQUIREMENT_STATUS_STYLES.PARTIEL}`}>
                    {req.assigned}/{req.quantity}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
