'use client';

import { useRef, useState } from 'react';

import {
  ACCEPTED_PROFILE_PHOTO_TYPES,
  ApiError,
  MAX_PROFILE_PHOTO_BYTES,
  deleteServerProfilePhoto,
  uploadServerProfilePhoto,
  validateProfilePhotoFile,
} from '@/app/lib/api';

// Derived from the shared constant so the displayed limit can never drift from
// the limit actually enforced client-side (the backend re-validates regardless).
const MAX_PROFILE_PHOTO_MB = Math.round(MAX_PROFILE_PHOTO_BYTES / (1024 * 1024));

interface ProfilePhotoControlsProps {
  serverId: string;
  hasProfilePhoto: boolean;
  /** Bumped by the parent after a successful upload or deletion. */
  onChanged: () => void;
}

/**
 * Upload / replace / delete a server's profile photo.
 *
 * Step 24C-D-5. Client-side validation is only a fast feedback aid: the server
 * re-validates by magic bytes and is the sole authority. Error text comes from
 * the API so the user sees the real reason (format, size, permission).
 */
export default function ProfilePhotoControls({
  serverId,
  hasProfilePhoto,
  onChanged,
}: ProfilePhotoControlsProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  async function handleFileSelected(file: File | undefined) {
    if (!file) return;
    setError(null);

    const validation = validateProfilePhotoFile(file);
    if (!validation.valid) {
      setError(validation.error ?? 'Fichier invalide.');
      if (inputRef.current) inputRef.current.value = '';
      return;
    }

    setBusy(true);
    try {
      await uploadServerProfilePhoto(serverId, file);
      setConfirmingDelete(false);
      onChanged();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail || 'Échec de l’envoi de la photo.'
          : 'Échec de l’envoi de la photo.',
      );
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  }

  async function handleDelete() {
    setError(null);
    setBusy(true);
    try {
      await deleteServerProfilePhoto(serverId);
      setConfirmingDelete(false);
      onChanged();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail || 'Échec de la suppression.'
          : 'Échec de la suppression.',
      );
    } finally {
      setBusy(false);
    }
  }

  const accept = ACCEPTED_PROFILE_PHOTO_TYPES.join(',');

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          className="hidden"
          onChange={(e) => handleFileSelected(e.target.files?.[0])}
        />

        <button
          type="button"
          disabled={busy}
          onClick={() => inputRef.current?.click()}
          className="px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {busy ? 'Traitement...' : hasProfilePhoto ? 'Remplacer la photo' : 'Ajouter une photo'}
        </button>

        {hasProfilePhoto && !confirmingDelete && (
          <button
            type="button"
            disabled={busy}
            onClick={() => setConfirmingDelete(true)}
            className="px-3 py-1.5 text-sm font-medium rounded-lg border border-red-200 bg-white text-red-600 hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Supprimer
          </button>
        )}
      </div>

      {confirmingDelete && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2">
          <p className="text-sm text-red-700">Supprimer définitivement la photo ?</p>
          <button
            type="button"
            disabled={busy}
            onClick={handleDelete}
            className="px-2.5 py-1 text-sm font-medium rounded-md bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 transition-colors"
          >
            {busy ? 'Suppression...' : 'Confirmer'}
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => setConfirmingDelete(false)}
            className="px-2.5 py-1 text-sm font-medium rounded-md border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-50 transition-colors"
          >
            Annuler
          </button>
        </div>
      )}

      {error && (
        <p role="alert" className="text-sm text-red-600">
          {error}
        </p>
      )}

      <p className="text-xs text-gray-500">
        JPEG, PNG ou WebP · {MAX_PROFILE_PHOTO_MB} Mo maximum.
      </p>
    </div>
  );
}