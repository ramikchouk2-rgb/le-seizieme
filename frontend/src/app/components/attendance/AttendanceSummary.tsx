'use client';

interface AttendanceSummaryProps {
  summary: {
    total_expected: number;
    present: number;
    late: number;
    absent: number;
    excused: number;
    checked_out: number;
    not_checked_in: number;
    attendance_rate: number;
  };
  statusStyles: Record<string, string>;
}

export default function AttendanceSummary({ summary, statusStyles }: AttendanceSummaryProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Attendus</p>
        <p className="text-2xl font-bold text-gray-900">{summary.total_expected}</p>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Présents</p>
        <p className="text-2xl font-bold text-green-600">{summary.present}</p>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Retards</p>
        <p className="text-2xl font-bold text-yellow-600">{summary.late}</p>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Absents</p>
        <p className="text-2xl font-bold text-red-600">{summary.absent}</p>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Excusés</p>
        <p className="text-2xl font-bold text-blue-600">{summary.excused}</p>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Départs</p>
        <p className="text-2xl font-bold text-purple-600">{summary.checked_out}</p>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Taux présence</p>
        <p className="text-2xl font-bold text-gray-900">{summary.attendance_rate.toFixed(1)}%</p>
      </div>
    </div>
  );
}
