'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import {
  ACCEPTED_ATTESTATION_TYPES,
  ApiError,
  MAX_ATTESTATION_BYTES,
  getServerAttestationFile,
  listServerAttestations,
  rejectServerAttestation,
  supersedeServerAttestation,
  uploadServerAttestation,
  validateAttestationFile,
  verifyServerAttestation,
} from '@/app/lib/api';
import type { ServerAttestation } from '@/app/lib/types';

const MAX_ATTESTATION_MB = Math.round(MAX_ATTESTATION_BYTES / (1024 * 1024));

interface ServerAttestationsPanelProps {
  serverId: string;
  /** False for roles without MANAGER/ADMIN, matching the API's permission model. */
  canManage: boolean;
}

const STATUS_STYLES: Record<string, string> = {
  PENDING: 'bg-amber-50 text-amber-700 border-amber-200',
  VERIFIED: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  REJECTED: 'bg-red-50 text-red-700 border-red-200',
  SUPERSEDED: 'bg-gray-100 text-gray-600 border-gray-200',
};

/**
 * Manage a server's professional attestations. Step 24C-D-6.
 *
 * Append-only: uploading always creates a NEW PENDING record and never edits an
 * existing one. An upload is never verified automatically -- verification is an
 * explicit Manager/Admin decision, which is why every list entry shows its
 * status and only VERIFIED entries count.
 */
export default function ServerAttestationsPanel({
  serverId,
  canManage,
}: ServerAttestationsPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [items, setItems] = useState<ServerAttestation[]>([]);
  const [verifiedCount, setVerifiedCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [qualificationName, setQualificationName] = useState('');
  const [issuingOrganization, setIssuingOrganization] = useState('');
  const [issuedOn, setIssuedOn] = useState('');
  const [expiresOn, setExpiresOn] = useState('');

  const [rejectingId, setRejectingId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [supersedingId, setSupersedingId] = useState<string | null>(null);
  const [replacementId, setReplacementId] = useState('');

  const refresh = useCallback(async () => {
    try {
      const data = await listServerAttestations(serverId);
      setItems(data.items);
      setVerifiedCount(data.verified_count);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail || 'Chargement impossible.' : 'Chargement impossible.',
      );
    } finally {
      setLoading(false);
    }
  }, [serverId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  function message(err: unknown, fallback: string) {
    return err instanceof ApiError && err.detail ? err.detail : fallback;
  }

  async function handleUpload(file: File | undefined) {
    if (!file) return;
    setError(null);

    // Client-side checks are fast feedback only; the server re-validates by
    // magic bytes and is the sole authority.
    const validation = validateAttestationFile(file);
    if (!validation.valid) {
      setError(validation.error ?? 'Fichier invalide.');
      if (inputRef.current) inputRef.current.value = '';
      return;
    }
    if (!qualificationName.trim()) {
      setError("L'intitulé de la qualification est obligatoire.");
      if (inputRef.current) inputRef.current.value = '';
      return;
    }

    setBusy(true);
    try {
      await uploadServerAttestation(serverId, file, {
        qualification_name: qualificationName,
        issuing_organization: issuingOrganization || undefined,
        issued_on: issuedOn || undefined,
        expires_on: expiresOn || undefined,
      });
      setQualificationName('');
      setIssuingOrganization('');
      setIssuedOn('');
      setExpiresOn('');
      await refresh();
    } catch (err) {
      setError(message(err, "Échec de l'envoi du document."));
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  }

  async function handleVerify(id: string) {
    setError(null);
    setBusyId(id);
    try {
      await verifyServerAttestation(serverId, id);
      await refresh();
    } catch (err) {
      setError(message(err, 'Échec de la vérification.'));
    } finally {
      setBusyId(null);
    }
  }

  async function handleReject(id: string) {
    setError(null);
    if (!rejectReason.trim()) {
      setError('Un motif de rejet est obligatoire.');
      return;
    }
    setBusyId(id);
    try {
      await rejectServerAttestation(serverId, id, rejectReason);
      setRejectingId(null);
      setRejectReason('');
      await refresh();
    } catch (err) {
      setError(message(err, 'Échec du rejet.'));
    } finally {
      setBusyId(null);
    }
  }

  async function handleSupersede(id: string) {
    setError(null);
    setBusyId(id);
    try {
      // A VERIFIED attestation requires its replacement to be named, so a real
      // qualification can never silently stop counting.
      await supersedeServerAttestation(serverId, id, replacementId || undefined);
      setSupersedingId(null);
      setReplacementId('');
      await refresh();
    } catch (err) {
      setError(message(err, 'Échec du remplacement.'));
    } finally {
      setBusyId(null);
    }
  }

  async function handleOpenDocument(attestation: ServerAttestation) {
    setError(null);
    setBusyId(attestation.id);
    try {
      // No public URL exists: the bytes are fetched through the protected
      // endpoint and handed to the browser as an object URL.
      const blob = await getServerAttestationFile(serverId, attestation.id);
      const url = URL.createObjectURL(blob);
      const name = attestation.file.original_filename || 'document';
      window.open(url, '_blank', 'noopener');
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (err) {
      setError(message(err, "Ouverture du document impossible."));
    } finally {
      setBusyId(null);
    }
  }

  // Only VERIFIED, non-superseded rows can act as a replacement.
  const replaceable = items.filter((a) => a.status !== 'SUPERSEDED');

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-sm text-gray-600">
          {verifiedCount} qualification{verifiedCount > 1 ? 's' : ''} vérifiée
          {verifiedCount > 1 ? 's' : ''}
        </p>
      </div>

      {canManage && (
        <div className="space-y-3 rounded-lg border border-gray-200 bg-gray-50 p-3">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="text-xs font-medium text-gray-700">
                Intitulé de la qualification *
              </span>
              <input
                type="text"
                value={qualificationName}
                onChange={(e) => setQualificationName(e.target.value)}
                maxLength={200}
                className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"
                placeholder="Ex. Sommelier"
              />
            </label>
            <label className="block">
              <span className="text-xs font-medium text-gray-700">
                Organisme émetteur
              </span>
              <input
                type="text"
                value={issuingOrganization}
                onChange={(e) => setIssuingOrganization(e.target.value)}
                maxLength={200}
                className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"
              />
            </label>
            <label className="block">
              <span className="text-xs font-medium text-gray-700">Délivré le</span>
              <input
                type="date"
                value={issuedOn}
                onChange={(e) => setIssuedOn(e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"
              />
            </label>
            <label className="block">
              <span className="text-xs font-medium text-gray-700">Expire le</span>
              <input
                type="date"
                value={expiresOn}
                onChange={(e) => setExpiresOn(e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"
              />
            </label>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <input
              ref={inputRef}
              type="file"
              accept={ACCEPTED_ATTESTATION_TYPES.join(',')}
              className="hidden"
              onChange={(e) => handleUpload(e.target.files?.[0])}
            />
            <button
              type="button"
              disabled={busy}
              onClick={() => inputRef.current?.click()}
              className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {busy ? 'Envoi...' : 'Ajouter un document'}
            </button>
            <span className="text-xs text-gray-500">
              PDF, JPEG, PNG ou WebP · {MAX_ATTESTATION_MB} Mo maximum.
            </span>
          </div>
          <p className="text-xs text-gray-500">
            Chaque envoi crée une attestation en attente. Un document n'est jamais
            validé automatiquement.
          </p>
        </div>
      )}

      {error && (
        <p role="alert" className="text-sm text-red-600">
          {error}
        </p>
      )}

      {loading ? (
        <p className="text-sm text-gray-500">Chargement...</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-gray-500">Aucune attestation.</p>
      ) : (
        <ul className="space-y-3">
          {items.map((att) => (
            <li
              key={att.id}
              className="rounded-lg border border-gray-200 bg-white p-3"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-900">
                    {att.qualification_name}
                  </p>
                  <p className="text-xs text-gray-500">
                    {att.file.original_filename || 'Document'} ·{' '}
                    {(att.file.file_size / 1024).toFixed(0)} Ko
                    {att.issuing_organization ? ` · ${att.issuing_organization}` : ''}
                    {att.issued_on ? ` · délivré le ${att.issued_on}` : ''}
                    {att.expires_on ? ` · expire le ${att.expires_on}` : ''}
                  </p>
                  <span
                    className={`mt-1 inline-block rounded border px-2 py-0.5 text-xs font-medium ${
                      STATUS_STYLES[att.status] ?? STATUS_STYLES.SUPERSEDED
                    }`}
                  >
                    {att.status_label}
                  </span>
                  {!att.counts_as_verified_qualification && (
                    <p className="mt-1 text-xs text-gray-500">
                      Ne compte pas comme qualification vérifiée.
                    </p>
                  )}
                  {att.rejection_reason && (
                    <p className="mt-1 text-xs text-red-600">
                      Motif du rejet : {att.rejection_reason}
                    </p>
                  )}
                  {att.verified_at && (
                    <p className="mt-1 text-xs text-gray-500">
                      Vérifié le {att.verified_at.slice(0, 10)}
                    </p>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    disabled={busyId === att.id}
                    onClick={() => handleOpenDocument(att)}
                    className="rounded-md border border-gray-300 bg-white px-2.5 py-1 text-sm text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50"
                  >
                    Ouvrir
                  </button>

                  {canManage && att.status === 'PENDING' && (
                    <>
                      <button
                        type="button"
                        disabled={busyId === att.id}
                        onClick={() => handleVerify(att.id)}
                        className="rounded-md bg-emerald-600 px-2.5 py-1 text-sm font-medium text-white transition-colors hover:bg-emerald-700 disabled:opacity-50"
                      >
                        Vérifier
                      </button>
                      <button
                        type="button"
                        disabled={busyId === att.id}
                        onClick={() => {
                          setRejectingId(att.id);
                          setRejectReason('');
                        }}
                        className="rounded-md border border-red-200 bg-white px-2.5 py-1 text-sm text-red-600 transition-colors hover:bg-red-50 disabled:opacity-50"
                      >
                        Rejeter
                      </button>
                    </>
                  )}

                  {canManage && att.status !== 'SUPERSEDED' && (
                    <button
                      type="button"
                      disabled={busyId === att.id}
                      onClick={() => {
                        setSupersedingId(att.id);
                        setReplacementId('');
                      }}
                      className="rounded-md border border-gray-300 bg-white px-2.5 py-1 text-sm text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50"
                    >
                      Remplacer
                    </button>
                  )}
                </div>
              </div>

              {rejectingId === att.id && (
                <div className="mt-3 flex flex-wrap items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2">
                  <input
                    type="text"
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    placeholder="Motif du rejet"
                    className="min-w-0 flex-1 rounded-md border border-gray-300 px-2 py-1 text-sm"
                  />
                  <button
                    type="button"
                    disabled={busyId === att.id}
                    onClick={() => handleReject(att.id)}
                    className="rounded-md bg-red-600 px-2.5 py-1 text-sm font-medium text-white transition-colors hover:bg-red-700 disabled:opacity-50"
                  >
                    Confirmer
                  </button>
                  <button
                    type="button"
                    disabled={busyId === att.id}
                    onClick={() => setRejectingId(null)}
                    className="rounded-md border border-gray-300 bg-white px-2.5 py-1 text-sm text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50"
                  >
                    Annuler
                  </button>
                </div>
              )}

              {supersedingId === att.id && (
                <div className="mt-3 flex flex-wrap items-center gap-2 rounded-lg border border-gray-300 bg-gray-50 px-3 py-2">
                  <select
                    value={replacementId}
                    onChange={(e) => setReplacementId(e.target.value)}
                    className="min-w-0 flex-1 rounded-md border border-gray-300 bg-white px-2 py-1 text-sm"
                  >
                    <option value="">
                      {att.status === 'VERIFIED'
                        ? 'Document de remplacement (obligatoire)'
                        : 'Aucun document de remplacement'}
                    </option>
                    {replaceable
                      .filter((r) => r.id !== att.id)
                      .map((r) => (
                        <option key={r.id} value={r.id}>
                          {r.qualification_name} ({r.status_label})
                        </option>
                      ))}
                  </select>
                  <button
                    type="button"
                    disabled={busyId === att.id}
                    onClick={() => handleSupersede(att.id)}
                    className="rounded-md bg-gray-700 px-2.5 py-1 text-sm font-medium text-white transition-colors hover:bg-gray-800 disabled:opacity-50"
                  >
                    Confirmer
                  </button>
                  <button
                    type="button"
                    disabled={busyId === att.id}
                    onClick={() => setSupersedingId(null)}
                    className="rounded-md border border-gray-300 bg-white px-2.5 py-1 text-sm text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50"
                  >
                    Annuler
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}