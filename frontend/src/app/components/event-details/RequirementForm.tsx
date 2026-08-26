'use client';

import { useState, useEffect } from 'react';
import { useFocusTrap } from '@/app/components/ui/FocusTrap';
import { RequirementCreateRequest, RequirementUpdateRequest, getCities, City } from '@/app/lib/api';

interface RequirementFormProps {
  onClose: () => void;
  onSave: (data: RequirementCreateRequest | RequirementUpdateRequest) => Promise<void>;
  initial?: {
    role_name: string;
    quantity: number;
    minimum_skill_level: number;
    minimum_experience: number;
    required_gender: string | null;
  };
  saving?: boolean;
}

const ROLES = [
  'Manager',
  'Maître d\'hôtel',
  'Barman',
  'Food',
];

const GENDERS = [
  { value: null, label: 'Indifférent' },
  { value: 'MALE', label: 'Homme' },
  { value: 'FEMALE', label: 'Femme' },
];

export default function RequirementForm({ onClose, onSave, initial, saving = false }: RequirementFormProps) {
  const [cities, setCities] = useState<City[]>([]);
  const [loadingCities, setLoadingCities] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [role, setRole] = useState(initial?.role_name || '');
  const [quantity, setQuantity] = useState(initial?.quantity || 1);
  const [skill, setSkill] = useState(initial?.minimum_skill_level || 1);
  const [experience, setExperience] = useState(initial?.minimum_experience || 0);
  const [gender, setGender] = useState<string | null>(initial?.required_gender || null);

  const containerRef = useFocusTrap({ onClose, closeOnEscape: true, restoreFocus: true });

  useEffect(() => {
    async function loadCities() {
      try {
        const data = await getCities();
        setCities(data);
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
    setError(null);

    if (!role.trim()) {
      setError('Le rôle est requis.');
      return;
    }
    if (quantity < 1) {
      setError('La quantité doit être au moins 1.');
      return;
    }
    if (skill < 1 || skill > 10) {
      setError('Le niveau de compétence doit être entre 1 et 10.');
      return;
    }
    if (experience < 0) {
      setError('L\'expérience ne peut pas être négative.');
      return;
    }

    await onSave({
      role_name: role.trim(),
      quantity,
      minimum_skill_level: skill,
      minimum_experience: experience,
      required_gender: gender,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="requirement-form-dialog-title">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div ref={containerRef} className="relative bg-white rounded-xl border border-gray-200 shadow-2xl w-full max-w-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 id="requirement-form-dialog-title" className="text-lg font-semibold text-gray-900">
            {initial ? 'Modifier le poste' : 'Ajouter un poste'}
          </h3>
          <button
            onClick={onClose}
            aria-label="Fermer"
            className="p-1 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="requirement-role" className="block text-sm font-medium text-gray-700 mb-1">Poste / rôle *</label>
            <select
              id="requirement-role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
            >
              <option value="">Sélectionner un poste</option>
              {ROLES.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="requirement-quantity" className="block text-sm font-medium text-gray-700 mb-1">Nombre demandé *</label>
              <input
                id="requirement-quantity"
                type="number"
                min={1}
                value={quantity}
                onChange={(e) => setQuantity(parseInt(e.target.value) || 1)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
              />
            </div>
            <div>
              <label htmlFor="requirement-gender" className="block text-sm font-medium text-gray-700 mb-1">Genre</label>
              <select
                id="requirement-gender"
                value={gender || ''}
                onChange={(e) => setGender(e.target.value ? (e.target.value as 'MALE' | 'FEMALE') : null)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
              >
                {GENDERS.map((g) => (
                  <option key={g.value ?? 'any'} value={g.value ?? ''}>{g.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="requirement-skill" className="block text-sm font-medium text-gray-700 mb-1">Niveau minimum (1-10)</label>
              <input
                id="requirement-skill"
                type="number"
                min={1}
                max={10}
                value={skill}
                onChange={(e) => setSkill(parseInt(e.target.value) || 1)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
              />
            </div>
            <div>
              <label htmlFor="requirement-experience" className="block text-sm font-medium text-gray-700 mb-1">Expérience minimum (années)</label>
              <input
                id="requirement-experience"
                type="number"
                min={0}
                value={experience}
                onChange={(e) => setExperience(parseInt(e.target.value) || 0)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-[#D4AF37] text-white hover:bg-[#B8941E] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {saving ? 'Enregistrement...' : initial ? 'Enregistrer' : 'Ajouter'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
