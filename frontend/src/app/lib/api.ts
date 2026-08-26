import type {
  ActivityItem,
  EventDetailData,
  ServerFilters,
  ServerListItem,
  ServerListResponse,
  ServerProfile,
  ServerStats,
  WorkerType,
} from '@/app/lib/types';

export type { ActivityItem, ServerFilters, ServerListItem, ServerListResponse, ServerProfile, ServerStats, WorkerType, EventDetailData } from '@/app/lib/types';
export type { LoginResponse, UserResponse } from '@/app/lib/api-client';
export { ApiError } from '@/app/lib/api-client';
export { login, getCurrentUser, logout } from '@/app/lib/api-client';

export interface EventListParams {
  search?: string;
  city?: string;
  status?: string;
  priority?: string;
  urgent?: boolean;
  staffing?: string;
  date_range?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

export interface EventListItem {
  id: string;
  name: string;
  city: string;
  start_datetime: string;
  end_datetime: string;
  guest_count: number;
  alcohol_service: boolean;
  food_products_count: number;
  priority: string;
  urgent: boolean;
  status: string;
  staffing: {
    requested: number;
    selected: number;
    missing: number;
    percentage: number;
  };
}

export interface EventListResponse {
  items: EventListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface EventStats {
  upcoming_events: number;
  planned_events: number;
  urgent_events: number;
  in_progress_events: number;
  completed_events: number;
  total_events: number;
}

export interface City {
  id: string;
  name: string;
}

export interface EventCreateRequest {
  name: string;
  client_name: string;
  city_id: string;
  address: string;
  start_datetime: string;
  end_datetime: string;
  guest_count: number;
  event_type: string;
  alcohol_service?: boolean;
  food_products_count?: number;
  priority?: string;
  is_urgent?: boolean;
  required_response_minutes?: number;
  status?: string;
  notes?: string;
}

export interface DashboardServerStats {
  total: number;
  available: number;
  unavailable: number;
  with_vehicle: number;
}

export interface StaffRecommendationResponse {
  event: {
    event_id: string;
    name: string;
    city: string;
    start_datetime: string;
    end_datetime: string;
    guest_count: number;
    alcohol_service: boolean;
    food_products_count: number;
    requirements: {
      requirement_id: string;
      role_name: string;
      quantity: number;
      required_gender: string | null;
      minimum_experience: number;
      minimum_skill_level: number;
    }[];
  };
  requirements: {
    requirement: {
      requirement_id: string;
      role_name: string;
      quantity: number;
      required_gender: string | null;
      minimum_experience: number;
      minimum_skill_level: number;
    };
    candidates: {
      server_id: string;
      name: string;
      gender: string;
      city: string;
      experience_years: number;
      worker_type: string;
      main_skill_level: number;
      availability_status: string;
      distance_km: number | null;
      score: number | null;
      reasons: string[];
      exclusion_reason?: string | null;
    }[];
    selected: {
      server_id: string;
      name: string;
      gender: string;
      city: string;
      experience_years: number;
      worker_type: string;
      main_skill_level: number;
      availability_status: string;
      distance_km: number | null;
      score: number | null;
      reasons: string[];
      exclusion_reason?: string | null;
    }[];
    status: string;
    message: string | null;
  }[];
  total_eligible: number;
  total_excluded: number;
  total_selected: number;
  status: string;
}

export interface TransportRecommendationResponse {
  event_id: string;
  transport_status: string;
  drivers: {
    server_id: string;
    name: string;
    vehicle: string;
    capacity: number;
    available_seats: number;
    can_transport_coworkers: boolean;
  }[];
  passengers: {
    server_id: string;
    name: string;
    pickup_order: number;
    distance_from_driver_km: number;
  }[];
  unassigned_passengers: {
    server_id: string;
    name: string;
    reason: string;
  }[];
  total_selected: number;
  total_assigned: number;
  total_unassigned: number;
}

export interface TransportConfirmationRequest {
  groups: {
    driver_server_id: string;
    passengers: {
      server_id: string;
      pickup_order: number;
    }[];
  }[];
}

export interface TransportConfirmationGroupResponse {
  group_id: string;
  driver_name: string;
  vehicle: string;
  capacity: number;
  passenger_count: number;
  estimated_distance_km?: number;
}

export interface TransportConfirmationResponse {
  event_id: string;
  status: string;
  groups_created: number;
  passengers_created: number;
  groups: TransportConfirmationGroupResponse[];
  message?: string;
}

export interface ConfirmStaffAssignmentRequest {
  server_id: string;
  role: string;
}

export interface ConfirmStaffAssignmentResponse {
  server_id: string;
  server_name: string;
  role: string;
}

export interface ConfirmStaffResponse {
  event_id: string;
  status: string;
  created_count: number;
  assignments: ConfirmStaffAssignmentResponse[];
  missing_positions: number;
}

export interface RequirementDetail {
  requirement_id: string;
  role_name: string;
  quantity: number;
  required_gender: string | null;
  minimum_experience: number;
  minimum_skill_level: number;
  selected: number;
  missing: number;
}

export interface RequirementCreateRequest {
  role_name: string;
  quantity: number;
  minimum_skill_level?: number;
  minimum_experience?: number;
  required_gender?: string | null;
}

export interface RequirementUpdateRequest {
  role_name?: string;
  quantity?: number;
  minimum_skill_level?: number;
  minimum_experience?: number;
  required_gender?: string | null;
}

export interface AddStaffAssignmentRequest {
  server_id: string;
  requirement_id: string;
  role: string;
}

export interface UpdateStaffAssignmentRequest {
  role?: string;
  assignment_status?: string;
  requirement_id?: string;
}

export interface StaffAssignmentResponse {
  id: string;
  event_id: string;
  server_id: string;
  server_name: string;
  role: string;
  status: string;
  assigned_at: string;
  confirmed_at?: string;
  score?: number;
  distance_km?: number;
  years_experience?: number;
  skill_level?: number;
  availability_status?: string;
  gender?: string;
  city?: string;
  requirement_id?: string;
}

export interface EligibleStaffResponse {
  server_id: string;
  server_name: string;
  gender: string;
  city: string;
  years_experience: number;
  skill_level: number;
  availability_status: string;
  score?: number;
  distance_km?: number;
  requirement_id?: string;
  role?: string;
}

export interface EventStatusUpdateRequest {
  status: string;
}

export interface EventStatusUpdateResponse {
  event_id: string;
  status: string;
  previous_status: string;
  message: string;
}

export interface AvailabilityResponse {
  id: string;
  server_id: string;
  start_datetime: string;
  end_datetime: string;
  status: string;
  note?: string | null;
  conflict: boolean;
  conflict_reason?: string | null;
}

export interface ServerAvailabilityListResponse {
  server_id: string;
  items: AvailabilityResponse[];
}

export interface AvailabilityCheckResponse {
  server_id: string;
  event_id: string;
  available: boolean;
  reason?: string | null;
}

export interface AttendanceResponse {
  id: string;
  event_id: string;
  event_staff_id: string;
  server_id: string;
  server_name: string;
  role: string;
  status: string;
  check_in_at?: string | null;
  check_out_at?: string | null;
  note?: string | null;
}

export interface AttendanceListResponse {
  event_id: string;
  summary: Record<string, number>;
  staff: AttendanceResponse[];
}

export interface AttendanceSummaryResponse {
  event_id: string;
  total_expected: number;
  present: number;
  late: number;
  absent: number;
  excused: number;
  checked_out: number;
  not_checked_in: number;
  attendance_rate: number;
}

export interface AttendanceInitializeResponse {
  event_id: string;
  initialized_count: number;
  total_expected: number;
}

export interface EventOperationsRequirement {
  requirement_id: string;
  role_name: string;
  quantity: number;
  required_gender: string | null;
  minimum_experience: number;
  minimum_skill_level: number;
  assigned: number;
  confirmed: number;
  missing: number;
  status: string;
}

export interface EventOperationsStaff {
  assignment_id: string;
  server_id: string;
  server_name: string;
  role: string;
  assignment_status: string;
  years_experience?: number;
  skill_level?: number;
  score?: number;
  transport_status?: string;
}

export interface EventOperationsTransportGroup {
  group_id: string;
  driver_name: string;
  vehicle: string;
  capacity: number;
  passenger_count: number;
  available_seats: number;
  status: string;
  passengers: {
    server_id: string;
    name: string;
    pickup_order: number;
    pickup_status: string;
  }[];
}

export interface EventOperationsTransport {
  groups: EventOperationsTransportGroup[];
  total_groups: number;
  total_passengers: number;
  unassigned_passengers: number;
}

export interface OperationalAlert {
  type: string;
  severity: string;
  message: string;
  related_entity?: string;
}

export interface EventOperationsResponse {
  event_id: string;
  event_name: string;
  status: string;
  city: string;
  date: string;
  guest_count: number;
  duration_minutes?: number;
  attendance_available: boolean;
  attendance?: {
    summary: {
      total_expected: number;
      present: number;
      late: number;
      absent: number;
      excused: number;
      checked_out: number;
      not_checked_in: number;
      attendance_rate: number;
    };
    staff: {
      id: string;
      server_name: string;
      role: string;
      status: string;
      check_in_at?: string | null;
      check_out_at?: string | null;
    }[];
  };
  staffing_summary: {
    requested: number;
    assigned: number;
    confirmed: number;
    missing: number;
    proposed: number;
    coverage_percentage: number;
  };
  requirements: EventOperationsRequirement[];
  confirmed_staff: EventOperationsStaff[];
  transport: EventOperationsTransport;
  alerts: OperationalAlert[];
}

export interface EventReportRequirement {
  requirement_id: string;
  role: string;
  requested: number;
  assigned: number;
  confirmed: number;
  fulfilled: boolean;
  status: string;
}

export interface EventReportStaff {
  server_id: string;
  name: string;
  role: string;
  assignment_status: string;
  attendance_status?: string | null;
  check_in_at?: string | null;
  check_out_at?: string | null;
  completion_points: number;
  performance_points: number;
  total_points: number;
  evaluation_score?: number | null;
  evaluation_comment?: string | null;
  evaluated?: boolean;
}

export interface EventReportTransport {
  total_groups: number;
  confirmed_groups: number;
  total_passengers: number;
  assigned_passengers: number;
  unassigned_passengers: number;
}

export interface EventReportGamification {
  completion_points: number;
  performance_points: number;
  total_points: number;
}

export interface EventReportKpi {
  staffing_rate: number;
  attendance_rate: number;
  requirement_fulfillment_rate: number;
  transport_coverage_rate: number;
  evaluation_coverage?: number;
}

export interface EventReportAlert {
  type: string;
  severity: string;
  message: string;
  related_entity?: string | null;
}

export interface EventReportEvaluationSummary {
  total_evaluated: number;
  total_confirmed: number;
  evaluation_coverage: number;
  average_score: number | null;
  highest_score: number | null;
  lowest_score: number | null;
  excellent_count: number;
  good_count: number;
  average_count: number;
  needs_improvement_count: number;
}

export interface EventReportResponse {
  event_id: string;
  event_name: string;
  status: string;
  is_final: boolean;
  event: {
    name?: string;
    city?: string;
    start_datetime?: string;
    end_datetime?: string;
    guest_count?: number;
    alcohol_service?: boolean;
    food_products_count?: number;
    priority?: string;
    urgent?: boolean;
    status?: string;
  };
  staffing: {
    requested?: number;
    selected?: number;
    missing?: number;
    percentage?: number;
  };
  requirements: EventReportRequirement[];
  attendance: {
    available: boolean;
    expected?: number;
    present?: number;
    late?: number;
    absent?: number;
    attendance_rate?: number;
  };
  staff: EventReportStaff[];
  transport: EventReportTransport;
  gamification: EventReportGamification;
  final_kpis: EventReportKpi;
  evaluation_summary?: EventReportEvaluationSummary;
  alerts: EventReportAlert[];
  generated_at: string;
}

export interface EvaluationResponse {
  id: string;
  event_id: string;
  server_id: string;
  server_name: string;
  role: string;
  punctuality: number;
  work_quality: number;
  presentation: number;
  teamwork: number;
  client_relation: number;
  comment?: string | null;
  created_at: string;
}

export interface UrgentOffer {
  offer_id: string;
  server_id: string;
  server_name: string;
  role: string;
  status: string;
  wave_number: number;
  created_at: string | null;
  expires_at: string | null;
  score: number | null;
  distance_km: number | null;
  reason: string | null;
}

export interface UrgentStatus {
  event_id: string;
  is_urgent: boolean;
  wave_number: number;
  wave_size: number;
  offers_sent: number;
  pending_count: number;
  accepted_count: number;
  declined_count: number;
  expired_count: number;
  total_staff_needed: number;
  total_staff_confirmed: number;
  remaining_staff: number;
  can_generate_next_wave: boolean;
  offers: UrgentOffer[];
  requirements: {
    role: string;
    requested: number;
    accepted: number;
    remaining: number;
  }[];
}

export interface UrgentGenerateResponse {
  event_id: string;
  status: string;
  wave_number: number;
  offers_created: number;
  requirements: {
    role: string;
    requested: number;
    accepted: number;
    remaining: number;
  }[];
  offers: UrgentOffer[];
}

export interface UrgentActionResponse {
  success: boolean;
  message: string;
  offer: UrgentOffer | null;
  urgent_status: UrgentStatus;
}

export interface GamificationRankingItem {
  rank: number;
  server_id: string;
  server_name: string;
  total_points: number;
  completion_points: number;
  performance_points: number;
}

export interface GamificationRanking {
  year: number;
  month: number;
  calculated_at: string | null;
  rankings: GamificationRankingItem[];
  total_servers: number;
  total_points: number;
  top_server: string | null;
  status: string | null;
}

export interface GamificationBonus {
  server_id: string;
  server_name: string;
  rank: number;
  points: number;
  bonus_amount: number;
  rule: string | null;
  status: string | null;
}

export interface GamificationCalculationResponse {
  year: number;
  month: number;
  rankings: GamificationRankingItem[];
  total_servers: number;
  status: string;
}

export interface GamificationAwardResponse {
  event_id: string;
  status: string;
  points_awarded: number;
  created: {
    server_id: string;
    server_name: string;
    points: number;
    reason: string;
  }[];
  skipped: {
    server_id: string;
    reason: string;
  }[];
}

import { fetchAPI, ApiError } from '@/app/lib/api-client';

export async function getEventDetail(eventId: string): Promise<EventDetailData | null> {
  try {
    const data = await fetchAPI<{
      event: EventDetailData['event'];
      staffing: EventDetailData['staffing'];
      requirements: EventDetailData['requirements_detail'];
      assignments: EventDetailData['assignments'];
      transport: EventDetailData['transport'];
    }>(`/events/${eventId}`);
    return {
      event: data.event,
      staffing: data.staffing,
      assignments: data.assignments,
      requirements_detail: data.requirements,
      transport: data.transport,
    };
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

function parseExperienceRange(range: string): { min?: number; max?: number } {
  if (!range) return {};
  if (range === '0-2') return { min: 0, max: 2 };
  if (range === '3-5') return { min: 3, max: 5 };
  if (range === '6-10') return { min: 6, max: 10 };
  if (range === '10-') return { min: 10 };
  return {};
}

export async function getServers(
  filters: ServerFilters,
  page: number,
  pageSize: number,
): Promise<ServerListResponse> {
  const params = new URLSearchParams();
  if (filters.search) params.set('search', filters.search);
  if (filters.city) params.set('city', filters.city);
  if (filters.gender) params.set('gender', filters.gender);
  if (filters.availability) params.set('availability', filters.availability);
  if (filters.worker_type) params.set('worker_type', filters.worker_type);
  if (filters.has_vehicle) {
    params.set('has_vehicle', filters.has_vehicle === 'yes' ? 'true' : 'false');
  }
  if (filters.can_transport) {
    params.set('can_transport', filters.can_transport === 'yes' ? 'true' : 'false');
  }
  if (filters.location_verified) {
    params.set('location_verified', filters.location_verified === 'verified' ? 'true' : 'false');
  }
  if (filters.skill) params.set('skill', filters.skill);

  const expRange = parseExperienceRange(filters.experience_range);
  if (expRange.min !== undefined) params.set('min_experience', String(expRange.min));
  if (expRange.max !== undefined) params.set('max_experience', String(expRange.max));

  if (filters.sort_by) params.set('sort_by', filters.sort_by);
  if (filters.sort_order) params.set('sort_order', filters.sort_order);

  params.set('page', String(page));
  params.set('page_size', String(pageSize));

  const data = await fetchAPI<{ items: ServerListItem[]; total: number; page: number; page_size: number; total_pages: number }>(
    `/servers?${params.toString()}`
  );

  return {
    servers: data.items,
    total: data.total,
    page: data.page,
    page_size: data.page_size,
    total_pages: data.total_pages,
  };
}

export async function getServerStats(): Promise<ServerStats> {
  return fetchAPI<ServerStats>('/servers/stats');
}

export async function getServer(serverId: string): Promise<ServerProfile | null> {
  try {
    return await fetchAPI<ServerProfile>(`/servers/${serverId}`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export async function getEvents(params: EventListParams = {}): Promise<EventListResponse> {
  const query = new URLSearchParams();
  if (params.search) query.set('search', params.search);
  if (params.city) query.set('city', params.city);
  if (params.status) query.set('status', params.status);
  if (params.priority) query.set('priority', params.priority);
  if (params.urgent !== undefined) query.set('urgent', String(params.urgent));
  if (params.staffing) query.set('staffing', params.staffing);
  if (params.date_range) query.set('date_range', params.date_range);
  if (params.sort_by) query.set('sort_by', params.sort_by);
  if (params.sort_order) query.set('sort_order', params.sort_order);
  if (params.page) query.set('page', String(params.page));
  if (params.page_size) query.set('page_size', String(params.page_size));

  const data = await fetchAPI<EventListResponse>(`/events?${query.toString()}`);
  return data;
}

export async function getEventStats(): Promise<EventStats> {
  return fetchAPI<EventStats>('/events/stats');
}

export async function getCities(): Promise<City[]> {
  return fetchAPI<City[]>('/cities');
}

export async function createEvent(data: EventCreateRequest): Promise<EventListItem> {
  return fetchAPI<EventListItem>('/events', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getDashboardServerStats(): Promise<DashboardServerStats> {
  return fetchAPI<DashboardServerStats>('/servers/stats');
}

export async function getUpcomingEvents(limit: number = 5): Promise<EventListResponse> {
  return getEvents({ date_range: 'UPCOMING', page: 1, page_size: limit });
}

export async function getUrgentEvents(limit: number = 5): Promise<EventListResponse> {
  return getEvents({ urgent: true, page: 1, page_size: limit });
}

export async function getTopServers(limit: number = 5): Promise<ServerListResponse> {
  const data = await fetchAPI<{ items: ServerListItem[]; total: number; page: number; page_size: number; total_pages: number }>(
    `/servers?sort_by=points&sort_order=desc&page=1&page_size=${limit}`
  );
  return {
    servers: data.items,
    total: data.total,
    page: data.page,
    page_size: data.page_size,
    total_pages: data.total_pages,
  };
}

export async function getRecentActivity(limit: number = 10): Promise<ActivityItem[]> {
  return fetchAPI<ActivityItem[]>(`/activity/recent?limit=${limit}`);
}

export async function generateStaffRecommendations(eventId: string): Promise<StaffRecommendationResponse> {
  return fetchAPI<StaffRecommendationResponse>(`/events/${eventId}/generate-staff`, {
    method: 'POST',
  });
}

export async function confirmStaffAssignments(
  eventId: string,
  assignments: ConfirmStaffAssignmentRequest[],
): Promise<ConfirmStaffResponse> {
  return fetchAPI<ConfirmStaffResponse>(`/events/${eventId}/confirm-staff`, {
    method: 'POST',
    body: JSON.stringify({ assignments }),
  });
}

export async function generateTransportRecommendation(eventId: string): Promise<TransportRecommendationResponse> {
  return fetchAPI<TransportRecommendationResponse>(`/events/${eventId}/recommend-transport`, {
    method: 'POST',
  });
}

export async function confirmTransportRecommendation(
  eventId: string,
  request: TransportConfirmationRequest,
): Promise<TransportConfirmationResponse> {
  return fetchAPI<TransportConfirmationResponse>(`/events/${eventId}/confirm-transport`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function getUrgentStatus(eventId: string): Promise<UrgentStatus> {
  return fetchAPI<UrgentStatus>(`/events/${eventId}/urgent-status`);
}

export async function generateUrgentOffers(eventId: string): Promise<UrgentGenerateResponse> {
  return fetchAPI<UrgentGenerateResponse>(`/events/${eventId}/urgent-offers/generate`, {
    method: 'POST',
  });
}

export async function acceptUrgentOffer(eventId: string, offerId: string): Promise<UrgentActionResponse> {
  return fetchAPI<UrgentActionResponse>(`/events/${eventId}/urgent-offers/${offerId}/accept`, {
    method: 'POST',
  });
}

export async function declineUrgentOffer(eventId: string, offerId: string): Promise<UrgentActionResponse> {
  return fetchAPI<UrgentActionResponse>(`/events/${eventId}/urgent-offers/${offerId}/decline`, {
    method: 'POST',
  });
}

export async function expireUrgentOffer(eventId: string, offerId: string): Promise<UrgentActionResponse> {
  return fetchAPI<UrgentActionResponse>(`/events/${eventId}/urgent-offers/${offerId}/expire`, {
    method: 'POST',
  });
}

export async function getMonthlyRankings(year: number, month: number): Promise<GamificationRanking> {
  return fetchAPI<GamificationRanking>(`/rankings/${year}/${month}`);
}

export async function calculateMonthlyRankings(year: number, month: number): Promise<GamificationCalculationResponse> {
  return fetchAPI<GamificationCalculationResponse>(`/rankings/${year}/${month}/calculate`, {
    method: 'POST',
  });
}

export async function getMonthlyBonuses(year: number, month: number): Promise<GamificationBonus[]> {
  return fetchAPI<GamificationBonus[]>(`/bonuses/${year}/${month}`);
}

export async function getServerPoints(serverId: string): Promise<ServerPoints> {
  return fetchAPI<ServerPoints>(`/servers/${serverId}/points`);
}

export async function awardCompletionPoints(eventId: string): Promise<GamificationAwardResponse> {
  return fetchAPI<GamificationAwardResponse>(`/events/${eventId}/award-completion-points`, {
    method: 'POST',
  });
}

export async function awardPerformancePoints(eventId: string): Promise<GamificationAwardResponse> {
  return fetchAPI<GamificationAwardResponse>(`/events/${eventId}/award-performance-points`, {
    method: 'POST',
  });
}

export async function updateEventStatus(
  eventId: string,
  payload: EventStatusUpdateRequest,
): Promise<EventStatusUpdateResponse> {
  return fetchAPI<EventStatusUpdateResponse>(`/events/${eventId}/status`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function getEventOperations(eventId: string): Promise<EventOperationsResponse> {
  return fetchAPI<EventOperationsResponse>(`/events/${eventId}/operations`);
}

export async function getServerAvailability(serverId: string): Promise<ServerAvailabilityListResponse> {
  return fetchAPI<ServerAvailabilityListResponse>(`/servers/${serverId}/availability`);
}

export async function createServerAvailability(
  serverId: string,
  payload: { start_datetime: string; end_datetime: string; status?: string; note?: string },
): Promise<AvailabilityResponse> {
  return fetchAPI<AvailabilityResponse>(`/servers/${serverId}/availability`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateServerAvailability(
  serverId: string,
  availabilityId: string,
  payload: { start_datetime?: string; end_datetime?: string; status?: string; note?: string },
): Promise<AvailabilityResponse> {
  return fetchAPI<AvailabilityResponse>(`/servers/${serverId}/availability/${availabilityId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function deleteServerAvailability(serverId: string, availabilityId: string): Promise<void> {
  return fetchAPI<void>(`/servers/${serverId}/availability/${availabilityId}`, {
    method: 'DELETE',
  });
}

export async function checkServerAvailability(
  serverId: string,
  eventId: string,
): Promise<AvailabilityCheckResponse> {
  const params = new URLSearchParams();
  params.set('event_id', eventId);

  return fetchAPI<AvailabilityCheckResponse>(`/servers/${serverId}/availability/check?${params.toString()}`);
}

export async function getEventAttendance(eventId: string): Promise<AttendanceListResponse> {
  return fetchAPI<AttendanceListResponse>(`/events/${eventId}/attendance`);
}

export async function initializeEventAttendance(eventId: string): Promise<AttendanceInitializeResponse> {
  return fetchAPI<AttendanceInitializeResponse>(`/events/${eventId}/attendance/initialize`, {
    method: 'POST',
  });
}

export async function checkInStaff(
  eventId: string,
  eventStaffId: string,
  note?: string,
): Promise<{ success: boolean; attendance_id: string; message: string }> {
  return fetchAPI<{ success: boolean; attendance_id: string; message: string }>(`/events/${eventId}/attendance/${eventStaffId}/check-in`, {
    method: 'POST',
    body: JSON.stringify({ note: note || null }),
  });
}

export async function checkOutStaff(
  eventId: string,
  eventStaffId: string,
  note?: string,
): Promise<{ success: boolean; attendance_id: string; message: string }> {
  return fetchAPI<{ success: boolean; attendance_id: string; message: string }>(`/events/${eventId}/attendance/${eventStaffId}/check-out`, {
    method: 'POST',
    body: JSON.stringify({ note: note || null }),
  });
}

export async function updateAttendanceStatus(
  eventId: string,
  eventStaffId: string,
  status: string,
  note?: string,
): Promise<{ success: boolean; attendance_id: string; status: string }> {
  return fetchAPI<{ success: boolean; attendance_id: string; status: string }>(`/events/${eventId}/attendance/${eventStaffId}`, {
    method: 'PATCH',
    body: JSON.stringify({ status, note: note || null }),
  });
}

export async function getAttendanceSummary(eventId: string): Promise<AttendanceSummaryResponse> {
  return fetchAPI<AttendanceSummaryResponse>(`/events/${eventId}/attendance/summary`);
}

export async function getEventReport(eventId: string): Promise<EventReportResponse> {
  return fetchAPI<EventReportResponse>(`/events/${eventId}/report`);
}

export async function getEventEvaluations(eventId: string): Promise<EvaluationResponse[]> {
  return fetchAPI<EvaluationResponse[]>(`/events/${eventId}/evaluations`);
}

export async function createEvaluation(eventId: string, payload: {
  server_id: string;
  punctuality: number;
  work_quality: number;
  presentation: number;
  teamwork: number;
  client_relation: number;
  comment?: string | null;
}): Promise<EvaluationResponse> {
  return fetchAPI<EvaluationResponse>(`/events/${eventId}/evaluations`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateEvaluation(eventId: string, evaluationId: string, payload: {
  punctuality?: number;
  work_quality?: number;
  presentation?: number;
  teamwork?: number;
  client_relation?: number;
  comment?: string | null;
}): Promise<EvaluationResponse> {
  return fetchAPI<EvaluationResponse>(`/events/${eventId}/evaluations/${evaluationId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function deleteEvaluation(eventId: string, evaluationId: string): Promise<void> {
  return fetchAPI<void>(`/events/${eventId}/evaluations/${evaluationId}`, {
    method: 'DELETE',
  });
}

export async function addStaffAssignment(eventId: string, payload: AddStaffAssignmentRequest): Promise<StaffAssignmentResponse> {
  return fetchAPI<StaffAssignmentResponse>(`/events/${eventId}/staff`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function removeStaffAssignment(eventId: string, assignmentId: string): Promise<void> {
  return fetchAPI<void>(`/events/${eventId}/staff/${assignmentId}`, {
    method: 'DELETE',
  });
}

export async function updateStaffAssignment(
  eventId: string,
  assignmentId: string,
  payload: UpdateStaffAssignmentRequest,
): Promise<StaffAssignmentResponse> {
  return fetchAPI<StaffAssignmentResponse>(`/events/${eventId}/staff/${assignmentId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function getEligibleStaff(
  eventId: string,
  search?: string,
  role?: string,
): Promise<EligibleStaffResponse[]> {
  const params = new URLSearchParams();
  if (search) params.set('search', search);
  if (role) params.set('role', role);

  return fetchAPI<EligibleStaffResponse[]>(`/events/${eventId}/eligible-staff${params.toString() ? '?' + params.toString() : ''}`);
}

export async function getEventRequirements(eventId: string): Promise<{ event_id: string; requirements: RequirementDetail[] }> {
  return fetchAPI<{ event_id: string; requirements: RequirementDetail[] }>(`/events/${eventId}/requirements`);
}

export async function createEventRequirement(eventId: string, payload: RequirementCreateRequest): Promise<RequirementDetail> {
  return fetchAPI<RequirementDetail>(`/events/${eventId}/requirements`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateEventRequirement(eventId: string, requirementId: string, payload: RequirementUpdateRequest): Promise<RequirementDetail> {
  return fetchAPI<RequirementDetail>(`/events/${eventId}/requirements/${requirementId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function deleteEventRequirement(eventId: string, requirementId: string): Promise<void> {
  await fetchAPI<void>(`/events/${eventId}/requirements/${requirementId}`, {
    method: 'DELETE',
  });
}

export interface ServerPoints {
  server_id: string;
  server_name: string;
  total_points: number;
  completion_points: number;
  performance_points: number;
  current_month_points: number;
  previous_month_points: number;
  rank: number | null;
  transactions: {
    transaction_id: string;
    server_id: string;
    type: string;
    points: number;
    event_id: string | null;
    description: string | null;
    created_at: string | null;
  }[];
}
