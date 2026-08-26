'use client';

interface ServerRankingItem {
  server_name: string;
  total_points: number;
  rank: number;
}

interface TopServersProps {
  rankings: ServerRankingItem[];
  loading?: boolean;
}

export default function TopServers({ rankings, loading = false }: TopServersProps) {
  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Serveurs du mois</h3>
        <p className="text-gray-500 text-sm">Chargement...</p>
      </div>
    );
  }

  if (!rankings || rankings.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Serveurs du mois</h3>
        <p className="text-gray-500 text-sm">Aucun classement disponible.</p>
      </div>
    );
  }

  const maxPoints = Math.max(...rankings.map((r) => r.total_points));

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Serveurs du mois</h3>
      <div className="space-y-3">
        {rankings.slice(0, 5).map((server, index) => {
          const percentage = maxPoints > 0 ? (server.total_points / maxPoints) * 100 : 0;
          return (
            <div key={server.server_name} className="flex items-center gap-3">
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                index === 0 ? 'bg-[#D4AF37] text-white' :
                index === 1 ? 'bg-gray-300 text-gray-700' :
                index === 2 ? 'bg-amber-200 text-amber-800' :
                'bg-gray-100 text-gray-600'
              }`}>
                {server.rank}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1">
                  <p className="text-sm font-medium text-gray-900 truncate">{server.server_name}</p>
                  <p className="text-sm font-bold text-[#D4AF37]">{server.total_points} pts</p>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-1.5">
                  <div
                    className="bg-[#D4AF37] h-1.5 rounded-full transition-all duration-500"
                    style={{ width: `${percentage}%` }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
