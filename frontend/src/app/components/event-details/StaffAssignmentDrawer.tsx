'use client';

import { useFocusTrap } from '@/app/components/ui/FocusTrap';
import { StaffAssignment, ASSIGNMENT_STATUSES } from '@/app/components/dashboard/types';

interface StaffAssignmentDrawerProps {
  assignment: StaffAssignment | null;
  onClose: () => void;
}

const SECTION = 'text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2';

export default function StaffAssignmentDrawer({ assignment, onClose }: StaffAssignmentDrawerProps) {
  const containerRef = useFocusTrap({ onClose, closeOnEscape: true, restoreFocus: true });

  if (!assignment) return null;

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div ref={containerRef} className="absolute right-0 top-0 h-full w-full max-w-md bg-white shadow-2xl overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-gray-900">Détails de l'affectation</h2>
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

          <div className="flex items-center gap-4 mb-6">
            <div className="w-16 h-16 rounded-full bg-[#D4AF37]/10 flex items-center justify-center text-[#D4AF37] text-xl font-bold">
              {assignment.first_name[0]}{assignment.last_name[0]}
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                {assignment.first_name} {assignment.last_name}
              </h3>
              <p className="text-sm text-gray-500">{assignment.city}</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 mb-6">
            <div className="bg-gray-50 rounded-lg p-3">
              <p className={SECTION}>Rôle</p>
              <p className="text-sm text-gray-900">{assignment.role}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className={SECTION}>Score</p>
              <p className="text-sm font-bold text-[#D4AF37]">{(assignment.score ?? 0).toFixed(1)}/100</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className={SECTION}>Distance</p>
              <p className="text-sm text-gray-900">{(assignment.distance_km ?? 0).toFixed(1)} km</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className={SECTION}>Expérience</p>
              <p className="text-sm text-gray-900">{assignment.years_experience} ans</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className={SECTION}>Niveau de compétence</p>
              <p className="text-sm text-gray-900">{assignment.skill_level}/10</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className={SECTION}>Disponibilité</p>
              <p className={`text-sm font-medium ${assignment.availability_status === 'AVAILABLE' ? 'text-green-600' : 'text-red-600'}`}>
                {assignment.availability_status === 'AVAILABLE' ? 'Disponible' : 'Indisponible'}
              </p>
            </div>
          </div>

          <div className="mb-6">
            <p className={SECTION}>Statut</p>
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
              assignment.status === 'PROPOSED' ? 'bg-blue-50 text-blue-700 border-blue-200' :
              assignment.status === 'CONFIRMED' ? 'bg-green-50 text-green-700 border-green-200' :
              assignment.status === 'DECLINED' ? 'bg-red-50 text-red-700 border-red-200' :
              assignment.status === 'CANCELLED' ? 'bg-gray-50 text-gray-700 border-gray-200' :
              'bg-purple-50 text-purple-700 border-purple-200'
            }`}>
              {ASSIGNMENT_STATUSES[assignment.status as keyof typeof ASSIGNMENT_STATUSES] || assignment.status}
            </span>
          </div>

          <div className="mb-6">
            <p className={SECTION}>Raisons de sélection</p>
            <div className="space-y-2">
              {assignment.reasons.map((reason, index) => (
                <div key={index} className="flex items-start gap-2 bg-gray-50 rounded-lg px-3 py-2">
                  <svg className="w-4 h-4 text-[#D4AF37] mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="text-sm text-gray-700">{reason}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="mb-6">
            <p className={SECTION}>Actions</p>
            <div className="grid grid-cols-2 gap-2">
              {[
                'Confirmer',
                'Refuser',
                'Reassigner',
                'Voir le profil',
              ].map((action) => (
                <button
                  key={action}
                  disabled
                  className="px-3 py-2 text-sm font-medium rounded-lg border border-gray-200 text-gray-400 cursor-not-allowed"
                  title="Bientôt disponible"
                >
                  {action}
                </button>
              ))}
            </div>
            <p className="text-xs text-gray-400 mt-2 italic">Ces actions seront disponibles prochainement.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
