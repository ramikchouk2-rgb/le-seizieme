'use client';

interface EventReportTransportProps {
  transport: {
    total_groups: number;
    confirmed_groups: number;
    total_passengers: number;
    assigned_passengers: number;
    unassigned_passengers: number;
  };
}

export default function EventReportTransport({ transport }: EventReportTransportProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Transport</h2>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Groupes</p>
          <p className="text-2xl font-bold text-gray-900">{transport.total_groups}</p>
        </div>
        <div className="bg-green-50 rounded-lg p-4 border border-green-200">
          <p className="text-xs text-green-600 uppercase tracking-wider mb-1">Confirmés</p>
          <p className="text-2xl font-bold text-green-600">{transport.confirmed_groups}</p>
        </div>
        <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
          <p className="text-xs text-blue-600 uppercase tracking-wider mb-1">Passagers</p>
          <p className="text-2xl font-bold text-blue-600">{transport.total_passengers}</p>
        </div>
        <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
          <p className="text-xs text-purple-600 uppercase tracking-wider mb-1">Assignés</p>
          <p className="text-2xl font-bold text-purple-600">{transport.assigned_passengers}</p>
        </div>
        <div className="bg-red-50 rounded-lg p-4 border border-red-200">
          <p className="text-xs text-red-600 uppercase tracking-wider mb-1">Non assignés</p>
          <p className="text-2xl font-bold text-red-600">{transport.unassigned_passengers}</p>
        </div>
      </div>
    </div>
  );
}
