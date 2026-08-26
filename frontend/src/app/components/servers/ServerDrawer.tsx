'use client';

import { useFocusTrap } from '@/app/components/ui/FocusTrap';
import { ServerListItem, ServerProfile } from '@/app/lib/api';
import Link from 'next/link';

interface ServerDrawerProps {
  server: ServerListItem | null;
  profile: ServerProfile | null;
  loading: boolean;
  onClose: () => void;
}

const SKILL_BADGE = 'bg-blue-50 text-blue-700 border-blue-200';
const SECTION = 'text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2';

export default function ServerDrawer({ server, profile, loading, onClose }: ServerDrawerProps) {
  const containerRef = useFocusTrap({ onClose, closeOnEscape: true, restoreFocus: true });

  if (!server) return null;

  if (loading) {
    return (
      <div className="fixed inset-0 z-50">
        <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
        <div ref={containerRef} className="absolute right-0 top-0 h-full w-full max-w-xl bg-white shadow-2xl overflow-y-auto">
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-gray-900">Profil serveur</h2>
              <button
                onClick={onClose}
                aria-label="Fermer"
                className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <p className="text-sm text-gray-500">Chargement du profil...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="fixed inset-0 z-50">
        <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
        <div ref={containerRef} className="absolute right-0 top-0 h-full w-full max-w-xl bg-white shadow-2xl overflow-y-auto">
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-gray-900">Profil serveur</h2>
              <button
                onClick={onClose}
                aria-label="Fermer"
                className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <p className="text-sm text-red-600">Impossible de charger le profil du serveur.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div ref={containerRef} className="absolute right-0 top-0 h-full w-full max-w-xl bg-white shadow-2xl overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-gray-900">Profil serveur</h2>
            <button
              onClick={onClose}
              aria-label="Fermer"
              className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="flex items-center gap-4 mb-6">
            <div className="w-16 h-16 rounded-full bg-[#D4AF37]/10 flex items-center justify-center text-[#D4AF37] text-xl font-bold">
              {server.first_name[0]}{server.last_name[0]}
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                {server.first_name} {server.last_name}
              </h3>
              <p className="text-sm text-gray-500">
                {server.city} • {server.years_experience} ans d'expérience
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 mb-6">
            <div className="bg-gray-50 rounded-lg p-3">
              <p className={SECTION}>Genre</p>
              <p className="text-sm text-gray-900">{server.gender === 'MALE' ? 'Homme' : 'Femme'}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className={SECTION}>Profil</p>
              <p className="text-sm text-gray-900">
                {server.worker_type === 'HARD_WORKER' ? 'Profil performant' : server.worker_type === 'BALANCED' ? 'Profil équilibré' : server.worker_type === 'SOFT_WORKER' ? 'Profil souple' : server.worker_type}
              </p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className={SECTION}>Disponibilité</p>
              <p className={`text-sm font-medium ${server.availability_status === 'AVAILABLE' ? 'text-green-600' : 'text-red-600'}`}>
                {server.availability_status === 'AVAILABLE' ? 'Disponible' : 'Indisponible'}
              </p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className={SECTION}>Classement mensuel</p>
              <p className="text-sm text-gray-900">#{profile.points.rank ?? '—'} • {profile.points.current_month_points} pts</p>
            </div>
          </div>

          <div className="mb-6">
            <p className={SECTION}>Compétences</p>
            <div className="space-y-2">
              {profile.skills.map((skill: { name: string; level: number }) => (
                <div key={skill.name} className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2">
                  <span className="text-sm text-gray-700">{skill.name}</span>
                  <div className="flex items-center gap-2">
                    <div className="w-24 bg-gray-200 rounded-full h-1.5">
                      <div
                        className="bg-[#D4AF37] h-1.5 rounded-full"
                        style={{ width: `${(skill.level / 10) * 100}%` }}
                      />
                    </div>
                    <span className="text-xs font-medium text-gray-700 w-8 text-right">{skill.level}/10</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mb-6">
            <p className={SECTION}>Véhicule</p>
            {profile.vehicle ? (
              <div className="bg-gray-50 rounded-lg p-3 space-y-1">
                <p className="text-sm text-gray-900">
                  {profile.vehicle.brand} {profile.vehicle.model}
                </p>
                <p className="text-xs text-gray-500">
                  {profile.vehicle.seats_total} places •{' '}
                  {profile.vehicle.can_transport_coworkers ? 'Transport collègues ✅' : 'Sans transport'}
                  {' '}• {profile.vehicle.is_active ? 'Actif' : 'Inactif'}
                </p>
              </div>
            ) : (
              <p className="text-sm text-gray-500">Aucun véhicule enregistré</p>
            )}
          </div>

          <div className="mb-6">
            <p className={SECTION}>Localisation</p>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-sm text-gray-900">
                {profile.location.city}, {profile.location.area}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                {profile.location.is_verified ? (
                  <span className="text-green-600">Localisation vérifiée ✅</span>
                ) : (
                  <span className="text-gray-400">Localisation non vérifiée</span>
                )}
              </p>
            </div>
          </div>

          <div className="mb-6">
            <p className={SECTION}>Disponibilités à venir</p>
            <div className="space-y-2">
              {profile.availability.slice(0, 3).map((slot: { id: string; start_datetime: string; end_datetime: string; status: string }) => (
                <div key={slot.id} className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2">
                  <span className="text-sm text-gray-700">
                    {new Date(slot.start_datetime).toLocaleDateString('fr-FR')} — {new Date(slot.end_datetime).toLocaleDateString('fr-FR')}
                  </span>
                  <span className={`text-xs font-medium ${slot.status === 'AVAILABLE' ? 'text-green-600' : 'text-red-600'}`}>
                    {slot.status === 'AVAILABLE' ? 'Disponible' : 'Indisponible'}
                  </span>
                </div>
              ))}
            </div>
            {server && (
              <Link
                href={`/dashboard/servers/${server.id}/availability`}
                className="inline-flex items-center mt-2 text-sm text-[#D4AF37] hover:text-[#B8941E] font-medium"
              >
                Gérer les disponibilités →
              </Link>
            )}
          </div>

          <div className="mb-6">
            <p className={SECTION}>Gamification</p>
            {profile.points && (
              <div className="bg-gray-50 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-700">Points mensuels</span>
                  <span className="text-sm font-bold text-[#D4AF37]">{profile.points.current_month_points} pts</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-700">Classement</span>
                  <span className="text-sm font-medium text-gray-900">#{profile.points.rank ?? '—'}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
