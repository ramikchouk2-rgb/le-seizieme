'use client';

import { useParams, useRouter } from 'next/navigation';
import { useState } from 'react';
import Header from '@/app/components/dashboard/Header';
import { useServer } from '@/app/lib/hooks';
import { useAnnouncer } from '@/app/components/ui/Announcer';
import { Spinner } from '@/app/lib/loading';
import Link from 'next/link';

const SECTION = 'text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2';

export default function ServerProfilePage() {
  const params = useParams();
  const router = useRouter();
  const serverId = params.serverId as string;
  const { announceSuccess, announceError } = useAnnouncer();
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deactivating, setDeactivating] = useState(false);

  const { data, isLoading, error, refetch } = useServer(serverId);

  const handleDeactivate = async () => {
    setDeactivating(true);
    try {
      // This would need a deactivate endpoint, for now we just update is_active
      // In a full implementation, this would call an update endpoint with is_active: false
      await fetch(`/api/servers/${serverId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: false }),
      });
      announceSuccess('Serveur désactivé avec succès.');
      router.push('/dashboard/servers');
    } catch {
      announceError('Impossible de désactiver le serveur.');
    } finally {
      setDeactivating(false);
      setShowDeleteDialog(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Spinner size="lg" className="mx-auto mb-4 text-[#D4AF37]" />
          <p className="text-gray-500 text-sm">Chargement du profil...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header title="Profil serveur" />
        <main className="p-8">
          <div className="max-w-7xl mx-auto">
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm">
              <p className="text-gray-500 text-sm mb-4">{error?.message || 'Serveur introuvable'}</p>
              <button
                onClick={() => refetch()}
                className="inline-flex items-center px-4 py-2 bg-[#D4AF37] text-white text-sm font-medium rounded-lg hover:bg-[#B8941E] transition-colors"
              >
                Réessayer
              </button>
            </div>
          </div>
        </main>
      </div>
    );
  }

  const profile = data;

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString('fr-FR');
    } catch {
      return dateStr;
    }
  };

  const formatDateTime = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleString('fr-FR');
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <Header
        title={`${profile.first_name} ${profile.last_name}`}
        action={
          <div className="flex items-center gap-2">
            <Link
              href={`/dashboard/servers/${serverId}/edit`}
              className="inline-flex items-center px-4 py-2 bg-white text-gray-700 text-sm font-medium rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors"
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Modifier
            </Link>
          </div>
        }
      />

      {/* Identity Section */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <svg className="w-5 h-5 text-[#D4AF37]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
          Identité
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-gray-50 rounded-lg p-4">
            <p className={SECTION}>Prénom</p>
            <p className="text-sm font-medium text-gray-900">{profile.first_name}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className={SECTION}>Nom</p>
            <p className="text-sm font-medium text-gray-900">{profile.last_name}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className={SECTION}>Email</p>
            <p className="text-sm text-gray-900">{profile.email}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className={SECTION}>Téléphone</p>
            <p className="text-sm text-gray-900">{profile.phone}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className={SECTION}>Genre</p>
            <p className="text-sm text-gray-900">{profile.gender === 'MALE' ? 'Homme' : profile.gender === 'FEMALE' ? 'Femme' : profile.gender}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className={SECTION}>Ville</p>
            <p className="text-sm text-gray-900">{profile.location.city}</p>
          </div>
        </div>
      </div>

      {/* Professional Profile Section */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <svg className="w-5 h-5 text-[#D4AF37]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
          Profil professionnel
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-50 rounded-lg p-4">
            <p className={SECTION}>Type de travailleur</p>
            <p className="text-sm font-medium text-gray-900">
              {profile.worker_type === 'HARD_WORKER' ? 'Profil performant' :
               profile.worker_type === 'BALANCED' ? 'Profil équilibré' :
               profile.worker_type === 'SOFT_WORKER' ? 'Profil souple' : profile.worker_type}
            </p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className={SECTION}>Années d'expérience</p>
            <p className="text-sm font-medium text-gray-900">{profile.years_experience} ans</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className={SECTION}>Statut</p>
            <p className={`text-sm font-medium ${profile.availability_status === 'AVAILABLE' ? 'text-green-600' : 'text-red-600'}`}>
              {profile.availability_status === 'AVAILABLE' ? 'Disponible' : 'Indisponible'}
            </p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className={SECTION}>Score mensuel</p>
            <p className="text-sm font-bold text-[#D4AF37]">{profile.points.current_month_points} pts</p>
          </div>
        </div>

        <div className="mb-6">
          <p className={SECTION}>Compétences</p>
          <div className="space-y-2">
            {profile.skills.length > 0 ? (
              profile.skills.map((skill) => (
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
              ))
            ) : (
              <p className="text-sm text-gray-500">Aucune compétence enregistrée</p>
            )}
          </div>
        </div>
      </div>

      {/* Transport Section */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <svg className="w-5 h-5 text-[#D4AF37]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192l-3.536 3.536M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-5 0a4 4 0 11-8 0 4 4 0 018 0z" />
          </svg>
          Transport
        </h3>
        {profile.vehicle ? (
          <div className="bg-gray-50 rounded-lg p-4 space-y-2">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-900">{profile.vehicle.brand} {profile.vehicle.model}</p>
                <p className="text-xs text-gray-500">Type: {profile.vehicle.vehicle_type} • {profile.vehicle.seats_total} places</p>
              </div>
              <div className="flex items-center gap-3">
                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
                  profile.vehicle.can_transport_coworkers ? 'bg-green-50 text-green-700 border-green-200' : 'bg-red-50 text-red-700 border-red-200'
                }`}>
                  {profile.vehicle.can_transport_coworkers ? 'Peut transporter des collègues ✅' : 'Ne peut pas transporter'}
                </span>
                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
                  profile.vehicle.is_active ? 'bg-green-50 text-green-700 border-green-200' : 'bg-red-50 text-red-700 border-red-200'
                }`}>
                  {profile.vehicle.is_active ? 'Actif' : 'Inactif'}
                </span>
              </div>
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-500">Aucun véhicule enregistré</p>
        )}
      </div>

      {/* Location Section */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <svg className="w-5 h-5 text-[#D4AF37]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          Localisation
        </h3>
        <div className="bg-gray-50 rounded-lg p-4">
          <p className="text-sm text-gray-900">{profile.location.city}, {profile.location.area || '—'}</p>
          <p className="text-xs text-gray-500 mt-1">
            {profile.location.is_verified ? (
              <span className="text-green-600">Localisation vérifiée ✅</span>
            ) : (
              <span className="text-gray-400">Localisation non vérifiée</span>
            )}
          </p>
        </div>
      </div>

      {/* Availability Section */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <svg className="w-5 h-5 text-[#D4AF37]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          Disponibilités
        </h3>
        <div className="space-y-2">
          {profile.availability.length > 0 ? (
            profile.availability.slice(0, 5).map((slot: { id: string; start_datetime: string; end_datetime: string; status: string }) => (
              <div key={slot.id} className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2">
                <span className="text-sm text-gray-700">
                  {formatDateTime(slot.start_datetime)} — {formatDateTime(slot.end_datetime)}
                </span>
                <span className={`text-xs font-medium ${slot.status === 'AVAILABLE' ? 'text-green-600' : 'text-red-600'}`}>
                  {slot.status === 'AVAILABLE' ? 'Disponible' : 'Indisponible'}
                </span>
              </div>
            ))
          ) : (
            <p className="text-sm text-gray-500">Aucune disponibilité enregistrée</p>
          )}
        </div>
        <Link
          href={`/dashboard/servers/${serverId}/availability`}
          className="inline-flex items-center mt-4 text-sm text-[#D4AF37] hover:text-[#B8941E] font-medium"
        >
          Gérer les disponibilités →
        </Link>
      </div>

      {/* Event History Section */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <svg className="w-5 h-5 text-[#D4AF37]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Historique des événements
        </h3>
        <p className="text-sm text-gray-500">L'historique des événements sera disponible prochainement.</p>
      </div>

      {/* Gamification Section */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <svg className="w-5 h-5 text-[#D4AF37]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Gamification
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-50 rounded-lg p-4">
            <p className={SECTION}>Points totaux</p>
            <p className="text-2xl font-bold text-gray-900">{profile.points.total_points}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className={SECTION}>Points du mois</p>
            <p className="text-2xl font-bold text-[#D4AF37]">{profile.points.current_month_points}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className={SECTION}>Classement</p>
            <p className="text-2xl font-bold text-gray-900">#{profile.points.rank ?? '—'}</p>
          </div>
        </div>
      </div>

      {/* Deactivate Section */}
      <div className="bg-white rounded-xl border border-red-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-red-600 mb-4 flex items-center gap-2">
          <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          Actions critiques
        </h3>
        <p className="text-sm text-gray-600 mb-4">
          La désactivation conservera les données mais empêchera le serveur d'être assigné à de nouveaux événements.
        </p>
        <button
          onClick={() => setShowDeleteDialog(true)}
          disabled={deactivating}
          className="px-4 py-2 bg-red-50 text-red-600 text-sm font-medium rounded-lg border border-red-200 hover:bg-red-100 transition-colors"
        >
          {deactivating ? 'Désactivation...' : 'Désactiver le serveur'}
        </button>
      </div>

      {showDeleteDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-xl p-6 max-w-md w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Désactiver le serveur</h3>
            <p className="text-sm text-gray-600 mb-4">
              Êtes-vous sûr de vouloir désactiver <strong>{profile.first_name} {profile.last_name}</strong> ?
              Le serveur ne sera plus assignable aux nouveaux événements.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowDeleteDialog(false)}
                className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50"
              >
                Annuler
              </button>
              <button
                onClick={handleDeactivate}
                disabled={deactivating}
                className="px-4 py-2 text-sm font-medium rounded-lg bg-red-500 text-white hover:bg-red-600 disabled:opacity-50"
              >
                {deactivating ? 'Désactivation...' : 'Confirmer la désactivation'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}