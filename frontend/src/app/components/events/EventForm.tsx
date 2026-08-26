'use client';

import { useState, useEffect } from 'react';
import { City, EventCreateRequest, createEvent, getCities } from '@/app/lib/api';

interface EventFormProps {
  onSuccess?: (eventId: string) => void;
  onCancel?: () => void;
}

export default function EventForm({ onSuccess, onCancel }: EventFormProps) {
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

  useEffect(() => {
    async function loadCities() {
      try {
        const data = await getCities();
        setCities(data);
        if (data.length > 0 && !form.city_id) {
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const result = await createEvent(form);
      onSuccess?.(result.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible de créer l\'événement.');
    } finally {
      setSubmitting(false);
    }
  };

  const inputClass =
    'w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]';

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
          {error}
        </div>
      )}

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

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label htmlFor="event-start" className="block text-sm font-medium text-gray-700 mb-1">Date de début *</label>
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
          <label htmlFor="event-end" className="block text-sm font-medium text-gray-700 mb-1">Date de fin *</label>
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

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
            <option value="NORMAL">Normal</option>
            <option value="PRIORITY">Prioritaire</option>
            <option value="URGENT">Urgent</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label htmlFor="event-status" className="block text-sm font-medium text-gray-700 mb-1">Statut</label>
          <select
            id="event-status"
            value={form.status}
            onChange={(e) => setForm({ ...form, status: e.target.value })}
            className={inputClass}
          >
            <option value="PLANNED">Planifié</option>
            <option value="STAFFING">Staffing</option>
            <option value="CONFIRMED">Confirmé</option>
            <option value="IN_PROGRESS">En cours</option>
            <option value="COMPLETED">Terminé</option>
            <option value="CANCELLED">Annulé</option>
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
            Urgent
          </label>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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

      <div>
        <label htmlFor="event-notes" className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
        <textarea
          id="event-notes"
          value={form.notes}
          onChange={(e) => setForm({ ...form, notes: e.target.value })}
          rows={3}
          className={inputClass}
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
          {submitting ? 'Création...' : 'Créer l\'événement'}
        </button>
      </div>
    </form>
  );
}
