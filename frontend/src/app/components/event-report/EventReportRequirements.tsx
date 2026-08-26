'use client';

interface EventReportRequirementsProps {
  requirements: {
    requirement_id: string;
    role: string;
    requested: number;
    assigned: number;
    confirmed: number;
    fulfilled: boolean;
    status: string;
  }[];
}

export default function EventReportRequirements({ requirements }: EventReportRequirementsProps) {
  const statusStyles: Record<string, string> = {
    COMPLET: 'bg-green-50 text-green-700 border-green-200',
    PARTIEL: 'bg-yellow-50 text-yellow-700 border-yellow-200',
    CRITIQUE: 'bg-red-50 text-red-700 border-red-200',
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="p-4 md:p-6 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Besoins et couverture</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Rôle</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Demandé</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Assigné</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Confirmé</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Statut</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {requirements.map((req) => (
              <tr key={req.requirement_id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-sm font-medium text-gray-900">{req.role}</td>
                <td className="px-4 py-3 text-sm text-gray-700">{req.requested}</td>
                <td className="px-4 py-3 text-sm text-gray-700">{req.assigned}</td>
                <td className="px-4 py-3 text-sm text-gray-700">{req.confirmed}</td>
                <td className="px-4 py-3 text-sm">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${statusStyles[req.status] || 'bg-gray-50 text-gray-700 border-gray-200'}`}>
                    {req.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
