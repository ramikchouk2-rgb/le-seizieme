'use client';

import { StaffAssignment } from '@/app/components/dashboard/types';
import { getAverageScore } from '@/app/data/event-details';

interface StaffingScoreProps {
  assignments: StaffAssignment[];
}

export default function StaffingScore({ assignments }: StaffingScoreProps) {
  const avgScore = getAverageScore(assignments);
  const percentage = Math.min(avgScore, 100);

  if (assignments.length === 0) {
    return null;
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm mb-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Qualité des recommandations</h3>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-gray-500">Score moyen</span>
        <span className="text-sm font-bold text-[#D4AF37]">{avgScore.toFixed(1)}/100</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
        <div
          className="bg-[#D4AF37] h-2 rounded-full transition-all duration-500"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <p className="text-xs text-gray-500 mt-2">
        Moyenne des scores de recommandation de {assignments.length} serveur{assignments.length > 1 ? 's' : ''}.
      </p>
    </div>
  );
}
