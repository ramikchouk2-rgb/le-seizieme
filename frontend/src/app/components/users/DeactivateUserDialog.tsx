'use client';

import { UserListItem } from '@/app/lib/types';

interface DeactivateUserDialogProps {
  user: UserListItem;
  open: boolean;
  loading: boolean;
  onClose: () => void;
  onConfirm: () => void;
}

export default function DeactivateUserDialog({
  user,
  open,
  loading,
  onClose,
  onConfirm,
}: DeactivateUserDialogProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl p-6 max-w-md w-full mx-4 shadow-xl">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Désactiver l'utilisateur</h3>
        <p className="text-sm text-gray-600 mb-4">
          Êtes-vous sûr de vouloir désactiver <strong>{user.email}</strong> ?
          L'utilisateur ne pourra plus se connecter, mais ses données seront conservées.
        </p>
        {user.role === 'ADMIN' && (
          <p className="text-sm text-orange-700 bg-orange-50 border border-orange-200 rounded-lg p-3 mb-4">
            Attention : il ne restera plus aucun administrateur actif si vous désactivez ce compte.
          </p>
        )}
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            Annuler
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-red-500 text-white hover:bg-red-600 disabled:opacity-50"
          >
            {loading ? 'Désactivation...' : 'Confirmer la désactivation'}
          </button>
        </div>
      </div>
    </div>
  );
}
