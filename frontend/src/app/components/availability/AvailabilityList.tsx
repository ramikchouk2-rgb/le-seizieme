'use client';

import { AvailabilityResponse } from '@/app/lib/api';

interface AvailabilityListProps {
  items: AvailabilityResponse[];
  onEdit: (item: AvailabilityResponse) => void;
  onDelete: (item: AvailabilityResponse) => void;
  statusStyles: Record<string, string>;
}

export default function AvailabilityList({ items, onEdit, onDelete, statusStyles }: AvailabilityListProps) {
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' });
  };

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  };

  const getDuration = (start: string, end: string) => {
    const startDate = new Date(start);
    const endDate = new Date(end);
    const hours = (endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60);
    return `${hours}h`;
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="p-4 md:p-6 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Liste des disponibilités</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Date</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider hidden md:table-cell">Début</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider hidden md:table-cell">Fin</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Durée</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Statut</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {items.map((item) => (
              <tr key={item.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-sm text-gray-900">{formatDate(item.start_datetime)}</td>
                <td className="px-4 py-3 text-sm text-gray-700 hidden md:table-cell">{formatTime(item.start_datetime)}</td>
                <td className="px-4 py-3 text-sm text-gray-700 hidden md:table-cell">{formatTime(item.end_datetime)}</td>
                <td className="px-4 py-3 text-sm text-gray-700">{getDuration(item.start_datetime, item.end_datetime)}</td>
                <td className="px-4 py-3 text-sm">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${statusStyles[item.status] || 'bg-gray-50 text-gray-700 border-gray-200'}`}>
                    {item.status === 'AVAILABLE' ? 'Disponible' : item.status === 'UNAVAILABLE' ? 'Indisponible' : 'Réservé'}
                  </span>
                  {item.conflict && (
                    <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-orange-50 text-orange-700 border border-orange-200">
                      Conflit
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-sm">
                  <div className="flex gap-2">
                    <button
                      onClick={() => onEdit(item)}
                      className="text-[#D4AF37] hover:text-[#B8941E] font-medium"
                    >
                      Modifier
                    </button>
                    <button
                      onClick={() => onDelete(item)}
                      className="text-red-600 hover:text-red-700 font-medium"
                    >
                      Supprimer
                    </button>
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
