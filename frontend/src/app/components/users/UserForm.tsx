'use client';

import { useState, useEffect } from 'react';
import { UserCreateRequest, UserUpdateRequest, USER_ROLE_OPTIONS } from '@/app/lib/types';
import { createUser, updateUser } from '@/app/lib/api';
import { useAnnouncer } from '@/app/components/ui/Announcer';

interface UserFormProps {
  mode: 'create' | 'edit';
  initialData?: {
    id: string;
    email: string;
    role: string;
    is_active: boolean;
  } | null;
  onSuccess?: (userId: string) => void;
  onCancel?: () => void;
}

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MIN_PASSWORD_LENGTH = 8;

function validateCreate(form: Partial<UserCreateRequest>): string | null {
  if (!form.email?.trim()) return 'L\'email est requis.';
  if (!EMAIL_REGEX.test(form.email)) return 'Format d\'email invalide.';
  if (!form.role) return 'Le rôle est requis.';
  if (!form.password) return 'Le mot de passe est requis.';
  if (form.password.length < MIN_PASSWORD_LENGTH) {
    return `Le mot de passe doit contenir au moins ${MIN_PASSWORD_LENGTH} caractères.`;
  }
  if (form.is_active === undefined) return 'Le statut est requis.';
  return null;
}

export default function UserForm({ mode, initialData, onSuccess, onCancel }: UserFormProps) {
  const { announceError } = useAnnouncer();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [changePassword, setChangePassword] = useState(false);

  const [form, setForm] = useState<Partial<UserCreateRequest>>({
    email: '',
    password: '',
    role: 'STAFF',
    is_active: true,
  });

  useEffect(() => {
    if (mode === 'edit' && initialData) {
      setForm({
        email: initialData.email || '',
        role: (initialData.role || 'STAFF') as UserCreateRequest['role'],
        is_active: initialData.is_active !== undefined ? initialData.is_active : true,
      });
    }
  }, [mode, initialData]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const validationError = validateCreate(form);
    if (validationError) {
      setError(validationError);
      return;
    }

    setSubmitting(true);
    try {
      if (mode === 'create') {
        const result = await createUser(form as UserCreateRequest);
        onSuccess?.(result.id);
      } else if (initialData) {
        const payload: UserUpdateRequest = {};
        if (form.email && form.email !== initialData.email) payload.email = form.email;
        if (form.role && form.role !== initialData.role) payload.role = form.role;
        if (form.is_active !== undefined && form.is_active !== initialData.is_active) {
          payload.is_active = form.is_active;
        }
        if (changePassword && form.password) {
          payload.password = form.password;
        }
        const result = await updateUser(initialData.id, payload);
        onSuccess?.(result.id);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Une erreur est survenue.';
      setError(message);
      announceError(message);
    } finally {
      setSubmitting(false);
    }
  };

  const inputClass =
    'w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]';
  const sectionClass = 'bg-gray-50 rounded-xl p-5 border border-gray-100';

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">{error}</div>
      )}

      <div className={sectionClass}>
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <svg className="w-5 h-5 text-[#D4AF37]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 012 2v2a1 1 0 01-1 1H4a1 1 0 01-1-1v-2a2 2 0 012-2z" />
          </svg>
          Informations
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="md:col-span-2">
            <label htmlFor="user-email" className="block text-sm font-medium text-gray-700 mb-1">
              Email *
            </label>
            <input
              id="user-email"
              type="email"
              required
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className={inputClass}
            />
          </div>

          {mode === 'create' && (
            <div>
              <label htmlFor="user-password" className="block text-sm font-medium text-gray-700 mb-1">
                Mot de passe *
              </label>
              <input
                id="user-password"
                type="password"
                required
                minLength={MIN_PASSWORD_LENGTH}
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                className={inputClass}
                autoComplete="new-password"
              />
            </div>
          )}

          {mode === 'edit' && (
            <div>
              <label htmlFor="user-role" className="block text-sm font-medium text-gray-700 mb-1">
                Rôle *
              </label>
              <select
                id="user-role"
                required
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value as UserCreateRequest['role'] })}
                className={inputClass}
              >
                {USER_ROLE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>

      {mode === 'create' && (
        <div className={sectionClass}>
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <svg className="w-5 h-5 text-[#D4AF37]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 012 2v2a1 1 0 01-1 1H4a1 1 0 01-1-1v-2a2 2 0 012-2z" />
              </svg>
            Statut
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="user-active" className="block text-sm font-medium text-gray-700 mb-1">
                Actif
              </label>
              <select
                id="user-active"
                value={form.is_active ? 'true' : 'false'}
                onChange={(e) => setForm({ ...form, is_active: e.target.value === 'true' })}
                className={inputClass}
              >
                <option value="true">Oui</option>
                <option value="false">Non</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {mode === 'edit' && (
        <div className={sectionClass}>
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <svg className="w-5 h-5 text-[#D4AF37]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m0 0v2m0-2h2m-2 0h-2z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.447a8.954 8.954 0 013.35-1.52 8.983 8.983 0 013.46-.09 8.983 8.983 0 012.54 1.01 8.954 8.954 0 011.52 2.35 8.983 8.983 0 01.52 2.69v1.86a8.983 8.983 0 01-.52 2.69 8.954 8.954 0 01-1.52 2.35 8.983 8.983 0 01-2.54 1.01 8.983 8.983 0 01-3.46-.09 8.954 8.954 0 01-3.35-1.52 8.983 8.983 0 01-2.54-1.01 8.954 8.954 0 01-1.52-2.35 8.983 8.983 0 01-.52-2.69v-1.86a8.983 8.983 0 01.52-2.69 8.954 8.954 0 011.52-2.35 8.983 8.983 0 012.54-1.01 8.954 8.954 0 013.35.52z" />
            </svg>
            Sécurité
          </h3>
          <p className="text-sm text-gray-500 mb-4">
            Laissez le mot de passe vide pour conserver l'actuel.
          </p>
          {changePassword && (
            <div className="mb-4">
              <label htmlFor="user-edit-password" className="block text-sm font-medium text-gray-700 mb-1">
                Nouveau mot de passe *
              </label>
              <input
                id="user-edit-password"
                type="password"
                minLength={MIN_PASSWORD_LENGTH}
                value={form.password || ''}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                className={inputClass}
                autoComplete="new-password"
              />
              {form.password && form.password.length < MIN_PASSWORD_LENGTH && (
                <p className="mt-1 text-xs text-red-600">
                  Le mot de passe doit contenir au moins {MIN_PASSWORD_LENGTH} caractères.
                </p>
              )}
            </div>
          )}
          <button
            type="button"
            onClick={() => setChangePassword((v) => !v)}
            className="text-sm text-[#D4AF37] hover:text-[#B8941E] font-medium"
          >
            {changePassword ? 'Annuler le changement' : 'Changer le mot de passe'}
          </button>
        </div>
      )}

      <div className="flex justify-end gap-2 pt-2">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={submitting}
            className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Annuler
          </button>
        )}
        <button
          type="submit"
          disabled={submitting}
          className="px-4 py-2 text-sm font-medium rounded-lg bg-[#D4AF37] text-white hover:bg-[#B8941E] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {submitting
            ? mode === 'create'
              ? 'Création...'
              : 'Enregistrement...'
            : mode === 'create'
            ? 'Créer l\'utilisateur'
            : 'Enregistrer les modifications'}
        </button>
      </div>
    </form>
  );
}
