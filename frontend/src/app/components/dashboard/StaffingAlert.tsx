'use client';

interface StaffingAlertProps {
  required: number;
  assigned: number;
  remaining: number;
  roles: { role: string; remaining: number }[];
  loading?: boolean;
}

export default function StaffingAlert({ required, assigned, remaining, roles, loading = false }: StaffingAlertProps) {
  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="text-2xl">⏳</div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Postes encore à pourvoir</h3>
            <p className="text-sm text-gray-500">Chargement...</p>
          </div>
        </div>
      </div>
    );
  }
  if (remaining <= 0) {
    return (
      <div className="bg-green-50 rounded-xl border border-green-200 p-6 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="text-2xl">✅</div>
          <div>
            <h3 className="text-lg font-semibold text-green-900">Équipe complète</h3>
            <p className="text-sm text-green-700">Tous les postes sont pourvus ({assigned}/{required}).</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-amber-50 rounded-xl border border-amber-200 p-6 shadow-sm">
      <div className="flex items-start gap-3 mb-4">
        <div className="text-2xl">⚠️</div>
        <div>
          <h3 className="text-lg font-semibold text-amber-900">Postes encore à pourvoir</h3>
          <p className="text-sm text-amber-700 mt-1">
            {remaining} poste{remaining > 1 ? 's' : ''} manquant{remaining > 1 ? 's' : ''} sur {required}.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="bg-white/60 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-gray-900">{required}</p>
          <p className="text-xs text-gray-500">Requis</p>
        </div>
        <div className="bg-white/60 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-green-600">{assigned}</p>
          <p className="text-xs text-gray-500">Assignés</p>
        </div>
        <div className="bg-white/60 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-amber-600">{remaining}</p>
          <p className="text-xs text-gray-500">Manquants</p>
        </div>
      </div>

      {roles.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-amber-800 uppercase tracking-wide">Postes manquants par rôle</p>
          {roles.map((role, index) => (
            <div key={index} className="flex items-center justify-between bg-white/60 rounded-lg px-3 py-2">
              <span className="text-sm text-gray-700">{role.role}</span>
              <span className="text-sm font-semibold text-amber-700">{role.remaining} manquant{role.remaining > 1 ? 's' : ''}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
