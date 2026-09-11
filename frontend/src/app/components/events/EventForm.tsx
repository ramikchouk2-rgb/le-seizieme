'use client';

import { useState, useEffect, useMemo } from 'react';
import { City, EventCreateRequest, EventUpdateRequest, createEvent, updateEvent, getCities, RequirementCreateRequest } from '@/app/lib/api';

interface RequirementForm {
  role_name: string;
  quantity: number;
  required_gender: string | null;
  minimum_experience: number;
  minimum_skill_level: number;
}

interface EventFormProps {
  mode: 'create' | 'edit';
  initialData?: EventCreateRequest | null;
  initialRequirements?: RequirementCreateRequest[];
  onSuccess?: (eventId: string) => void;
  onCancel?: () => void;
}

const GENDER_OPTIONS = [
  { value: 'MALE', label: 'Homme' },
  { value: 'FEMALE', label: 'Femme' },
  { value: 'OTHER', label: 'Autre' },
];

const PRIORITY_OPTIONS = [
  { value: 'NORMAL', label: 'Normal' },
  { value: 'PRIORITY', label: 'Prioritaire' },
  { value: 'URGENT', label: 'Urgent' },
];

const STATUS_OPTIONS = [
  { value: 'PLANNED', label: 'Planifié' },
  { value: 'STAFFING', label: 'Staffing' },
  { value: 'CONFIRMED', label: 'Confirmé' },
  { value: 'IN_PROGRESS', label: 'En cours' },
  { value: 'COMPLETED', label: 'Terminé' },
  { value: 'CANCELLED', label: 'Annulé' },
];

export default function EventForm({ mode, initialData, initialRequirements, onSuccess, onCancel }: EventFormProps) {
  const [cities, setCities] = useState<City[]>([]);
  const [loadingCities, setLoadingCities] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState<EventCreateRequest>({
    name: '',
    client_name: '',
    city_id: '',
    address: '',
    start_datetime: '',
    end_datetime: '',
    guest_count: 1,
    event_type: '',
    alcohol_service: false,
    food_products_count: 0,
    priority: 'NORMAL',
    is_urgent: false,
    required_response_minutes: undefined,
    status: 'PLANNED',
    notes: '',
  });

  const [requirements, setRequirements] = useState<RequirementForm[]>([]);

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
        name: initialData.name || '',
        client_name: initialData.client_name || '',
        city_id: initialData.city_id || '',
        address: initialData.address || '',
        start_datetime: initialData.start_datetime || '',
        end_datetime: initialData.end_datetime || '',
        guest_count: initialData.guest_count || 1,
        event_type: initialData.event_type || '',
        alcohol_service: initialData.alcohol_service || false,
        food_products_count: initialData.food_products_count || 0,
        priority: initialData.priority || 'NORMAL',
        is_urgent: initialData.is_urgent || false,
        required_response_minutes: initialData.required_response_minutes,
        status: initialData.status || 'PLANNED',
        notes: initialData.notes || '',
      });
    }
    if (initialRequirements) {
      setRequirements(initialRequirements.map(r => ({
        role_name: r.role_name,
        quantity: r.quantity,
        required_gender: r.required_gender || null,
        minimum_experience: r.minimum_experience || 0,
        minimum_skill_level: r.minimum_skill_level || 1,
      })));
    }
  }, [initialData, initialRequirements]);

  const totalPositions = useMemo(() => requirements.reduce((sum, r) => sum + r.quantity, 0), [requirements]);
  const requirementTypes = useMemo(() => requirements.length, [requirements]);

  const validateForm = (): string | null => {
    if (!form.name.trim()) return 'Le nom de l\'événement est requis.';
    if (!form.client_name.trim()) return 'Le nom du client est requis.';
    if (!form.city_id) return 'La ville est requise.';
    if (!form.address.trim()) return 'L\'adresse est requise.';
    if (!form.start_datetime) return 'La date de début est requise.';
    if (!form.end_datetime) return 'La date de fin est requise.';
    if (!form.event_type.trim()) return 'Le type d\'événement est requis.';
    if (form.guest_count < 1) return 'Le nombre d\'invités doit être au moins 1.';

    const start = new Date(form.start_datetime);
    const end = new Date(form.end_datetime);
    if (isNaN(start.getTime()) || isNaN(end.getTime())) return 'Format de date invalide.';
    if (end <= start) return 'La date de fin doit être postérieure à la date de début.';

    if (requirements.length > 0) {
      for (let i = 0; i < requirements.length; i++) {
        const r = requirements[i];
        if (!r.role_name.trim()) return `Le poste du besoin #${i + 1} est requis.`;
        if (r.quantity < 1) return `La quantité du besoin #${i + 1} doit être au moins 1.`;
        if (r.minimum_experience < 0) return `L'expérience du besoin #${i + 1} ne peut pas être négative.`;
        if (r.minimum_skill_level < 1 || r.minimum_skill_level > 10) return `Le niveau de compétence du besoin #${i + 1} doit être entre 1 et 10.`;
        if (r.required_gender && !['MALE', 'FEMALE', 'OTHER'].includes(r.required_gender)) {
          return `Le sexe requis du besoin #${i + 1} est invalide.`;
        }
      }
    }

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
      const payload: EventCreateRequest | EventUpdateRequest = {
        ...form,
        start_datetime: new Date(form.start_datetime).toISOString(),
        end_datetime: new Date(form.end_datetime).toISOString(),
      };

      let eventId: string;

      if (mode === 'create') {
        const result = await createEvent(payload as EventCreateRequest);
        eventId = result.id;

        if (requirements.length > 0) {
          for (const req of requirements) {
            await fetch(`/api/events/${eventId}/requirements`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(req),
            });
          }
        }
      } else {
        await updateEvent(form.id || '', payload as EventUpdateRequest);
        eventId = form.id || '';
      }

      onSuccess?.(eventId);
    } catch (err) {
      setError(err instanceof Error ? err.message : `Impossible de ${mode === 'create' ? 'créer' : 'modifier'} l'événement.`);
    } finally {
      setSubmitting(false);
    }
  };

  const addRequirement = () => {
    setRequirements([...requirements, {
      role_name: '',
      quantity: 1,
      required_gender: null,
      minimum_experience: 0,
      minimum_skill_level: 1,
    }]);
  };

  const removeRequirement = (index: number) => {
    setRequirements(requirements.filter((_, i) => i !== index));
  };

  const updateRequirement = (index: number, field: keyof RequirementForm, value: string | number | null) => {
    setRequirements(requirements.map((r, i) => i === index ? { ...r, [field]: value } : r));
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
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
          </svg>
          Informations générales
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="event-name" className="block text-sm font-medium text-gray-700 mb-1">Nom de l'événement *</label>
            <input
              id="event-name"
              type="text"
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className={inputClass}
            />
          </div>
          <div>
            <label htmlFor="client-name" className="block text-sm font-medium text-gray-700 mb-1">Client *</label>
            <input
              id="client-name"
              type="text"
              required
              value={form.client_name}
              onChange={(e) => setForm({ ...form, client_name: e.target.value })}
              className={inputClass}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="event-city" className="block text-sm font-medium text-gray-700 mb-1">Ville *</label>
            <select
              id="event-city"
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
          <div>
            <label htmlFor="event-address" className="block text-sm font-medium text-gray-700 mb-1">Adresse *</label>
            <input
              id="event-address"
              type="text"
              required
              value={form.address}
              onChange={(e) => setForm({ ...form, address: e.target.value })}
              className={inputClass}
            />
          </div>
        </div>
      </div>

      <div className={sectionClass}>
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <svg className="w-5 h-5 text-[#D4AF37]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          Planning
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="event-start" className="block text-sm font-medium text-gray-700 mb-1">Date et heure de début *</label>
            <input
              id="event-start"
              type="datetime-local"
              required
              value={form.start_datetime}
              onChange={(e) => setForm({ ...form, start_datetime: e.target.value })}
              className={inputClass}
            />
          </div>
          <div>
            <label htmlFor="event-end" className="block text-sm font-medium text-gray-700 mb-1">Date et heure de fin *</label>
            <input
              id="event-end"
              type="datetime-local"
              required
              value={form.end_datetime}
              onChange={(e) => setForm({ ...form, end_datetime: e.target.value })}
              className={inputClass}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
          <div>
            <label htmlFor="event-guests" className="block text-sm font-medium text-gray-700 mb-1">Nombre d'invités *</label>
            <input
              id="event-guests"
              type="number"
              required
              min={1}
              value={form.guest_count}
              onChange={(e) => setForm({ ...form, guest_count: parseInt(e.target.value) || 1 })}
              className={inputClass}
            />
          </div>
          <div>
            <label htmlFor="event-type" className="block text-sm font-medium text-gray-700 mb-1">Type d'événement *</label>
            <input
              id="event-type"
              type="text"
              required
              value={form.event_type}
              onChange={(e) => setForm({ ...form, event_type: e.target.value })}
              className={inputClass}
            />
          </div>
          <div>
            <label htmlFor="event-priority" className="block text-sm font-medium text-gray-700 mb-1">Priorité</label>
            <select
              id="event-priority"
              value={form.priority}
              onChange={(e) => setForm({ ...form, priority: e.target.value })}
              className={inputClass}
            >
              {PRIORITY_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className={sectionClass}>
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <svg className="w-5 h-5 text-[#D4AF37]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          Configuration
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="event-status" className="block text-sm font-medium text-gray-700 mb-1">Statut</label>
            <select
              id="event-status"
              value={form.status}
              onChange={(e) => setForm({ ...form, status: e.target.value })}
              className={inputClass}
            >
              {STATUS_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2 mt-6">
            <input
              type="checkbox"
              id="is_urgent"
              checked={form.is_urgent}
              onChange={(e) => setForm({ ...form, is_urgent: e.target.checked })}
              className="h-4 w-4 rounded border-gray-300 text-[#D4AF37] focus:ring-[#D4AF37]"
            />
            <label htmlFor="is_urgent" className="text-sm font-medium text-gray-700">
              Événement urgent
            </label>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="alcohol_service"
              checked={form.alcohol_service}
              onChange={(e) => setForm({ ...form, alcohol_service: e.target.checked })}
              className="h-4 w-4 rounded border-gray-300 text-[#D4AF37] focus:ring-[#D4AF37]"
            />
            <label htmlFor="alcohol_service" className="text-sm font-medium text-gray-700">
              Service d'alcool
            </label>
          </div>
          <div>
            <label htmlFor="event-food" className="block text-sm font-medium text-gray-700 mb-1">Produits alimentaires</label>
            <input
              id="event-food"
              type="number"
              min={0}
              value={form.food_products_count}
              onChange={(e) => setForm({ ...form, food_products_count: parseInt(e.target.value) || 0 })}
              className={inputClass}
            />
          </div>
        </div>
      </div>

      <div className={sectionClass}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <svg className="w-5 h-5 text-[#D4AF37]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
            Besoins en personnel
          </h3>
          <button
            type="button"
            onClick={addRequirement}
            disabled={submitting}
            className="px-3 py-1.5 text-sm font-medium rounded-lg bg-[#D4AF37] text-white hover:bg-[#B8941E] transition-colors disabled:opacity-50"
          >
            + Ajouter un besoin
          </button>
        </div>

        {requirements.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <p className="mb-2">Aucun besoin en personnel défini.</p>
            <p className="text-sm">Cliquez sur "Ajouter un besoin" pour définir les postes requis.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {requirements.map((req, index) => (
              <div key={index} className="bg-white rounded-lg border border-gray-200 p-4">
                <div className="flex items-start justify-between gap-4 mb-3">
                  <h4 className="font-medium text-gray-900">Besoin #{index + 1}</h4>
                  <button
                    type="button"
                    onClick={() => removeRequirement(index)}
                    disabled={submitting}
                    className="p-1 text-gray-400 hover:text-red-500 transition-colors disabled:opacity-50"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Poste / Type *</label>
                    <input
                      type="text"
                      required
                      value={req.role_name}
                      onChange={(e) => updateRequirement(index, 'role_name', e.target.value)}
                      className={inputClass}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Quantité *</label>
                    <input
                      type="number"
                      required
                      min={1}
                      value={req.quantity}
                      onChange={(e) => updateRequirement(index, 'quantity', parseInt(e.target.value) || 1)}
                      className={inputClass}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Sexe requis</label>
                    <select
                      value={req.required_gender || ''}
                      onChange={(e) => updateRequirement(index, 'required_gender', e.target.value || null)}
                      className={inputClass}
                    >
                      <option value="">Non spécifié</option>
                      {GENDER_OPTIONS.map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Expérience min. (années)</label>
                    <input
                      type="number"
                      min={0}
                      value={req.minimum_experience}
                      onChange={(e) => updateRequirement(index, 'minimum_experience', parseInt(e.target.value) || 0)}
                      className={inputClass}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Niveau compétence (1-10)</label>
                    <input
                      type="number"
                      min={1}
                      max={10}
                      value={req.minimum_skill_level}
                      onChange={(e) => updateRequirement(index, 'minimum_skill_level', parseInt(e.target.value) || 1)}
                      className={inputClass}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="mt-6 p-4 bg-white rounded-lg border border-gray-200">
          <h4 className="font-medium text-gray-900 mb-3">Résumé</h4>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
            <div>
              <p className="text-gray-500">Postes totaux</p>
              <p className="font-bold text-gray-900">{totalPositions}</p>
            </div>
            <div>
              <p className="text-gray-500">Types de postes</p>
              <p className="font-bold text-gray-900">{requirementTypes}</p>
            </div>
            <div>
              <p className="text-gray-500">Invités</p>
              <p className="font-bold text-gray-900">{form.guest_count}</p>
            </div>
            <div>
              <p className="text-gray-500">Ville</p>
              <p className="font-bold text-gray-900">
                {cities.find(c => c.id === form.city_id)?.name || '—'}
              </p>
            </div>
            <div>
              <p className="text-gray-500">Date</p>
              <p className="font-bold text-gray-900">
                {form.start_datetime ? new Date(form.start_datetime).toLocaleDateString('fr-FR') : '—'}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className={sectionClass}>
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <svg className="w-5 h-5 text-[#D4AF37]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 15l-3-3m0 0l3-3m-3 3h8M3 12a9 9 0 1118 0 9 9 0 01-18 0z" />
          </svg>
          Notes
        </h3>
        <textarea
          id="event-notes"
          value={form.notes}
          onChange={(e) => setForm({ ...form, notes: e.target.value })}
          rows={3}
          className={inputClass}
          placeholder="Notes additionnelles..."
        />
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
          {submitting ? (mode === 'create' ? 'Création...' : 'Modification...') : (mode === 'create' ? 'Créer l\'événement' : 'Enregistrer les modifications')}
        </button>
      </div>
    </form>
  );
}