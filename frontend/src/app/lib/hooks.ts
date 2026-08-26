import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getEvents,
  getEventStats,
  getUpcomingEvents,
  getUrgentEvents,
  getTopServers,
  getRecentActivity,
  getServerStats,
  getEventDetail,
  generateStaffRecommendations,
  confirmStaffAssignments,
  generateTransportRecommendation,
  confirmTransportRecommendation,
  updateEventStatus,
  getEventOperations,
  initializeEventAttendance,
  checkInStaff,
  checkOutStaff,
  updateAttendanceStatus,
  getAttendanceSummary,
  getEventReport,
  getEventEvaluations,
  createEvaluation,
  updateEvaluation,
  deleteEvaluation,
  getEventRequirements,
  createEventRequirement,
  updateEventRequirement,
  deleteEventRequirement,
  addStaffAssignment,
  removeStaffAssignment,
  updateStaffAssignment,
  getEligibleStaff,
  generateUrgentOffers,
  acceptUrgentOffer,
  declineUrgentOffer,
  expireUrgentOffer,
  getUrgentStatus,
  awardCompletionPoints,
  awardPerformancePoints,
  getMonthlyRankings,
  calculateMonthlyRankings,
  getMonthlyBonuses,
  getServerPoints,
  getServer,
  getServers,
  createEvent,
  getCities,
  getServerAvailability,
  createServerAvailability,
  updateServerAvailability,
  deleteServerAvailability,
  checkServerAvailability,
  getEventAttendance,
  getAttendanceSummary as getEventAttendanceSummary,
  ApiError,
} from '@/app/lib/api';

export function useEvents(params?: Parameters<typeof getEvents>[0]) {
  return useQuery({
    queryKey: ['events', params],
    queryFn: () => getEvents(params),
  });
}

export function useEventStats() {
  return useQuery({
    queryKey: ['eventStats'],
    queryFn: getEventStats,
    staleTime: 30 * 1000,
  });
}

export function useUpcomingEvents(limit = 5) {
  return useQuery({
    queryKey: ['upcomingEvents', limit],
    queryFn: () => getUpcomingEvents(limit),
    staleTime: 30 * 1000,
  });
}

export function useUrgentEvents(limit = 5) {
  return useQuery({
    queryKey: ['urgentEvents', limit],
    queryFn: () => getUrgentEvents(limit),
    staleTime: 15 * 1000,
  });
}

export function useTopServers(limit = 5) {
  return useQuery({
    queryKey: ['topServers', limit],
    queryFn: () => getTopServers(limit),
    staleTime: 60 * 1000,
  });
}

export function useRecentActivity(limit = 10) {
  return useQuery({
    queryKey: ['recentActivity', limit],
    queryFn: () => getRecentActivity(limit),
    staleTime: 30 * 1000,
  });
}

export function useServerStats() {
  return useQuery({
    queryKey: ['serverStats'],
    queryFn: getServerStats,
    staleTime: 30 * 1000,
  });
}

export function useEventDetail(eventId: string) {
  return useQuery({
    queryKey: ['eventDetail', eventId],
    queryFn: () => getEventDetail(eventId),
    enabled: !!eventId,
  });
}

export function useEventOperations(eventId: string) {
  return useQuery({
    queryKey: ['eventOperations', eventId],
    queryFn: () => getEventOperations(eventId),
    enabled: !!eventId,
    staleTime: 10 * 1000,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.status === 'IN_PROGRESS') return 30000;
      return false;
    },
  });
}

export function useEventReport(eventId: string) {
  return useQuery({
    queryKey: ['eventReport', eventId],
    queryFn: () => getEventReport(eventId),
    enabled: !!eventId,
  });
}

export function useEventEvaluations(eventId: string) {
  return useQuery({
    queryKey: ['eventEvaluations', eventId],
    queryFn: () => getEventEvaluations(eventId),
    enabled: !!eventId,
  });
}

export function useEventRequirements(eventId: string) {
  return useQuery({
    queryKey: ['eventRequirements', eventId],
    queryFn: () => getEventRequirements(eventId),
    enabled: !!eventId,
  });
}

export function useEventAttendance(eventId: string) {
  return useQuery({
    queryKey: ['eventAttendance', eventId],
    queryFn: () => getEventAttendance(eventId),
    enabled: !!eventId,
  });
}

export function useAttendanceSummary(eventId: string) {
  return useQuery({
    queryKey: ['attendanceSummary', eventId],
    queryFn: () => getEventAttendanceSummary(eventId),
    enabled: !!eventId,
  });
}

export function useUrgentStatus(eventId: string) {
  return useQuery({
    queryKey: ['urgentStatus', eventId],
    queryFn: () => getUrgentStatus(eventId),
    enabled: !!eventId,
    staleTime: 15 * 1000,
  });
}

export function useMonthlyRankings(year: number, month: number) {
  return useQuery({
    queryKey: ['monthlyRankings', year, month],
    queryFn: () => getMonthlyRankings(year, month),
    enabled: year > 0 && month > 0,
  });
}

export function useMonthlyBonuses(year: number, month: number) {
  return useQuery({
    queryKey: ['monthlyBonuses', year, month],
    queryFn: () => getMonthlyBonuses(year, month),
    enabled: year > 0 && month > 0,
  });
}

export function useServerPoints(serverId: string) {
  return useQuery({
    queryKey: ['serverPoints', serverId],
    queryFn: () => getServerPoints(serverId),
    enabled: !!serverId,
  });
}

export function useServer(serverId: string) {
  return useQuery({
    queryKey: ['server', serverId],
    queryFn: () => getServer(serverId),
    enabled: !!serverId,
  });
}

export function useServerAvailability(serverId: string) {
  return useQuery({
    queryKey: ['serverAvailability', serverId],
    queryFn: () => getServerAvailability(serverId),
    enabled: !!serverId,
  });
}

export function useServers(filters: Parameters<typeof getServers>[0], page: number, pageSize: number) {
  return useQuery({
    queryKey: ['servers', filters, page, pageSize],
    queryFn: () => getServers(filters, page, pageSize),
  });
}

export function useCities() {
  return useQuery({
    queryKey: ['cities'],
    queryFn: getCities,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCreateEvent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createEvent,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['events'] });
      queryClient.invalidateQueries({ queryKey: ['eventStats'] });
      queryClient.invalidateQueries({ queryKey: ['upcomingEvents'] });
    },
  });
}

export function useUpdateEventStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ eventId, payload }: { eventId: string; payload: { status: string } }) =>
      updateEventStatus(eventId, payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['eventDetail', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['events'] });
      queryClient.invalidateQueries({ queryKey: ['eventStats'] });
      queryClient.invalidateQueries({ queryKey: ['upcomingEvents'] });
      queryClient.invalidateQueries({ queryKey: ['urgentEvents'] });
    },
  });
}

export function useGenerateStaffRecommendations() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (eventId: string) => generateStaffRecommendations(eventId),
    onSuccess: (_, eventId) => {
      queryClient.invalidateQueries({ queryKey: ['eventDetail', eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventOperations', eventId] });
    },
  });
}

export function useConfirmStaffAssignments() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ eventId, assignments }: { eventId: string; assignments: Parameters<typeof confirmStaffAssignments>[1] }) =>
      confirmStaffAssignments(eventId, assignments),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['eventDetail', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventOperations', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventRequirements', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['eligibleStaff', variables.eventId] });
    },
  });
}

export function useGenerateTransportRecommendation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (eventId: string) => generateTransportRecommendation(eventId),
    onSuccess: (_, eventId) => {
      queryClient.invalidateQueries({ queryKey: ['eventDetail', eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventOperations', eventId] });
    },
  });
}

export function useConfirmTransportRecommendation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ eventId, request }: { eventId: string; request: Parameters<typeof confirmTransportRecommendation>[1] }) =>
      confirmTransportRecommendation(eventId, request),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['eventDetail', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventOperations', variables.eventId] });
    },
  });
}

export function useInitializeAttendance() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (eventId: string) => initializeEventAttendance(eventId),
    onSuccess: (_, eventId) => {
      queryClient.invalidateQueries({ queryKey: ['eventAttendance', eventId] });
      queryClient.invalidateQueries({ queryKey: ['attendanceSummary', eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventDetail', eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventOperations', eventId] });
    },
  });
}

export function useCheckInStaff() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ eventId, eventStaffId, note }: { eventId: string; eventStaffId: string; note?: string }) =>
      checkInStaff(eventId, eventStaffId, note),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['eventAttendance', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['attendanceSummary', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventDetail', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventOperations', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventReport', variables.eventId] });
    },
  });
}

export function useCheckOutStaff() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ eventId, eventStaffId, note }: { eventId: string; eventStaffId: string; note?: string }) =>
      checkOutStaff(eventId, eventStaffId, note),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['eventAttendance', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['attendanceSummary', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventDetail', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventOperations', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventReport', variables.eventId] });
    },
  });
}

export function useUpdateAttendanceStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ eventId, eventStaffId, status, note }: { eventId: string; eventStaffId: string; status: string; note?: string }) =>
      updateAttendanceStatus(eventId, eventStaffId, status, note),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['eventAttendance', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['attendanceSummary', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventDetail', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventOperations', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventReport', variables.eventId] });
    },
  });
}

export function useCreateEvaluation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ eventId, payload }: { eventId: string; payload: Parameters<typeof createEvaluation>[1] }) =>
      createEvaluation(eventId, payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['eventEvaluations', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventReport', variables.eventId] });
    },
  });
}

export function useUpdateEvaluation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ eventId, evaluationId, payload }: { eventId: string; evaluationId: string; payload: Parameters<typeof updateEvaluation>[2] }) =>
      updateEvaluation(eventId, evaluationId, payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['eventEvaluations', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventReport', variables.eventId] });
    },
  });
}

export function useDeleteEvaluation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ eventId, evaluationId }: { eventId: string; evaluationId: string }) =>
      deleteEvaluation(eventId, evaluationId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['eventEvaluations', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventReport', variables.eventId] });
    },
  });
}

export function useCreateEventRequirement() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ eventId, payload }: { eventId: string; payload: Parameters<typeof createEventRequirement>[1] }) =>
      createEventRequirement(eventId, payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['eventRequirements', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventDetail', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventOperations', variables.eventId] });
    },
  });
}

export function useUpdateEventRequirement() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ eventId, requirementId, payload }: { eventId: string; requirementId: string; payload: Parameters<typeof updateEventRequirement>[2] }) =>
      updateEventRequirement(eventId, requirementId, payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['eventRequirements', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventDetail', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventOperations', variables.eventId] });
    },
  });
}

export function useDeleteEventRequirement() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ eventId, requirementId }: { eventId: string; requirementId: string }) =>
      deleteEventRequirement(eventId, requirementId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['eventRequirements', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventDetail', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventOperations', variables.eventId] });
    },
  });
}

export function useAddStaffAssignment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ eventId, payload }: { eventId: string; payload: Parameters<typeof addStaffAssignment>[1] }) =>
      addStaffAssignment(eventId, payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['eventDetail', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventOperations', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['eligibleStaff', variables.eventId] });
    },
  });
}

export function useRemoveStaffAssignment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ eventId, assignmentId }: { eventId: string; assignmentId: string }) =>
      removeStaffAssignment(eventId, assignmentId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['eventDetail', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventOperations', variables.eventId] });
    },
  });
}

export function useUpdateStaffAssignment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ eventId, assignmentId, payload }: { eventId: string; assignmentId: string; payload: Parameters<typeof updateStaffAssignment>[2] }) =>
      updateStaffAssignment(eventId, assignmentId, payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['eventDetail', variables.eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventOperations', variables.eventId] });
    },
  });
}

export function useAwardCompletionPoints() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (eventId: string) => awardCompletionPoints(eventId),
    onSuccess: (_, eventId) => {
      queryClient.invalidateQueries({ queryKey: ['eventDetail', eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventOperations', eventId] });
      queryClient.invalidateQueries({ queryKey: ['serverPoints'] });
      queryClient.invalidateQueries({ queryKey: ['monthlyRankings'] });
      queryClient.invalidateQueries({ queryKey: ['monthlyBonuses'] });
    },
  });
}

export function useAwardPerformancePoints() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (eventId: string) => awardPerformancePoints(eventId),
    onSuccess: (_, eventId) => {
      queryClient.invalidateQueries({ queryKey: ['eventDetail', eventId] });
      queryClient.invalidateQueries({ queryKey: ['eventOperations', eventId] });
      queryClient.invalidateQueries({ queryKey: ['serverPoints'] });
      queryClient.invalidateQueries({ queryKey: ['monthlyRankings'] });
      queryClient.invalidateQueries({ queryKey: ['monthlyBonuses'] });
    },
  });
}

export function useCalculateRankings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: { year: number; month: number }) => calculateMonthlyRankings(params.year, params.month),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['monthlyRankings'] });
      queryClient.invalidateQueries({ queryKey: ['monthlyBonuses'] });
      queryClient.invalidateQueries({ queryKey: ['serverPoints'] });
    },
  });
}

export function useCreateServerAvailability() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ serverId, payload }: { serverId: string; payload: Parameters<typeof createServerAvailability>[1] }) =>
      createServerAvailability(serverId, payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['serverAvailability', variables.serverId] });
    },
  });
}

export function useUpdateServerAvailability() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ serverId, availabilityId, payload }: { serverId: string; availabilityId: string; payload: Parameters<typeof updateServerAvailability>[2] }) =>
      updateServerAvailability(serverId, availabilityId, payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['serverAvailability', variables.serverId] });
    },
  });
}

export function useDeleteServerAvailability() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ serverId, availabilityId }: { serverId: string; availabilityId: string }) =>
      deleteServerAvailability(serverId, availabilityId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['serverAvailability', variables.serverId] });
    },
  });
}
