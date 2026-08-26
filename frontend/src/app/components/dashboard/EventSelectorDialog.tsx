'use client';

import { useState, useEffect, useCallback } from 'react';
import { EventListItem, getEvents } from '@/app/lib/api';
import { useFocusTrap } from '@/app/components/ui/FocusTrap';

interface EventSelectorDialogProps {
  open: boolean;
  onClose: () => void;
  onSelect: (event: EventListItem) => void;
  loading?: boolean;
  title?: string;
}

export default function EventSelectorDialog({
  open,
  onClose,
  onSelect,
  loading = false,
  title = 'Sélectionner un événement',
}: EventSelectorDialogProps) {
  const [events, setEvents] = useState<EventListItem[]>([]);
  const [search, setSearch] = useState('');
  const [loadingEvents, setLoadingEvents] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const containerRef = useFocusTrap({ onClose, closeOnEscape: true, restoreFocus: true });

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    }
  }, [onClose]);

  useEffect(() => {
    if (open) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [open, handleKeyDown]);

  useEffect(() => {
    if (!open) return;
    setLoadingEvents(true);
    setError(null);
    getEvents({ date_range: 'UPCOMING', page: 1, page_size: 20 })
      .then((data) => setEvents(data.items))
      .catch(() => setError('Impossible de charger les événements.'))
      .finally(() => setLoadingEvents(false));
  }, [open]);

  const filtered = events.filter((ev) =>
    ev.name.toLowerCase().includes(search.toLowerCase()) ||
    ev.city.toLowerCase().includes(search.toLowerCase()),
  );

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="event-selector-dialog-title">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div ref={containerRef} className="relative bg-white rounded-xl border border-gray-200 shadow-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h3 id="event-selector-dialog-title" className="text-lg font-semibold text-gray-900">{title}</h3>
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

        <div className="p-6">
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
              {error}
            </div>
          )}

          <input
            type="text"
            placeholder="Rechercher un événement..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/30 focus:border-[#D4AF37] mb-4"
          />

          {loadingEvents ? (
            <p className="text-sm text-gray-500">Chargement...</p>
          ) : filtered.length === 0 ? (
            <p className="text-sm text-gray-500">Aucun événement trouvé.</p>
          ) : (
            <div className="space-y-2 max-h-[50vh] overflow-y-auto">
              {filtered.map((ev) => (
                <button
                  key={ev.id}
                  onClick={() => onSelect(ev)}
                  disabled={loading}
                  className="w-full text-left p-4 rounded-lg border border-gray-200 hover:border-[#D4AF37] hover:bg-[#D4AF37]/5 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{ev.name}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        {ev.city} • {new Date(ev.start_datetime).toLocaleDateString('fr-FR')} • {ev.guest_count} invités
                      </p>
                    </div>
                    <div className="text-right">
                      <span className={`text-xs px-2 py-1 rounded-full ${
                        ev.urgent ? 'bg-red-100 text-red-700' :
                        ev.status === 'PLANNED' ? 'bg-blue-100 text-blue-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>
                        {ev.urgent ? 'Urgent' : ev.status}
                      </span>
                      <p className="text-xs text-gray-500 mt-1">
                        {ev.staffing.selected}/{ev.staffing.requested} staff
                      </p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
