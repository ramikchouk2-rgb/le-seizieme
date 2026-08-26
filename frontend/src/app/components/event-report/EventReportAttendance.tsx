'use client';

interface EventReportAttendanceProps {
  attendance: {
    available: boolean;
    expected?: number;
    present?: number;
    late?: number;
    absent?: number;
    attendance_rate?: number;
  };
}

export default function EventReportAttendance({ attendance }: EventReportAttendanceProps) {
  if (!attendance.available) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Présence</h2>
        <p className="text-sm text-gray-500">Données de présence indisponibles pour cet événement.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Présence</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Attendus</p>
          <p className="text-2xl font-bold text-gray-900">{attendance.expected ?? 0}</p>
        </div>
        <div className="bg-green-50 rounded-lg p-4 border border-green-200">
          <p className="text-xs text-green-600 uppercase tracking-wider mb-1">Présents</p>
          <p className="text-2xl font-bold text-green-600">{attendance.present ?? 0}</p>
        </div>
        <div className="bg-yellow-50 rounded-lg p-4 border border-yellow-200">
          <p className="text-xs text-yellow-600 uppercase tracking-wider mb-1">Retards</p>
          <p className="text-2xl font-bold text-yellow-600">{attendance.late ?? 0}</p>
        </div>
        <div className="bg-red-50 rounded-lg p-4 border border-red-200">
          <p className="text-xs text-red-600 uppercase tracking-wider mb-1">Absents</p>
          <p className="text-2xl font-bold text-red-600">{attendance.absent ?? 0}</p>
        </div>
      </div>
      <div className="mt-4 bg-gray-50 rounded-lg p-4 border border-gray-200">
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Taux de présence</p>
        <p className="text-2xl font-bold text-gray-900">{(attendance.attendance_rate ?? 0).toFixed(1)}%</p>
      </div>
    </div>
  );
}
