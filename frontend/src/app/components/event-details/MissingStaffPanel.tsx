'use client';

import { EventDetailData } from '@/app/components/dashboard/types';

interface MissingStaffPanelProps {
  requirements: EventDetailData['requirements_detail'];
}

export default function MissingStaffPanel({ requirements }: MissingStaffPanelProps) {
  const missingRequirements = requirements.filter((r) => r.missing > 0);
  const totalMissing = missingRequirements.reduce((sum, r) => sum + r.missing, 0);

  if (totalMissing === 0) {
    return (
      <div className="bg-green-50 rounded-xl border border-green-200 p-6 shadow-sm mb-6">
        <div className="flex items-center gap-3">
          <div className="text-2xl">✅</div>
          <div>
            <h3 className="text-lg font-semibold text-green-900">Tous les postes sont couverts.</h3>
            <p className="text-sm text-green-700 mt-1">Le staffing est complet pour cet événement.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-amber-50 rounded-xl border border-amber-200 p-6 shadow-sm mb-6">
      <div className="flex items-start gap-3 mb-4">
        <div className="text-2xl">⚠️</div>
        <div>
          <h3 className="text-lg font-semibold text-amber-900">Postes manquants</h3>
          <p className="text-sm text-amber-700 mt-1">
            {totalMissing} poste{totalMissing > 1 ? 's' : ''} manquant{totalMissing > 1 ? 's' : ''} au total.
          </p>
        </div>
      </div>

      <div className="space-y-2 mb-4">
        {missingRequirements.map((req, index) => (
          <div key={index} className="flex items-center justify-between bg-white/60 rounded-lg px-3 py-2">
            <span className="text-sm text-gray-700">
              {req.role_name}
              {req.required_gender && (
                <span className="text-gray-500 ml-1">
                  — {req.required_gender === 'MALE' ? 'Hommes' : 'Femmes'}
                </span>
              )}
            </span>
            <span className="text-sm font-semibold text-amber-700">{req.missing} manquant{req.missing > 1 ? 's' : ''}</span>
          </div>
        ))}
      </div>

      <div className="bg-white/60 rounded-lg p-3">
        <p className="text-xs text-amber-800">
          Ces postes nécessitent une nouvelle recommandation ou une campagne d'offres.
        </p>
      </div>
    </div>
  );
}
