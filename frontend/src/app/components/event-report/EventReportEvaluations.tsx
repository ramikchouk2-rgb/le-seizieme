'use client';

interface EventReportEvaluationsProps {
  evaluationSummary: {
    total_evaluated: number;
    total_confirmed: number;
    evaluation_coverage: number;
    average_score: number | null;
    highest_score: number | null;
    lowest_score: number | null;
    excellent_count: number;
    good_count: number;
    average_count: number;
    needs_improvement_count: number;
  };
}

export default function EventReportEvaluations({ evaluationSummary }: EventReportEvaluationsProps) {
  const hasEvaluations = evaluationSummary.total_evaluated > 0;

  if (!hasEvaluations) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Évaluations</h2>
        <p className="text-sm text-gray-500">Aucune évaluation disponible pour cet événement.</p>
      </div>
    );
  }

  const score = evaluationSummary.average_score;
  let scoreColor = 'text-gray-900';
  if (score !== null) {
    if (score >= 9) scoreColor = 'text-green-600';
    else if (score >= 7) scoreColor = 'text-blue-600';
    else if (score >= 5) scoreColor = 'text-yellow-600';
    else scoreColor = 'text-red-600';
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="p-4 md:p-6 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Évaluations</h2>
      </div>
      <div className="p-4 md:p-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Évalués</p>
            <p className="text-2xl font-bold text-gray-900">
              {evaluationSummary.total_evaluated} / {evaluationSummary.total_confirmed}
            </p>
          </div>
          <div className="bg-green-50 rounded-lg p-4 border border-green-200">
            <p className="text-xs text-green-600 uppercase tracking-wider mb-1">Excellents (9-10)</p>
            <p className="text-2xl font-bold text-green-600">{evaluationSummary.excellent_count}</p>
          </div>
          <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
            <p className="text-xs text-blue-600 uppercase tracking-wider mb-1">Bons (7-8)</p>
            <p className="text-2xl font-bold text-blue-600">{evaluationSummary.good_count}</p>
          </div>
          <div className="bg-yellow-50 rounded-lg p-4 border border-yellow-200">
            <p className="text-xs text-yellow-600 uppercase tracking-wider mb-1">Moyens (5-6)</p>
            <p className="text-2xl font-bold text-yellow-600">{evaluationSummary.average_count}</p>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-red-50 rounded-lg p-4 border border-red-200">
            <p className="text-xs text-red-600 uppercase tracking-wider mb-1">À améliorer (1-4)</p>
            <p className="text-2xl font-bold text-red-600">{evaluationSummary.needs_improvement_count}</p>
          </div>
          <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
            <p className="text-xs text-purple-600 uppercase tracking-wider mb-1">Score moyen</p>
            <p className={`text-2xl font-bold ${scoreColor}`}>
              {score !== null ? score.toFixed(1) : '-'}
            </p>
          </div>
          <div className="bg-green-50 rounded-lg p-4 border border-green-200">
            <p className="text-xs text-green-600 uppercase tracking-wider mb-1">Meilleur score</p>
            <p className="text-2xl font-bold text-green-600">
              {evaluationSummary.highest_score !== null ? evaluationSummary.highest_score.toFixed(1) : '-'}
            </p>
          </div>
          <div className="bg-red-50 rounded-lg p-4 border border-red-200">
            <p className="text-xs text-red-600 uppercase tracking-wider mb-1">Score le plus bas</p>
            <p className="text-2xl font-bold text-red-600">
              {evaluationSummary.lowest_score !== null ? evaluationSummary.lowest_score.toFixed(1) : '-'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
