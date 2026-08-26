'use client';

interface EventReportGamificationProps {
  gamification: {
    completion_points: number;
    performance_points: number;
    total_points: number;
  };
}

export default function EventReportGamification({ gamification }: EventReportGamificationProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Gamification</h2>
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Points complétion</p>
          <p className="text-2xl font-bold text-gray-900">{gamification.completion_points}</p>
        </div>
        <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
          <p className="text-xs text-blue-600 uppercase tracking-wider mb-1">Points performance</p>
          <p className="text-2xl font-bold text-blue-600">{gamification.performance_points}</p>
        </div>
        <div className="bg-[#D4AF37]/10 rounded-lg p-4 border border-[#D4AF37]/20">
          <p className="text-xs text-[#D4AF37] uppercase tracking-wider mb-1">Total points</p>
          <p className="text-2xl font-bold text-[#D4AF37]">{gamification.total_points}</p>
        </div>
      </div>
    </div>
  );
}
