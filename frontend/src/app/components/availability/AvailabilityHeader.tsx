'use client';

interface AvailabilityHeaderProps {
  serverName?: string;
  serverId: string;
}

export default function AvailabilityHeader({ serverName, serverId }: AvailabilityHeaderProps) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          {serverName || 'Serveur'}
        </h1>
        <p className="text-sm text-gray-500">ID: {serverId}</p>
      </div>
    </div>
  );
}
