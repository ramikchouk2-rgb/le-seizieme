import { EventDetailData, StaffAssignment } from '@/app/components/dashboard/types';

export function getEventDurationHours(start: string, end: string): number {
  const startDate = new Date(start);
  const endDate = new Date(end);
  const diffMs = endDate.getTime() - startDate.getTime();
  return Math.round(diffMs / (1000 * 60 * 60));
}

export function getAverageScore(assignments: StaffAssignment[]): number {
  if (assignments.length === 0) return 0;
  const sum = assignments.reduce((acc, a) => acc + (a.score ?? 0), 0);
  return Math.round((sum / assignments.length) * 10) / 10;
}
