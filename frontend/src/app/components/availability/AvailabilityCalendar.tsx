'use client';

interface AvailabilityCalendarProps {
  items: {
    id: string;
    start_datetime: string;
    end_datetime: string;
    status: string;
    conflict: boolean;
    conflict_reason?: string | null;
  }[];
}

export default function AvailabilityCalendar({ items }: AvailabilityCalendarProps) {
  const now = new Date();
  const currentMonth = now.getMonth();
  const currentYear = now.getFullYear();
  const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
  const firstDay = new Date(currentYear, currentMonth, 1).getDay();

  const days = Array.from({ length: daysInMonth }, (_, i) => i + 1);

  const getStatusForDay = (day: number) => {
    const date = new Date(currentYear, currentMonth, day);
    const matching = items.filter((item) => {
      const start = new Date(item.start_datetime);
      const end = new Date(item.end_datetime);
      return date >= start && date <= end;
    });

    if (matching.length === 0) return null;

    const hasConflict = matching.some((item) => item.conflict);
    const allAvailable = matching.every((item) => item.status === 'AVAILABLE');
    const allUnavailable = matching.every((item) => item.status === 'UNAVAILABLE');

    if (hasConflict) return { type: 'conflict', label: 'Conflit' };
    if (allAvailable) return { type: 'available', label: 'Disponible' };
    if (allUnavailable) return { type: 'unavailable', label: 'Indisponible' };
    return { type: 'mixed', label: 'Mixte' };
  };

  const styles: Record<string, string> = {
    available: 'bg-green-100 text-green-800 border-green-200',
    unavailable: 'bg-red-100 text-red-800 border-red-200',
    conflict: 'bg-orange-100 text-orange-800 border-orange-200',
    mixed: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="p-4 md:p-6 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Calendrier</h2>
        <p className="text-sm text-gray-500">
          {now.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' })}
        </p>
      </div>
      <div className="p-4 md:p-6">
        <div className="grid grid-cols-7 gap-2 mb-2">
          {['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'].map((day) => (
            <div key={day} className="text-center text-xs font-medium text-gray-500 py-2">
              {day}
            </div>
          ))}
        </div>
        <div className="grid grid-cols-7 gap-2">
          {Array.from({ length: firstDay }).map((_, i) => (
            <div key={`empty-${i}`} />
          ))}
          {days.map((day) => {
            const status = getStatusForDay(day);
            const isToday = day === now.getDate();
            return (
              <div
                key={day}
                className={`aspect-square flex items-center justify-center rounded-lg border text-sm font-medium ${
                  status ? styles[status.type] : 'border-gray-100 text-gray-400'
                } ${isToday ? 'ring-2 ring-[#D4AF37]' : ''}`}
              >
                {day}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
