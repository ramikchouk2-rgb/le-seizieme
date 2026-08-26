'use client';

import { useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import Header from '@/app/components/dashboard/Header';
import EventReportHeader from '@/app/components/event-report/EventReportHeader';
import EventReportKpiCards from '@/app/components/event-report/EventReportKpiCards';
import EventReportStaffTable from '@/app/components/event-report/EventReportStaffTable';
import EventReportEvaluations from '@/app/components/event-report/EventReportEvaluations';
import EventReportAttendance from '@/app/components/event-report/EventReportAttendance';
import EventReportRequirements from '@/app/components/event-report/EventReportRequirements';
import EventReportTransport from '@/app/components/event-report/EventReportTransport';
import EventReportGamification from '@/app/components/event-report/EventReportGamification';
import EventReportAlerts from '@/app/components/event-report/EventReportAlerts';
import EventReportFinalSummary from '@/app/components/event-report/EventReportFinalSummary';
import { useEventReport } from '@/app/lib/hooks';
import { Spinner } from '@/app/lib/loading';

export default function EventReportPage() {
  const params = useParams();
  const eventId = params.eventId as string;

  const { data, isLoading, error, refetch } = useEventReport(eventId);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header title="Rapport final" />
        <main className="p-8">
          <div className="max-w-7xl mx-auto space-y-6">
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm">
              <Spinner size="lg" className="mx-auto mb-4 text-[#D4AF37]" />
              <p className="text-gray-500 text-sm">Génération du rapport...</p>
            </div>
          </div>
        </main>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header title="Rapport final" />
        <main className="p-8">
          <div className="max-w-7xl mx-auto">
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm">
              <p className="text-gray-500 text-sm mb-4">{error?.message || 'Impossible de charger le rapport.'}</p>
              <button
                onClick={() => refetch()}
                className="inline-flex items-center px-4 py-2 bg-[#D4AF37] text-white text-sm font-medium rounded-lg hover:bg-[#B8941E] transition-colors"
              >
                Réessayer
              </button>
            </div>
          </div>
        </main>
      </div>
    );
  }

  const report = data;
  const event = report.event as { name?: string; city?: string; start_datetime?: string; status?: string } | null;
  const kpis = report.final_kpis;

  return (
    <div className="min-h-screen bg-gray-50">
      <Header title="Rapport final" />
      <main className="p-4 md:p-8">
        <div className="max-w-7xl mx-auto space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <Link
                href={`/dashboard/events/${eventId}`}
                className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-2"
              >
                ← Retour à l'événement
              </Link>
            </div>
            <span className="text-xs text-gray-400">
              Généré le {new Date(report.generated_at).toLocaleDateString('fr-FR')}
            </span>
          </div>

          <EventReportHeader
            eventName={event?.name || report.event_name}
            city={event?.city || ''}
            date={event?.start_datetime ? new Date(event.start_datetime).toLocaleDateString('fr-FR') : ''}
            status={report.status}
            isFinal={report.is_final}
          />
          <EventReportKpiCards
            kpis={{
              staffing_rate: kpis.staffing_rate,
              attendance_rate: kpis.attendance_rate,
              requirement_fulfillment_rate: kpis.requirement_fulfillment_rate,
              transport_coverage_rate: kpis.transport_coverage_rate,
            }}
            totals={{
              totalStaff: report.staff.length,
              totalPoints: report.staff.reduce((sum, s) => sum + s.total_points, 0),
            }}
          />
          <EventReportStaffTable staff={report.staff} />
          <EventReportEvaluations evaluationSummary={report.evaluation_summary || {
            total_evaluated: 0,
            total_confirmed: 0,
            evaluation_coverage: 0,
            average_score: null,
            highest_score: null,
            lowest_score: null,
            excellent_count: 0,
            good_count: 0,
            average_count: 0,
            needs_improvement_count: 0,
          }} />
          <EventReportAttendance attendance={report.attendance} />
          <EventReportRequirements requirements={report.requirements} />
          <EventReportTransport transport={report.transport} />
          <EventReportGamification gamification={report.gamification} />
          <EventReportAlerts alerts={report.alerts} />
          <EventReportFinalSummary
            status={report.status}
            isFinal={report.is_final}
            kpis={{
              staffing_rate: kpis.staffing_rate,
              attendance_rate: kpis.attendance_rate,
              requirement_fulfillment_rate: kpis.requirement_fulfillment_rate,
              transport_coverage_rate: kpis.transport_coverage_rate,
            }}
          />
        </div>
      </main>
    </div>
  );
}
