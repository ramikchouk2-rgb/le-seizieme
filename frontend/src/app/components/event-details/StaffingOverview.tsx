'use client';

import { EventStaffing } from '@/app/components/dashboard/types';

interface StaffingOverviewProps {
  staffing: EventStaffing;
}

export default function StaffingOverview({ staffing }: StaffingOverviewProps) {
  const isComplete = staffing.missing === 0;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm mb-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Staffing global</h3>
      
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-gray-500">Progression</span>
        <span className="text-sm font-medium text-gray-700">
          {staffing.selected} / {staffing.requested} postes couverts
        </span>
      </div>
      
      <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden mb-4">
        <div
          className={`h-3 rounded-full transition-all duration-500 ${
            staffing.percentage === 100 ? 'bg-green-500' : staffing.percentage >= 50 ? 'bg-[#D4AF37]' : 'bg-red-500'
          }`}
          style={{ width: `${staffing.percentage}%` }}
        />
      </div>

      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-gray-900">{staffing.requested}</p>
          <p className="text-xs text-gray-500">Requis</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-green-600">{staffing.selected}</p>
          <p className="text-xs text-gray-500">Affectés / recommandés</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-red-600">{staffing.missing}</p>
          <p className="text-xs text-gray-500">Manquants</p>
        </div>
      </div>

      <div className={`rounded-lg p-3 ${isComplete ? 'bg-green-50 border border-green-200' : 'bg-amber-50 border border-amber-200'}`}>
        <p className={`text-sm font-medium ${isComplete ? 'text-green-800' : 'text-amber-800'}`}>
          {isComplete ? 'Le staffing est complet.' : 'Le staffing est incomplet.'}
        </p>
      </div>
    </div>
  );
}
