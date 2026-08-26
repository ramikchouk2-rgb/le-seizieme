'use client';

import { useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import Header from '@/app/components/dashboard/Header';
import AttendanceSummary from '@/app/components/attendance/AttendanceSummary';
import AttendanceTable from '@/app/components/attendance/AttendanceTable';
import CheckInDialog from '@/app/components/attendance/CheckInDialog';
import CheckOutDialog from '@/app/components/attendance/CheckOutDialog';
import UpdateAttendanceDialog from '@/app/components/attendance/UpdateAttendanceDialog';
import InitializeAttendanceDialog from '@/app/components/attendance/InitializeAttendanceDialog';
import { useEventAttendance, useAttendanceSummary, useInitializeAttendance, useCheckInStaff, useCheckOutStaff, useUpdateAttendanceStatus } from '@/app/lib/hooks';
import { Spinner } from '@/app/lib/loading';
import { useAnnouncer } from '@/app/components/ui/Announcer';

type LoadingState = 'loading' | 'error' | 'success';

const STATUS_STYLES: Record<string, string> = {
  EXPECTED: 'bg-gray-50 text-gray-700 border-gray-200',
  PRESENT: 'bg-green-50 text-green-700 border-green-200',
  LATE: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  ABSENT: 'bg-red-50 text-red-700 border-red-200',
  EXCUSED: 'bg-blue-50 text-blue-700 border-blue-200',
  LEFT: 'bg-purple-50 text-purple-700 border-purple-200',
};

export default function EventAttendancePage() {
  const params = useParams();
  const eventId = params.eventId as string;
  const { announceSuccess, announceError } = useAnnouncer();

  const [showCheckIn, setShowCheckIn] = useState(false);
  const [showCheckOut, setShowCheckOut] = useState(false);
  const [showUpdate, setShowUpdate] = useState(false);
  const [showInitialize, setShowInitialize] = useState(false);
  const [selectedItem, setSelectedItem] = useState<{ id: string; server_name: string; role: string; status: string } | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: attendanceData, isLoading: attendanceLoading, error: attendanceError, refetch: refetchAttendance } = useEventAttendance(eventId);
  const { data: summaryData, isLoading: summaryLoading, error: summaryError, refetch: refetchSummary } = useAttendanceSummary(eventId);
  const initializeMutation = useInitializeAttendance();
  const checkInMutation = useCheckInStaff();
  const checkOutMutation = useCheckOutStaff();
  const updateStatusMutation = useUpdateAttendanceStatus();

  const items = attendanceData?.staff ?? [];
  const summary = summaryData;
  const isLoading = attendanceLoading || summaryLoading;
  const error = attendanceError?.message || summaryError?.message || null;

  const handleInitialize = async () => {
    try {
      await initializeMutation.mutateAsync(eventId);
      setShowInitialize(false);
      announceSuccess('Présence initialisée avec succès.');
    } catch (err) {
      announceError('Opération impossible. Veuillez réessayer.');
      throw err;
    }
  };

  const handleCheckIn = async (note?: string) => {
    if (!selectedItem) return;
    try {
      await checkInMutation.mutateAsync({ eventId, eventStaffId: selectedItem.id, note });
      setShowCheckIn(false);
      setSelectedItem(null);
      announceSuccess('Présence enregistrée.');
    } catch {
      announceError('Opération impossible. Veuillez réessayer.');
    }
  };

  const handleCheckOut = async (note?: string) => {
    if (!selectedItem) return;
    try {
      await checkOutMutation.mutateAsync({ eventId, eventStaffId: selectedItem.id, note });
      setShowCheckOut(false);
      setSelectedItem(null);
      announceSuccess('Départ enregistré.');
    } catch {
      announceError('Opération impossible. Veuillez réessayer.');
    }
  };

  const handleUpdateStatus = async (status: string, note?: string) => {
    if (!selectedItem) return;
    try {
      await updateStatusMutation.mutateAsync({ eventId, eventStaffId: selectedItem.id, status, note });
      setShowUpdate(false);
      setSelectedItem(null);
      announceSuccess('Statut de présence mis à jour.');
    } catch {
      announceError('Opération impossible. Veuillez réessayer.');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Header title="Suivi de présence" />
      <main className="p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between mb-6">
            <p className="text-gray-600">
              Gérez les présences et l'état de l'équipe pour cet événement.
            </p>
            <button
              onClick={() => setShowInitialize(true)}
              className="inline-flex items-center px-4 py-2 bg-[#D4AF37] text-white text-sm font-medium rounded-lg hover:bg-[#B8941E] transition-colors"
            >
              Initialiser les présences
            </button>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 text-sm text-red-700 flex items-center justify-between">
              <span>{error}</span>
              <button onClick={() => { refetchAttendance(); refetchSummary(); }} className="underline font-medium">
                Réessayer
              </button>
            </div>
          )}

          {isLoading ? (
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm">
              <Spinner size="lg" className="mx-auto mb-4 text-[#D4AF37]" />
              <p className="text-gray-500 text-sm">Chargement des présences...</p>
            </div>
          ) : (
            <>
              {summary && <AttendanceSummary summary={summary} statusStyles={STATUS_STYLES} />}

              <div className="mt-6">
                <AttendanceTable
                  items={items}
                  statusStyles={STATUS_STYLES}
                  onCheckIn={(item) => { setSelectedItem(item); setShowCheckIn(true); }}
                  onCheckOut={(item) => { setSelectedItem(item); setShowCheckOut(true); }}
                  onUpdate={(item) => { setSelectedItem(item); setShowUpdate(true); }}
                />
              </div>
            </>
          )}
        </div>
      </main>

      {showInitialize && (
        <InitializeAttendanceDialog
          onConfirm={handleInitialize}
          onClose={() => setShowInitialize(false)}
          loading={initializeMutation.isPending}
        />
      )}

      {showCheckIn && selectedItem && (
        <CheckInDialog
          item={selectedItem}
          onConfirm={handleCheckIn}
          onClose={() => { setShowCheckIn(false); setSelectedItem(null); }}
          loading={checkInMutation.isPending}
        />
      )}

      {showCheckOut && selectedItem && (
        <CheckOutDialog
          item={selectedItem}
          onConfirm={handleCheckOut}
          onClose={() => { setShowCheckOut(false); setSelectedItem(null); }}
          loading={checkOutMutation.isPending}
        />
      )}

      {showUpdate && selectedItem && (
        <UpdateAttendanceDialog
          item={selectedItem}
          onConfirm={handleUpdateStatus}
          onClose={() => { setShowUpdate(false); setSelectedItem(null); }}
          loading={updateStatusMutation.isPending}
        />
      )}
    </div>
  );
}
