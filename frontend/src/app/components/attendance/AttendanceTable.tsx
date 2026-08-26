'use client';

interface AttendanceItem {
  id: string;
  event_staff_id: string;
  server_id: string;
  server_name: string;
  role: string;
  status: string;
  check_in_at?: string | null;
  check_out_at?: string | null;
  note?: string | null;
}

interface AttendanceTableProps {
  items: AttendanceItem[];
  statusStyles: Record<string, string>;
  onCheckIn: (item: AttendanceItem) => void;
  onCheckOut: (item: AttendanceItem) => void;
  onUpdate: (item: AttendanceItem) => void;
}

export default function AttendanceTable({ items, statusStyles, onCheckIn, onCheckOut, onUpdate }: AttendanceTableProps) {
  const formatDateTime = (dateStr?: string | null) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  };

  const canCheckIn = (status: string) => status === 'EXPECTED' || status === 'LATE' || status === 'ABSENT' || status === 'EXCUSED';
  const canCheckOut = (status: string) => status === 'PRESENT' || status === 'LATE';
  const canUpdate = (status: string) => status !== 'LEFT';

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="p-4 md:p-6 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Liste des présences</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Serveur</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider hidden md:table-cell">Rôle</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Statut</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider hidden md:table-cell">Arrivée</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider hidden md:table-cell">Départ</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {items.map((item) => (
              <tr key={item.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-sm text-gray-900">{item.server_name}</td>
                <td className="px-4 py-3 text-sm text-gray-700 hidden md:table-cell">{item.role}</td>
                <td className="px-4 py-3 text-sm">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${statusStyles[item.status] || 'bg-gray-50 text-gray-700 border-gray-200'}`}>
                    {item.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-gray-700 hidden md:table-cell">{formatDateTime(item.check_in_at)}</td>
                <td className="px-4 py-3 text-sm text-gray-700 hidden md:table-cell">{formatDateTime(item.check_out_at)}</td>
                <td className="px-4 py-3 text-sm">
                  <div className="flex gap-2">
                    {canCheckIn(item.status) && (
                      <button onClick={() => onCheckIn(item)} className="text-green-600 hover:text-green-700 font-medium">
                        Check-in
                      </button>
                    )}
                    {canCheckOut(item.status) && (
                      <button onClick={() => onCheckOut(item)} className="text-blue-600 hover:text-blue-700 font-medium">
                        Check-out
                      </button>
                    )}
                    {canUpdate(item.status) && (
                      <button onClick={() => onUpdate(item)} className="text-[#D4AF37] hover:text-[#B8941E] font-medium">
                        Corriger
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
