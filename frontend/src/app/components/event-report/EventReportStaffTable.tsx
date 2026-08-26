'use client';

interface EventReportStaffTableProps {
  staff: {
    server_id: string;
    name: string;
    role: string;
    assignment_status: string;
    attendance_status?: string | null;
    check_in_at?: string | null;
    check_out_at?: string | null;
    completion_points: number;
    performance_points: number;
    total_points: number;
    evaluation_score?: number | null;
    evaluation_comment?: string | null;
    evaluated?: boolean;
  }[];
}

export default function EventReportStaffTable({ staff }: EventReportStaffTableProps) {
  const formatDateTime = (dateStr?: string | null) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  };

  const statusStyles: Record<string, string> = {
    CONFIRMED: 'bg-green-50 text-green-700 border-green-200',
    PROPOSED: 'bg-yellow-50 text-yellow-700 border-yellow-200',
    DECLINED: 'bg-red-50 text-red-700 border-red-200',
    CANCELLED: 'bg-gray-50 text-gray-700 border-gray-200',
    COMPLETED: 'bg-blue-50 text-blue-700 border-blue-200',
  };

  const attendanceStyles: Record<string, string> = {
    PRESENT: 'bg-green-50 text-green-700 border-green-200',
    LATE: 'bg-yellow-50 text-yellow-700 border-yellow-200',
    ABSENT: 'bg-red-50 text-red-700 border-red-200',
    EXCUSED: 'bg-blue-50 text-blue-700 border-blue-200',
    EXPECTED: 'bg-gray-50 text-gray-700 border-gray-200',
    LEFT: 'bg-purple-50 text-purple-700 border-purple-200',
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="p-4 md:p-6 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Performance du personnel</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Serveur</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider hidden md:table-cell">Rôle</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Affectation</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Présence</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider hidden md:table-cell">Arrivée</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider hidden md:table-cell">Départ</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Évaluation</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Points compl.</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Points perf.</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Total</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {staff.map((item) => (
              <tr key={item.server_id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-sm font-medium text-gray-900">{item.name}</td>
                <td className="px-4 py-3 text-sm text-gray-700 hidden md:table-cell">{item.role}</td>
                <td className="px-4 py-3 text-sm">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${statusStyles[item.assignment_status] || 'bg-gray-50 text-gray-700 border-gray-200'}`}>
                    {item.assignment_status}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm">
                  {item.attendance_status ? (
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${attendanceStyles[item.attendance_status] || 'bg-gray-50 text-gray-700 border-gray-200'}`}>
                      {item.attendance_status}
                    </span>
                  ) : (
                    <span className="text-xs text-gray-400">-</span>
                  )}
                </td>
                <td className="px-4 py-3 text-sm text-gray-700 hidden md:table-cell">{formatDateTime(item.check_in_at)}</td>
                <td className="px-4 py-3 text-sm text-gray-700 hidden md:table-cell">{formatDateTime(item.check_out_at)}</td>
                <td className="px-4 py-3 text-sm text-gray-900 font-medium">
                  {item.evaluated && item.evaluation_score !== null && item.evaluation_score !== undefined
                    ? item.evaluation_score.toFixed(1)
                    : '-'}
                </td>
                <td className="px-4 py-3 text-sm text-gray-900 font-medium">{item.completion_points}</td>
                <td className="px-4 py-3 text-sm text-gray-900 font-medium">{item.performance_points}</td>
                <td className="px-4 py-3 text-sm font-bold text-[#D4AF37]">{item.total_points}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
