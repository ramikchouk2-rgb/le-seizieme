'use client';

import { useState, useEffect } from 'react';
import { City, ServerCreateRequest, ServerUpdateRequest, createServer, updateServer, getCities } from '@/app/lib/api';

interface ServerFormProps {
  mode: 'create' | 'edit';
  initialData?: {
    first_name: string;
    last_name: string;
    email: string;
    phone: string;
    gender: string;
    city_id: string;
    years_experience: number;
    worker_type?: string;
    speed_score?: number;
    punctuality_score?: number;
    presentation_score?: number;
    communication_score?: number;
    teamwork_score?: number;
    discipline_score?: number;
    endurance_score?: number;
    is_active?: boolean;
    id: string;
  } | null;
  onSuccess?: (eventId: string) => void;
  onCancel?: () => void;
}

const GENDER_OPTIONS = [
  { value: 'MALE', label: 'Homme' },
  { value: 'FEMALE', label: 'Femme' },
];

const WORKER_TYPE_OPTIONS = [
  { value: 'HARD_WORKER', label: 'Profil performant' },
  { value: 'BALANCED', label: 'Profil équilibré' },
  { value: 'SOFT_WORKER', label: 'Profil souple' },
];

const SCORE_FIELDS = [
  { key: 'speed_score', label: 'Vitesse' },
  { key: 'punctuality_score', label: 'Ponctualité' },
  { key: 'presentation_score', label: 'Présentation' },
  { key: 'communication_score', label: 'Communication' },
  { key: 'teamwork_score', label: 'Travail d\'équipe' },
  { key: 'discipline_score', label: 'Discipline' },
  { key: 'endurance_score', label: 'Endurance' },
] as const;

export default function ServerForm({ mode, initialData, onSuccess, onCancel }: ServerFormProps) {
  const [cities, setCities] = useState<City[]>([]);
  const [loadingCities, setLoadingCities] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState<Partial<ServerCreateRequest & ServerUpdateRequest>>({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    gender: '',
    city_id: '',
    years_experience: 0,
    worker_type: 'BALANCED',
    speed_score: 5,
    punctuality_score: 5,
    presentation_score: 5,
    communication_score: 5,
    teamwork_score: 5,
    discipline_score: 5,
    endurance_score: 5,
    is_active: true,
  });

  useEffect(() => {
    async function loadCities() {
      try {
        const data = await getCities();
        setCities(data);
        if (data.length > 0 && !form.city_id && !initialData?.city_id) {
          setForm((f) => ({ ...f, city_id: data[0].id }));
        }
      } catch {
        setError('Impossible de charger les villes.');
      } finally {
        setLoadingCities(false);
      }
    }
    loadCities();
  }, []);

  useEffect(() => {
    if (initialData) {
      setForm({
        first_name: initialData.first_name || '',
        last_name: initialData.last_name || '',
        email: initialData.email || '',
        phone: initialData.phone || '',
        gender: initialData.gender || '',
        city_id: initialData.city_id || '',
        years_experience: initialData.years_experience || 0,
        worker_type: initialData.worker_type || 'BALANCED',
        speed_score: initialData.speed_score || 5,
        punctuality_score: initialData.punctuality_score || 5,
        presentation_score: initialData.presentation_score || 5,
        communication_score: initialData.communication_score || 5,
        teamwork_score: initialData.teamwork_score || 5,
        discipline_score: initialData.discipline_score || 5,
        endurance_score: initialData.endurance_score || 5,
        is_active: initialData.is_active !== undefined ? initialData.is_active : true,
      });
    }
  }, [initialData]);

  const validateForm = (): string | null => {
    if (!form.first_name?.trim()) return 'Le prénom est requis.';
    if (!form.last_name?.trim()) return 'Le nom est requis.';
    if (!form.email?.trim()) return 'L\'email est requis.';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email || '')) return 'Format d\'email invalide.';
    if (!form.phone?.trim()) return 'Le téléphone est requis.';
    if (!form.gender) return 'Le genre est requis.';
    if (!form.city_id) return 'La ville est requise.';
    if (form.years_experience !== undefined && form.years_experience < 0) return 'L\'expérience ne peut pas être négative.';
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const payload: ServerCreateRequest | ServerUpdateRequest = {
        first_name: form.first_name!,
        last_name: form.last_name!,
        email: form.email!,
        phone: form.phone!,
        gender: form.gender!,
        city_id: form.city_id!,
        years_experience: form.years_experience!,
        worker_type: form.worker_type,
        speed_score: form.speed_score,
        punctuality_score: form.punctuality_score,
        presentation_score: form.presentation_score,
        communication_score: form.communication_score,
        teamwork_score: form.teamwork_score,
        discipline_score: form.discipline_score,
        endurance_score: form.endurance_score,
        is_active: form.is_active,
      };

      let serverId: string;

      if (mode === 'create') {
        const result = await createServer(payload as ServerCreateRequest);
        serverId = result.id;
      } else {
        await updateServer(initialData!.id, payload as ServerUpdateRequest);
        serverId = initialData!.id;
      }

      onSuccess?.(serverId);
    } catch (err) {
      setError(err instanceof Error ? err.message : `Impossible de ${mode === 'create' ? 'créer' : 'modifier'} le serveur.`);
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
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
          {error}
        </div>
      )}

      <div className={sectionClass}>
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <svg className="w-5 h-5 text-[#D4AF37]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
          Identité
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="server-first-name" className="block text-sm font-medium text-gray-700 mb-1">Prénom *</label>
            <input
              id="server-first-name"
              type="text"
              required
              value={form.first_name}
              onChange={(e) => setForm({ ...form, first_name: e.target.value })}
              className={inputClass}
            />
          </div>
          <div>
            <label htmlFor="server-last-name" className="block text-sm font-medium text-gray-700 mb-1">Nom *</label>
            <input
              id="server-last-name"
              type="text"
              required
              value={form.last_name}
              onChange={(e) => setForm({ ...form, last_name: e.target.value })}
              className={inputClass}
            />
          </div>
          <div>
            <label htmlFor="server-email" className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
            <input
              id="server-email"
              type="email"
              required
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className={inputClass}
            />
          </div>
          <div>
            <label htmlFor="server-phone" className="block text-sm font-medium text-gray-700 mb-1">Téléphone *</label>
            <input
              id="server-phone"
              type="tel"
              required
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
              className={inputClass}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
          <div>
            <label htmlFor="server-gender" className="block text-sm font-medium text-gray-700 mb-1">Genre *</label>
            <select
              id="server-gender"
              required
              value={form.gender}
              onChange={(e) => setForm({ ...form, gender: e.target.value })}
              className={inputClass}
            >
              <option value="">Sélectionner</option>
              {GENDER_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="server-city" className="block text-sm font-medium text-gray-700 mb-1">Ville *</label>
            <select
              id="server-city"
              required
              value={form.city_id}
              onChange={(e) => setForm({ ...form, city_id: e.target.value })}
              className={inputClass}
              disabled={loadingCities}
            >
              <option value="">Sélectionner une ville</option>
              {cities.map((city) => (
                <option key={city.id} value={city.id}>{city.name}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className={sectionClass}>
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <svg className="w-5 h-5 text-[#D4AF37]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
          Profil professionnel
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label htmlFor="server-experience" className="block text-sm font-medium text-gray-700 mb-1">Années d'expérience *</label>
            <input
              id="server-experience"
              type="number"
              required
              min={0}
              value={form.years_experience}
              onChange={(e) => setForm({ ...form, years_experience: parseInt(e.target.value) || 0 })}
              className={inputClass}
            />
          </div>
          <div>
            <label htmlFor="server-worker-type" className="block text-sm font-medium text-gray-700 mb-1">Type de travailleur</label>
            <select
              id="server-worker-type"
              value={form.worker_type}
              onChange={(e) => setForm({ ...form, worker_type: e.target.value })}
              className={inputClass}
            >
              {WORKER_TYPE_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="server-active" className="block text-sm font-medium text-gray-700 mb-1">Actif</label>
            <select
              id="server-active"
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

      <div className={sectionClass}>
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <svg className="w-5 h-5 text-[#D4AF37]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-5.618 3.984A7.015 7.015 0 0012 21" />
          </svg>
          Scores de compétences (1-10)
        </h3>
        <p className="text-sm text-gray-500 mb-4">Évaluez les compétences clés du serveur sur une échelle de 1 à 10.</p>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {SCORE_FIELDS.map(({ key, label }) => (
            <div key={key}>
              <label htmlFor={`server-${key}`} className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
              <input
                id={`server-${key}`}
                type="number"
                min={1}
                max={10}
                value={form[key]}
                onChange={(e) => setForm({ ...form, [key]: parseInt(e.target.value) || 5 })}
                className={inputClass}
              />
            </div>
          ))}
        </div>
      </div>

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
          {submitting ? (mode === 'create' ? 'Création...' : 'Modification...') : (mode === 'create' ? 'Créer le serveur' : 'Enregistrer les modifications')}
        </button>
      </div>
    </form>
  );
}