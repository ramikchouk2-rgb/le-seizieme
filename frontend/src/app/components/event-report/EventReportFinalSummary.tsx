'use client';

interface EventReportFinalSummaryProps {
  status: string;
  isFinal: boolean;
  kpis: {
    staffing_rate: number;
    attendance_rate: number;
    requirement_fulfillment_rate: number;
    transport_coverage_rate: number;
  };
}

export default function EventReportFinalSummary({ status, isFinal, kpis }: EventReportFinalSummaryProps) {
  if (status === "CANCELLED") {
    return (
      <div className="bg-red-50 rounded-xl border border-red-200 p-6 shadow-sm">
        <div className="flex items-start gap-3">
          <span className="text-2xl">⚠️</span>
          <div>
            <h3 className="text-lg font-semibold text-red-900">Événement annulé</h3>
            <p className="text-sm text-red-700 mt-1">
              Cet événement a été annulé. Aucun rapport final de cloture n'est disponible.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (!isFinal) {
    return (
      <div className="bg-yellow-50 rounded-xl border border-yellow-200 p-6 shadow-sm">
        <div className="flex items-start gap-3">
          <span className="text-2xl">⏳</span>
          <div>
            <h3 className="text-lg font-semibold text-yellow-900">Événement en cours</h3>
            <p className="text-sm text-yellow-700 mt-1">
              Le rapport final sera disponible une fois l'événement terminé.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const allGood = kpis.staffing_rate >= 90 && kpis.attendance_rate >= 80 && kpis.requirement_fulfillment_rate >= 90 && kpis.transport_coverage_rate >= 90;

  return (
    <div className={`rounded-xl border p-6 shadow-sm ${allGood ? 'bg-green-50 border-green-200' : 'bg-yellow-50 border-yellow-200'}`}>
      <div className="flex items-start gap-3">
        <span className="text-2xl">{allGood ? '✅' : '⚠️'}</span>
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            {allGood ? 'Événement cloturé avec succès' : 'Événement cloturé avec réserves'}
          </h3>
          <p className="text-sm text-gray-700 mt-1">
            {allGood
              ? "Tous les indicateurs sont au vert. L'événement s'est déroulé dans de bonnes conditions."
              : "Certains indicateurs nécessitent une attention particulière pour les prochains événements."}
          </p>
          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-white rounded-lg p-3 border border-gray-200">
              <p className="text-xs text-gray-500">Staffing</p>
              <p className="text-lg font-bold text-gray-900">{kpis.staffing_rate}%</p>
            </div>
            <div className="bg-white rounded-lg p-3 border border-gray-200">
              <p className="text-xs text-gray-500">Présence</p>
              <p className="text-lg font-bold text-gray-900">{kpis.attendance_rate}%</p>
            </div>
            <div className="bg-white rounded-lg p-3 border border-gray-200">
              <p className="text-xs text-gray-500">Besoins</p>
              <p className="text-lg font-bold text-gray-900">{kpis.requirement_fulfillment_rate}%</p>
            </div>
            <div className="bg-white rounded-lg p-3 border border-gray-200">
              <p className="text-xs text-gray-500">Transport</p>
              <p className="text-lg font-bold text-gray-900">{kpis.transport_coverage_rate}%</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
