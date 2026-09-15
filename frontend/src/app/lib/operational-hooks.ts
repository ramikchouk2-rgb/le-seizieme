import { useQueries } from '@tanstack/react-query';
import type { UseQueryResult } from '@tanstack/react-query';
import {
  getEventOperations,
  getUrgentStatus,
  type EventOperationsResponse,
  type UrgentStatus,
} from '@/app/lib/api';

export function useEventOperationsBatch(eventIds: string[]): UseQueryResult<EventOperationsResponse, Error>[] {
  const ids = Array.from(new Set(eventIds.filter(Boolean)));
  return useQueries({
    queries: ids.map((eventId) => ({
      queryKey: ['eventOperations', eventId],
      queryFn: () => getEventOperations(eventId),
      enabled: Boolean(eventId),
      staleTime: 10 * 1000,
      refetchInterval: 30 * 1000,
    })),
  }) as UseQueryResult<EventOperationsResponse, Error>[];
}

export function useUrgentStatusBatch(eventIds: string[]): UseQueryResult<UrgentStatus, Error>[] {
  const ids = Array.from(new Set(eventIds.filter(Boolean)));
  return useQueries({
    queries: ids.map((eventId) => ({
      queryKey: ['urgentStatus', eventId],
      queryFn: () => getUrgentStatus(eventId),
      enabled: Boolean(eventId),
      staleTime: 15 * 1000,
      refetchInterval: 30 * 1000,
    })),
  }) as UseQueryResult<UrgentStatus, Error>[];
}
