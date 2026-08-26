'use client';

interface EventReportHeaderProps {
  eventName: string;
  city: string;
  date: string;
  status: string;
  isFinal: boolean;
}

export default function EventReportHeader({ eventName, city, date, status, isFinal }: EventReportHeaderProps) {
  const statusStyles: Record<string, string> = {
    COMPLETED: 'bg-green-50 text-green-700 border-green-200',
    CANCELLED: 'bg-red-50 text-red-700 border-red-200',
    IN_PROGRESS: 'bg-purple-50 text-purple-700 border-purple-200',
    CONFIRMED: 'bg-blue-50 text-blue-700 border-blue-200',
    STAFFING: 'bg-yellow-50 text-yellow-700 border-yellow-200',
    PLANNED: 'bg-gray-50 text-gray-700 border-gray-200',
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{eventName}</h1>
          <p className="text-sm text-gray-500 mt-1">
            {city} {date && <span>• {date}</span>}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${statusStyles[status] || 'bg-gray-50 text-gray-700 border-gray-200'}`}>
            {status}
          </span>
          {isFinal && (
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-[#D4AF37]/10 text-[#D4AF37] border border-[#D4AF37]/20">
              Rapport final
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
