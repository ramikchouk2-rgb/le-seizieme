'use client';

import { useFocusTrap } from '@/app/components/ui/FocusTrap';
import { Event } from '@/app/components/dashboard/types';
import { EVENT_STATUSES, EVENT_PRIORITIES } from '@/app/data/events';
import StaffingProgress from './StaffingProgress';
import EventActions from './EventActions';

interface EventDrawerProps {
  event: Event | null;
  onClose: () => void;
}

export default function EventDrawer({ event, onClose }: EventDrawerProps) {
  const containerRef = useFocusTrap({ onClose, closeOnEscape: true, restoreFocus: true });

  if (!event) return null;

  const requested = event.requirements.reduce((sum, r) => sum + r.quantity, 0);
  const selected = event.requirements.reduce((sum, r) => sum + (r.accepted || 0), 0);
  const missing = requested - selected;

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const getGenderLabel = (gender: string | null) => {
    if (gender === 'MALE') return 'Hommes';
    if (gender === 'FEMALE') return 'Femmes';
    return 'Tous';
  };

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div ref={containerRef} className="absolute right-0 top-0 h-full w-full max-w-xl bg-white shadow-2xl overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-gray-900">Détails de l'événement</h2>
            <button
              onClick={onClose}
              aria-label="Fermer"
              className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-1">{event.name}</h3>
            <div className="flex items-center gap-2 mb-3">
              <span className="text-sm text-gray-500">{event.city}</span>
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                event.status === 'PLANNED' ? 'bg-blue-50 text-blue-700 border-blue-200' :
                event.status === 'CONFIRMED' ? 'bg-green-50 text-green-700 border-green-200' :
                event.status === 'IN_PROGRESS' ? 'bg-purple-50 text-purple-700 border-purple-200' :
                event.status === 'COMPLETED' ? 'bg-gray-50 text-gray-700 border-gray-200' :
                'bg-red-50 text-red-700 border-red-200'
              }`}>
                {EVENT_STATUSES[event.status as keyof typeof EVENT_STATUSES] || event.status}
              </span>
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                event.priority === 'NORMAL' ? 'bg-gray-50 text-gray-700 border-gray-200' :
                event.priority === 'HIGH' ? 'bg-orange-50 text-orange-700 border-orange-200' :
                'bg-red-50 text-red-700 border-red-200'
              }`}>
                {EVENT_PRIORITIES[event.priority as keyof typeof EVENT_PRIORITIES] || event.priority}
              </span>
            </div>
          </div>

          <div className="mb-6">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Informations</p>
            <div className="bg-gray-50 rounded-lg p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">Date début</span>
                <span className="text-sm text-gray-900">{formatDate(event.start_datetime)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">Date fin</span>
                <span className="text-sm text-gray-900">{formatDate(event.end_datetime)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">Invités</span>
                <span className="text-sm text-gray-900">{event.guest_count}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">Alcool</span>
                <span className="text-sm text-gray-900">{event.alcohol_service ? 'Oui' : 'Non'}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">Produits alimentaires</span>
                <span className="text-sm text-gray-900">{event.food_products_count}</span>
              </div>
            </div>
          </div>

          <div className="mb-6">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Staffing</p>
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-700">Postes couverts</span>
                <span className="text-sm font-bold text-gray-900">{selected} / {requested}</span>
              </div>
              <StaffingProgress requested={requested} selected={selected} missing={missing} showLabel={false} />
              <div className="grid grid-cols-3 gap-3 mt-3">
                <div className="text-center">
                  <p className="text-lg font-bold text-gray-900">{requested}</p>
                  <p className="text-xs text-gray-500">Requis</p>
                </div>
                <div className="text-center">
                  <p className="text-lg font-bold text-green-600">{selected}</p>
                  <p className="text-xs text-gray-500">Sélectionnés</p>
                </div>
                <div className="text-center">
                  <p className="text-lg font-bold text-red-600">{missing}</p>
                  <p className="text-xs text-gray-500">Manquants</p>
                </div>
              </div>
            </div>
          </div>

          <div className="mb-6">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Requirements</p>
            <div className="space-y-2">
              {event.requirements.map((req, index) => {
                const reqSelected = req.accepted || 0;
                const reqMissing = req.quantity - reqSelected;
                const reqPercentage = req.quantity > 0 ? Math.round((reqSelected / req.quantity) * 100) : 0;

                return (
                  <div key={index} className="bg-gray-50 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-gray-900">
                        {req.role_name}
                        {req.required_gender && <span className="text-gray-500 ml-1">— {getGenderLabel(req.required_gender)}</span>}
                      </span>
                      <span className={`text-xs font-medium ${reqMissing > 0 ? 'text-red-600' : 'text-green-600'}`}>
                        {reqSelected} / {req.quantity}
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-1.5 overflow-hidden">
                      <div
                        className={`h-1.5 rounded-full transition-all duration-500 ${
                          reqPercentage === 100 ? 'bg-green-500' : reqPercentage >= 50 ? 'bg-[#D4AF37]' : 'bg-red-500'
                        }`}
                        style={{ width: `${reqPercentage}%` }}
                      />
                    </div>
                    {reqMissing > 0 && (
                      <p className="text-xs text-red-600 mt-1">{reqMissing} manquant{reqMissing > 1 ? 's' : ''}</p>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="mb-6">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Transport</p>
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-sm text-gray-600">Transport à organiser</p>
            </div>
          </div>

          <div className="mb-6">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Actions</p>
            <EventActions
              onGenerateTeam={() => {}}
              onRecommendTransport={() => {}}
              onLaunchUrgentOffers={() => {}}
              onViewStaffing={() => {}}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
