'use client';

interface AvailabilityConflictAlertProps {
  reason?: string | null;
  type?: 'overlap' | 'event' | 'server';
}

export default function AvailabilityConflictAlert({ reason, type = 'overlap' }: AvailabilityConflictAlertProps) {
  if (!reason) return null;

  const messages: Record<string, string> = {
    overlap: 'Cette période chevauche une disponibilité existante.',
    event: 'Cette période entre en conflit avec un événement confirmé ou en cours.',
    server: 'Le serveur est inactif.',
  };

  return (
    <div className="p-3 rounded-lg bg-orange-50 text-orange-700 text-sm font-medium border border-orange-200">
      ⚠ {messages[type] || reason}
    </div>
  );
}
