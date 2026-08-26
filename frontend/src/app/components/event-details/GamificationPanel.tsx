'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { GamificationAwardResponse, awardCompletionPoints, awardPerformancePoints } from '@/app/lib/api';
import ConfirmGamificationActionDialog from './ConfirmGamificationActionDialog';

export default function GamificationPanel() {
  const params = useParams();
  const eventId = params.eventId as string;

  const [completionLoading, setCompletionLoading] = useState(false);
  const [performanceLoading, setPerformanceLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [completionDialogOpen, setCompletionDialogOpen] = useState(false);
  const [performanceDialogOpen, setPerformanceDialogOpen] = useState(false);

  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => setSuccess(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [success]);

  const handleAwardCompletion = async () => {
    setCompletionLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const result: GamificationAwardResponse = await awardCompletionPoints(eventId);
      setSuccess(`Points de présence attribués: ${result.points_awarded} points.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible d\'attribuer les points de présence.');
    } finally {
      setCompletionLoading(false);
      setCompletionDialogOpen(false);
    }
  };

  const handleAwardPerformance = async () => {
    setPerformanceLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const result: GamificationAwardResponse = await awardPerformancePoints(eventId);
      setSuccess(`Points de performance attribués: ${result.points_awarded} points.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible d\'attribuer les points de performance.');
    } finally {
      setPerformanceLoading(false);
      setPerformanceDialogOpen(false);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm mb-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Points de l'événement</h3>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {success && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-sm text-green-600">{success}</p>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-gray-50 rounded-lg p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Présence</p>
          <p className="text-sm font-medium text-gray-900 mt-1">Non attribués</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Performance</p>
          <p className="text-sm font-medium text-gray-900 mt-1">Non attribués</p>
        </div>
      </div>

      <div className="flex gap-3">
        <button
          onClick={() => setCompletionDialogOpen(true)}
          disabled={completionLoading}
          className="px-4 py-2 text-sm font-medium rounded-lg border border-[#D4AF37] text-[#D4AF37] hover:bg-[#D4AF37]/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {completionLoading ? 'Attribution...' : 'Attribuer les points de présence'}
        </button>
        <button
          onClick={() => setPerformanceDialogOpen(true)}
          disabled={performanceLoading}
          className="px-4 py-2 text-sm font-medium rounded-lg border border-[#D4AF37] text-[#D4AF37] hover:bg-[#D4AF37]/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {performanceLoading ? 'Attribution...' : 'Attribuer les points de performance'}
        </button>
      </div>

      <ConfirmGamificationActionDialog
        open={completionDialogOpen}
        onClose={() => setCompletionDialogOpen(false)}
        onConfirm={handleAwardCompletion}
        loading={completionLoading}
        title="Attribuer les points de présence ?"
        message="Les points de présence seront attribués aux serveurs confirmés pour cet événement."
        confirmLabel="Attribuer"
      />

      <ConfirmGamificationActionDialog
        open={performanceDialogOpen}
        onClose={() => setPerformanceDialogOpen(false)}
        onConfirm={handleAwardPerformance}
        loading={performanceLoading}
        title="Attribuer les points de performance ?"
        message="Les points de performance seront attribués aux serveurs ayant une évaluation valide."
        confirmLabel="Attribuer"
      />
    </div>
  );
}
