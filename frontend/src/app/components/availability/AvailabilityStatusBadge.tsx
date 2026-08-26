'use client';

interface AvailabilityStatusBadgeProps {
  status: string;
  conflict?: boolean;
}

export default function AvailabilityStatusBadge({ status, conflict }: AvailabilityStatusBadgeProps) {
  const styles: Record<string, string> = {
    AVAILABLE: 'bg-green-50 text-green-700 border-green-200',
    UNAVAILABLE: 'bg-red-50 text-red-700 border-red-200',
    RESERVED: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  };

  const labels: Record<string, string> = {
    AVAILABLE: 'Disponible',
    UNAVAILABLE: 'Indisponible',
    RESERVED: 'Réservé',
  };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${styles[status] || 'bg-gray-50 text-gray-700 border-gray-200'}`}>
      {labels[status] || status}
      {conflict && (
        <span className="ml-1 inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-orange-50 text-orange-700 border border-orange-200">
          Conflit
        </span>
      )}
    </span>
  );
}
