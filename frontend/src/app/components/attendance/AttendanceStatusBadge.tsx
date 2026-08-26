'use client';

interface AttendanceStatusBadgeProps {
  status: string;
}

export default function AttendanceStatusBadge({ status }: AttendanceStatusBadgeProps) {
  const styles: Record<string, string> = {
    EXPECTED: 'bg-gray-50 text-gray-700 border-gray-200',
    PRESENT: 'bg-green-50 text-green-700 border-green-200',
    LATE: 'bg-yellow-50 text-yellow-700 border-yellow-200',
    ABSENT: 'bg-red-50 text-red-700 border-red-200',
    EXCUSED: 'bg-blue-50 text-blue-700 border-blue-200',
    LEFT: 'bg-purple-50 text-purple-700 border-purple-200',
  };

  const labels: Record<string, string> = {
    EXPECTED: 'Attendu',
    PRESENT: 'Présent',
    LATE: 'Retard',
    ABSENT: 'Absent',
    EXCUSED: 'Excusé',
    LEFT: 'Parti',
  };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${styles[status] || 'bg-gray-50 text-gray-700 border-gray-200'}`}>
      {labels[status] || status}
    </span>
  );
}
