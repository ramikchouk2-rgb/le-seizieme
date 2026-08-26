'use client';

interface EventReportKpiCardsProps {
  kpis: {
    staffing_rate: number;
    attendance_rate: number;
    requirement_fulfillment_rate: number;
    transport_coverage_rate: number;
    evaluation_coverage?: number;
  };
  totals: {
    totalStaff: number;
    totalPoints: number;
  };
}

export default function EventReportKpiCards({ kpis, totals }: EventReportKpiCardsProps) {
  const cards = [
    { label: 'Taux de staffing', value: `${kpis.staffing_rate}%`, color: 'text-blue-600' },
    { label: 'Taux de présence', value: `${kpis.attendance_rate}%`, color: 'text-green-600' },
    { label: 'Satisfaction besoins', value: `${kpis.requirement_fulfillment_rate}%`, color: 'text-purple-600' },
    { label: 'Couverture transport', value: `${kpis.transport_coverage_rate}%`, color: 'text-orange-600' },
    { label: 'Couverture évaluation', value: `${kpis.evaluation_coverage ?? 0}%`, color: 'text-pink-600' },
    { label: 'Personnel total', value: totals.totalStaff.toString(), color: 'text-gray-900' },
    { label: 'Points totaux', value: totals.totalPoints.toString(), color: 'text-[#D4AF37]' },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-7 gap-4">
      {cards.map((card) => (
        <div key={card.label} className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{card.label}</p>
          <p className={`text-2xl font-bold ${card.color}`}>{card.value}</p>
        </div>
      ))}
    </div>
  );
}
