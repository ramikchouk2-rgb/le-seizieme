'use client';

import { useState, useEffect } from 'react';
import { useFocusTrap } from '@/app/components/ui/FocusTrap';

interface EvaluationFormItem {
  id: string;
  server_id: string;
  server_name: string;
  role: string;
  punctuality: number;
  work_quality: number;
  presentation: number;
  teamwork: number;
  client_relation: number;
  comment?: string | null;
}

interface EvaluationFormProps {
  onClose: () => void;
  onSave: (data: { server_id: string; punctuality: number; work_quality: number; presentation: number; teamwork: number; client_relation: number; comment?: string | null }) => Promise<void>;
  servers: { server_id: string; server_name: string; role?: string }[];
  initial?: EvaluationFormItem | null;
  saving?: boolean;
}

export default function EvaluationForm({ onClose, onSave, servers, initial, saving = false }: EvaluationFormProps) {
  const [serverId, setServerId] = useState(initial?.server_id || '');
  const [punctuality, setPunctuality] = useState(initial?.punctuality || 5);
  const [workQuality, setWorkQuality] = useState(initial?.work_quality || 5);
  const [presentation, setPresentation] = useState(initial?.presentation || 5);
  const [teamwork, setTeamwork] = useState(initial?.teamwork || 5);
  const [clientRelation, setClientRelation] = useState(initial?.client_relation || 5);
  const [comment, setComment] = useState(initial?.comment || '');
  const [error, setError] = useState('');

  const containerRef = useFocusTrap({ onClose, closeOnEscape: true, restoreFocus: true });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!serverId) {
      setError('Veuillez sélectionner un serveur.');
      return;
    }

    await onSave({
      server_id: serverId,
      punctuality,
      work_quality: workQuality,
      presentation,
      teamwork,
      client_relation: clientRelation,
      comment: comment || null,
    });
  };

  const ScoreSlider = ({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) => (
    <div>
      <div className="flex items-center justify-between mb-1">
        <label className="block text-sm font-medium text-gray-700">{label}</label>
        <span className="text-sm font-bold text-[#D4AF37]">{value}/10</span>
      </div>
      <input
        type="range"
        min={1}
        max={10}
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value))}
        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-[#D4AF37]"
      />
      <div className="flex justify-between text-xs text-gray-400 mt-1">
        <span>1</span>
        <span>5</span>
        <span>10</span>
      </div>
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="evaluation-form-dialog-title">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div ref={containerRef} className="relative bg-white rounded-xl border border-gray-200 shadow-2xl w-full max-w-lg p-6">
        <h3 id="evaluation-form-dialog-title" className="text-lg font-semibold text-gray-900 mb-4">
          {initial ? 'Modifier l\'évaluation' : 'Nouvelle évaluation'}
        </h3>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-50 text-red-700 text-sm border border-red-200">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="evaluation-server" className="block text-sm font-medium text-gray-700 mb-1">Serveur *</label>
            <select
              id="evaluation-server"
              value={serverId}
              onChange={(e) => setServerId(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
              disabled={!!initial}
            >
              <option value="">Sélectionner un serveur</option>
              {servers.map((s) => (
                <option key={s.server_id} value={s.server_id}>
                  {s.role ? `${s.server_name} — ${s.role}` : s.server_name}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-3">
            <ScoreSlider label="Ponctualité" value={punctuality} onChange={setPunctuality} />
            <ScoreSlider label="Qualité du travail" value={workQuality} onChange={setWorkQuality} />
            <ScoreSlider label="Présentation" value={presentation} onChange={setPresentation} />
            <ScoreSlider label="Esprit d'équipe" value={teamwork} onChange={setTeamwork} />
            <ScoreSlider label="Relation client" value={clientRelation} onChange={setClientRelation} />
          </div>

          <div>
            <label htmlFor="evaluation-comment" className="block text-sm font-medium text-gray-700 mb-1">Commentaire (optionnel)</label>
            <textarea
              id="evaluation-comment"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={3}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37]"
              placeholder="Commentaire sur la performance..."
            />
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
              {saving ? 'Enregistrement...' : initial ? 'Mettre à jour' : 'Enregistrer'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
