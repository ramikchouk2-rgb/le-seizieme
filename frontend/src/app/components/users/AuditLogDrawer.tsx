'use client';

import { useEffect, useState } from 'react';
import { AuditLogItem } from '@/app/lib/types';

interface AuditLogDrawerProps {
  item: AuditLogItem | null;
  open: boolean;
  onClose: () => void;
}

function formatDateTime(value?: string | null) {
  if (!value) return '—';
  const date = new Date(value.endsWith('Z') ? value : `${value}Z`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

const REDACTED_PLACEHOLDER = '[MASQUÉ]';
const MAX_DETAIL_DEPTH = 10;
const SENSITIVE_KEY_PATTERN =
  /pass|secret|token|jwt|credential|api[_-]?key|apikey|private[_-]?key|authorization|auth[_-]?key|auth[_-]?header|cookie|session[_-]?(id|token)|bearer|otp|mfa|signature|salt/i;

function isSensitiveKey(key: string): boolean {
  return SENSITIVE_KEY_PATTERN.test(key.replace(/[\s-]/g, '_'));
}

function sanitizeDetailValue(value: unknown, seen: WeakSet<object>, depth: number): unknown {
  if (value === null) return null;

  const type = typeof value;
  if (type === 'string' || type === 'number' || type === 'boolean') return value;
  if (type !== 'object') return String(value);
  if (depth >= MAX_DETAIL_DEPTH) return '[...]';

  const objectValue = value as object;
  if (seen.has(objectValue)) return '[Circulaire]';
  seen.add(objectValue);

  try {
    if (Array.isArray(value)) {
      return value.map((entry) => sanitizeDetailValue(entry, seen, depth + 1));
    }
    const sanitized: Record<string, unknown> = {};
    for (const [key, entry] of Object.entries(value as Record<string, unknown>)) {
      sanitized[key] = isSensitiveKey(key) ? REDACTED_PLACEHOLDER : sanitizeDetailValue(entry, seen, depth + 1);
    }
    return sanitized;
  } catch {
    return '[Donnée illisible]';
  } finally {
    seen.delete(objectValue);
  }
}

function formatDetail(detail: Record<string, unknown> | null): string {
  if (detail === null || detail === undefined) return 'Aucun détail disponible';
  if (typeof detail !== 'object') return String(detail);
  if (Object.keys(detail).length === 0) return 'Aucun détail disponible';
  try {
    return JSON.stringify(sanitizeDetailValue(detail, new WeakSet<object>(), 0), null, 2);
  } catch {
    return 'Erreur lors de l\'affichage du détail';
  }
}

function DetailSection({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">{label}</p>
      <div className="bg-gray-50 rounded-lg p-3 font-mono text-sm text-gray-900 whitespace-pre-wrap break-words">
        {children}
      </div>
    </div>
  );
}

export default function AuditLogDrawer({ item, open, onClose }: AuditLogDrawerProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!open || !item || !mounted) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="fixed inset-0 bg-black/30" onClick={onClose} aria-hidden="true" />
        <div className="relative bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] flex flex-col">
          <div className="flex items-center justify-between p-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">Détail de l'entrée d'audit</h3>
            <button
              onClick={onClose}
              className="p-1 rounded-lg text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition-colors"
              aria-label="Fermer"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="p-4 overflow-y-auto flex-1 space-y-4">
            <DetailSection label="ID">#{item.id}</DetailSection>
            <DetailSection label="Action">
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border bg-blue-50 text-blue-700 border-blue-200">
                {item.action}
              </span>
            </DetailSection>
            <DetailSection label="Date et heure">{formatDateTime(item.created_at)}</DetailSection>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <DetailSection label="Acteur (email)">
                {item.actor_email || '—'}
              </DetailSection>
              <DetailSection label="Acteur (ID)">
                {item.actor_user_id || '—'}
              </DetailSection>
              <DetailSection label="Cible (email)">
                {item.target_email || '—'}
              </DetailSection>
              <DetailSection label="Cible (ID)">
                {item.target_user_id || '—'}
              </DetailSection>
            </div>

            <DetailSection label="Détail complet">
              <pre className="text-xs overflow-x-auto">{formatDetail(item.detail)}</pre>
            </DetailSection>
          </div>

          <div className="p-4 border-t border-gray-200 flex justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors"
            >
              Fermer
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}