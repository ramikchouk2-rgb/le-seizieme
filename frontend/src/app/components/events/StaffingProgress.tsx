'use client';

interface StaffingProgressProps {
  requested: number;
  selected: number;
  missing: number;
  showLabel?: boolean;
}

export default function StaffingProgress({ requested, selected, missing, showLabel = true }: StaffingProgressProps) {
  const percentage = requested > 0 ? Math.round((selected / requested) * 100) : 0;

  return (
    <div className="w-full">
      {showLabel && (
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-gray-500">Staffing</span>
          <span className="text-xs font-medium text-gray-700">
            {selected} / {requested} postes
          </span>
        </div>
      )}
      <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
        <div
          className={`h-2 rounded-full transition-all duration-500 ${
            percentage === 100 ? 'bg-green-500' : percentage >= 50 ? 'bg-[#D4AF37]' : 'bg-red-500'
          }`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {missing > 0 && showLabel && (
        <p className="text-xs text-red-600 mt-1">{missing} poste{missing > 1 ? 's' : ''} manquant{missing > 1 ? 's' : ''}</p>
      )}
    </div>
  );
}
