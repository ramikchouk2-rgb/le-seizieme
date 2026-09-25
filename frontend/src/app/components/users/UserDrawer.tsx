'use client';

import Link from 'next/link';
import { useFocusTrap } from '@/app/components/ui/FocusTrap';
import { useAnnouncer } from '@/app/components/ui/Announcer';
import { USER_ROLES, UserListItem, UserUpdateRequest } from '@/app/lib/types';
import { USER_ROLE_OPTIONS } from '@/app/data/users';
import { useUpdateUser, useDeactivateUser } from '@/app/lib/hooks';
import DeactivateUserDialog from '@/app/components/users/DeactivateUserDialog';
import { useState, useEffect } from 'react';

interface UserDrawerProps {
  user: UserListItem | null;
  open: boolean;
  onClose: () => void;
}

const SECTION = 'text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2';

const ROLE_BADGE: Record<string, string> = {
  ADMIN: 'bg-purple-50 text-purple-700 border-purple-200',
  MANAGER: 'bg-blue-50 text-blue-700 border-blue-200',
  STAFF: 'bg-gray-50 text-gray-700 border-gray-200',
};

function StatusBadge({ active }: { active: boolean }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
        active
          ? 'bg-green-50 text-green-700 border-green-200'
          : 'bg-red-50 text-red-700 border-red-200'
      }`}
    >
      {active ? 'Actif' : 'Inactif'}
    </span>
  );
}

function formatDate(value?: string | null) {
  if (!value) return '—';
  const date = new Date(value.endsWith('Z') ? value : `${value}Z`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString('fr-FR', { year: 'numeric', month: 'short', day: 'numeric' });
}

export default function UserDrawer({ user, open, onClose }: UserDrawerProps) {
  const containerRef = useFocusTrap({ onClose, closeOnEscape: true, restoreFocus: true });
  const { announceSuccess, announceError } = useAnnouncer();
  const updateUser = useUpdateUser();
  const deactivateUser = useDeactivateUser();
  const [deactivateDialogOpen, setDeactivateDialogOpen] = useState(false);
  const [roleSaving, setRoleSaving] = useState(false);
  const [activeSaving, setActiveSaving] = useState(false);
  const [displayUser, setDisplayUser] = useState<UserListItem | null>(user);

  useEffect(() => {
    setDisplayUser(user);
    setDeactivateDialogOpen(false);
  }, [user]);

  if (!open || !displayUser) return null;

  const handleRoleChange = async (role: string) => {
    if (role === displayUser.role) return;
    setRoleSaving(true);
    try {
      await updateUser.mutateAsync({ userId: displayUser.id, payload: { role: role as UserUpdateRequest['role'] } });
      setDisplayUser((u) => (u ? { ...u, role } : u));
      announceSuccess('Rôle mis à jour.');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Impossible de modifier le rôle.';
      announceError(message);
    } finally {
      setRoleSaving(false);
    }
  };

  const handleToggleActive = async () => {
    setActiveSaving(true);
    try {
      await updateUser.mutateAsync({
        userId: displayUser.id,
        payload: { is_active: !displayUser.is_active },
      });
      setDisplayUser((u) => (u ? { ...u, is_active: !u.is_active } : u));
      announceSuccess(`Utilisateur ${displayUser.is_active ? 'désactivé' : 'activé'}.`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Impossible de modifier le statut.";
      announceError(message);
    } finally {
      setActiveSaving(false);
    }
  };

  const handleDeactivate = async () => {
    try {
      await deactivateUser.mutateAsync(displayUser.id);
      announceSuccess('Utilisateur désactivé.');
      setDeactivateDialogOpen(false);
      onClose();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Impossible de désactiver l\'utilisateur.';
      announceError(message);
    }
  };

  return (
    <>
      <div className="fixed inset-0 z-[60] flex">
        <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
        <div
          ref={containerRef}
          className="absolute right-0 top-0 h-full w-full max-w-xl bg-white shadow-2xl overflow-y-auto"
        >
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-gray-900">Profil utilisateur</h2>
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
                {displayUser.email?.[0]?.toUpperCase() || 'U'}
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{displayUser.email}</h3>
                <p className="text-sm text-gray-500">
                  {USER_ROLES[displayUser.role as keyof typeof USER_ROLES] || displayUser.role}
                </p>
              </div>
            </div>

            <div className="space-y-6">
              <div className="bg-gray-50 rounded-lg p-4">
                <p className={SECTION}>Rôle</p>
                <div className="flex items-center gap-3">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
                      ROLE_BADGE[displayUser.role] || 'bg-gray-50 text-gray-700 border-gray-200'
                    }`}
                  >
                    {USER_ROLES[displayUser.role as keyof typeof USER_ROLES] || displayUser.role}
                  </span>
                  <select
                    value={displayUser.role}
                    disabled={roleSaving}
                    onChange={(e) => handleRoleChange(e.target.value)}
                    className="text-sm rounded-lg border border-gray-300 px-2 py-1 focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 disabled:opacity-50"
                  >
                    {USER_ROLE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                  {roleSaving && <span className="text-xs text-gray-500">Enregistrement...</span>}
                </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <p className={SECTION}>Statut</p>
                <div className="flex items-center gap-3">
                  <StatusBadge active={displayUser.is_active} />
                  <button
                    onClick={handleToggleActive}
                    disabled={activeSaving}
                    className={`px-3 py-1 text-xs font-medium rounded-lg border transition-colors ${
                      displayUser.is_active
                        ? 'bg-red-50 text-red-600 border-red-200 hover:bg-red-100'
                        : 'bg-green-50 text-green-600 border-green-200 hover:bg-green-100'
                    }`}
                  >
                    {activeSaving
                      ? 'Enregistrement...'
                      : displayUser.is_active
                      ? 'Désactiver'
                      : 'Réactiver'}
                  </button>
                </div>
              </div>
            </div>

            <div className="mt-6 pt-6 border-t border-gray-200 space-y-4">
              <div className="flex justify-between">
                <span className="text-sm text-gray-500">Créé le</span>
                <span className="text-sm text-gray-900">{formatDate(displayUser.created_at)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-500">Mis à jour</span>
                <span className="text-sm text-gray-900">{formatDate(displayUser.updated_at)}</span>
              </div>
            </div>

            <div className="mt-6 flex items-center justify-between">
              <Link
                href={`/dashboard/users/${displayUser.id}/edit`}
                className="inline-flex items-center px-4 py-2 bg-[#D4AF37] text-white text-sm font-medium rounded-lg hover:bg-[#B8941E] transition-colors"
              >
                Modifier l'utilisateur
              </Link>
              <button
                onClick={() => setDeactivateDialogOpen(true)}
                disabled={updateUser.isPending}
                className="px-4 py-2 bg-red-50 text-red-600 text-sm font-medium rounded-lg border border-red-200 hover:bg-red-100 transition-colors"
              >
                Désactiver
              </button>
            </div>
          </div>
        </div>
      </div>

      <DeactivateUserDialog
        user={displayUser}
        open={deactivateDialogOpen}
        loading={deactivateUser.isPending}
        onClose={() => setDeactivateDialogOpen(false)}
        onConfirm={handleDeactivate}
      />
    </>
  );
}
