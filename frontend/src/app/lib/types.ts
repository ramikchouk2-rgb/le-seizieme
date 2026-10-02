export interface ServerFilters {
  search: string;
  city: string;
  gender: string;
  availability: string;
  worker_type: string;
  has_vehicle: string;
  can_transport: string;
  location_verified: string;
  experience_range: string;
  skill: string;
  sort_by: string;
  sort_order: 'asc' | 'desc';
}

/**
 * Step 24C-D-9: the uniform size a server wears.
 *
 * Mirrors the PostgreSQL enum `server_uniform_size`. Nullable everywhere: null
 * means the size was never recorded, which is distinct from any listed size and
 * is displayed as "Non renseignée" rather than defaulted.
 */
export type ServerUniformSize =
  | 'XS'
  | 'S'
  | 'M'
  | 'L'
  | 'XL'
  | 'XXL'
  | 'XXXL';

/** Selectable options. An empty value means "not recorded" and maps to null. */
export const UNIFORM_SIZE_OPTIONS: ServerUniformSize[] = [
  'XS',
  'S',
  'M',
  'L',
  'XL',
  'XXL',
  'XXXL',
];

export interface ServerListItem {
  id: string;
  first_name: string;
  last_name: string;
  gender: string;
  city: string;
  years_experience: number;
  worker_type: string;
  availability_status: string;
  main_skill: string;
  main_skill_level: number;
  vehicle?: {
    brand: string;
    model: string;
    can_transport_coworkers: boolean;
  };
  location_verified: boolean;
  monthly_points: number;
  rank: number;
  /** Step 24C-D-5: boolean projection only, never image bytes. */
  has_profile_photo?: boolean;
  /** Step 24C-D-9. Not shown as a column in the directory table. */
  uniform_size?: ServerUniformSize | null;
}

export interface ServerListResponse {
  servers: ServerListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ServerProfile {
  id: string;
  first_name: string;
  last_name: string;
  gender: string;
  city: string;
  city_id: string;
  years_experience: number;
  worker_type: string;
  /**
   * Step 24C-D-9. Null means the uniform size was never recorded; the UI shows
   * "Non renseignée" instead of assuming one.
   */
  uniform_size?: ServerUniformSize | null;
  availability_status: string;
  email: string;
  phone: string;
  location: {
    city: string;
    area: string;
    is_verified: boolean;
  };
  skills: {
    name: string;
    level: number;
  }[];
  vehicle?: {
    id: string;
    vehicle_type: string;
    brand: string;
    model: string;
    seats_total: number;
    can_transport_coworkers: boolean;
    is_active: boolean;
  };
  availability: {
    id: string;
    start_datetime: string;
    end_datetime: string;
    status: string;
    note?: string | null;
    conflict?: boolean;
    conflict_reason?: string | null;
  }[];
  upcoming_events?: {
    assignment_id: string;
    event_id: string;
    event_name: string;
    start_datetime: string;
    end_datetime: string;
    event_status: string;
    assignment_status: string;
    role: string;
    conflict?: boolean;
    conflict_reason?: string | null;
  }[];
  points: {
    total_points: number;
    current_month_points: number;
    previous_month_points: number;
    rank: number | null;
  };
  speed_score: number;
  punctuality_score: number;
  presentation_score: number;
  communication_score: number;
  teamwork_score: number;
  discipline_score: number;
  endurance_score: number;
  is_active: boolean;
  /**
   * Step 24C-D-5: photo metadata only. Photo bytes are never embedded in a
   * profile response; they are fetched from the authorized photo endpoint.
   */
  has_profile_photo: boolean;
  profile_photo?: ServerFileMetadata | null;
}

/** Step 24C-D-5: descriptive metadata for a stored server file. */
export interface ServerFileMetadata {
  id: string;
  server_id: string;
  file_type: string;
  mime_type: string;
  original_filename?: string | null;
  file_size: number;
  is_current: boolean;
  created_at: string;
}

// ============================================================
// Step 24C-D-6: professional attestations
//
// Attestations are append-only: uploading a document always creates a NEW record
// and never modifies an existing one. Nothing here carries document bytes or a
// URL -- `file` is descriptive metadata only.
// ============================================================

export type ServerAttestationStatus =
  | 'PENDING'
  | 'VERIFIED'
  | 'REJECTED'
  | 'SUPERSEDED';

/** Descriptive metadata about the stored document. Never the bytes. */
export interface AttestationFileMetadata {
  id: string;
  mime_type: string;
  original_filename?: string | null;
  file_size: number;
}

export interface ServerAttestation {
  id: string;
  server_id: string;
  file_id: string;
  status: ServerAttestationStatus;
  status_label: string;
  /**
   * The field every consumer must use to decide whether this document counts as a
   * real qualification. True only for VERIFIED, which requires an explicit
   * Manager/Admin decision -- an upload alone never sets it.
   */
  counts_as_verified_qualification: boolean;
  qualification_name: string;
  issuing_organization?: string | null;
  issued_on?: string | null;
  expires_on?: string | null;
  rejection_reason?: string | null;
  verified_at?: string | null;
  verified_by?: string | null;
  superseded_by_id?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  file: AttestationFileMetadata;
}

export interface ServerAttestationList {
  items: ServerAttestation[];
  total: number;
  /** Aggregate derived only from VERIFIED rows, so the UI need not recount. */
  verified_count: number;
}

/** Metadata submitted alongside an uploaded document. `status` is not settable. */
export interface ServerAttestationUploadMetadata {
  qualification_name: string;
  issuing_organization?: string;
  issued_on?: string;
  expires_on?: string;
}

export interface ServerStats {
  total: number;
  available: number;
  unavailable: number;
  with_vehicle: number;
}

export interface ServerSkill {
  skill_name: string;
  skill_level: number;
  years_experience: number;
}

export interface ServerVehicle {
  id: string;
  brand: string;
  model: string;
  seats_total: number;
  can_transport_coworkers: boolean;
  is_active: boolean;
}

export interface ServerAvailability {
  id: string;
  start_datetime: string;
  end_datetime: string;
  status: string;
  note?: string | null;
  conflict?: boolean;
  conflict_reason?: string | null;
}

export interface ServerLocation {
  city: string;
  area: string;
  is_verified: boolean;
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

export interface ServerEvaluation {
  id: string;
  event_id: string;
  event_name: string;
  role: string;
  score: number;
  feedback?: string;
  evaluated_at: string;
}

export interface ServerEventHistory {
  id: string;
  event_id: string;
  event_name: string;
  event_date: string;
  role: string;
  assignment_status: string;
}

export interface ServerCreateRequest {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  gender: string;
  city_id: string;
  years_experience?: number;
  worker_type?: string;
  /** Step 24C-D-9. Omit or send null for "not recorded". */
  uniform_size?: ServerUniformSize | null;
  speed_score?: number;
  punctuality_score?: number;
  presentation_score?: number;
  communication_score?: number;
  teamwork_score?: number;
  discipline_score?: number;
  endurance_score?: number;
}

export interface ServerUpdateRequest {
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  gender?: string;
  city_id?: string;
  years_experience?: number;
  worker_type?: string;
  /**
   * Step 24C-D-9. An explicit `null` CLEARS a recorded size; omitting the key
   * leaves the stored value untouched.
   */
  uniform_size?: ServerUniformSize | null;
  speed_score?: number;
  punctuality_score?: number;
  presentation_score?: number;
  communication_score?: number;
  teamwork_score?: number;
  discipline_score?: number;
  endurance_score?: number;
  is_active?: boolean;
}

export interface ServerResponse {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  gender: string;
  city_id: string;
  years_experience: number;
  worker_type?: string;
  /** Step 24C-D-9. Null when the size was never recorded. */
  uniform_size?: ServerUniformSize | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type ActivityType =
  | 'event_created'
  | 'staff_assigned'
  | 'transport_created'
  | 'urgent_offer'
  | 'points_awarded'
  | 'ranking_calculated';

export interface ActivityItem {
  id: string;
  type: ActivityType;
  message: string;
  timestamp: string;
  event_id?: string;
}

export const EVENT_STATUSES = {
  PLANNED: 'Planifié',
  CONFIRMED: 'Confirmé',
  IN_PROGRESS: 'En cours',
  COMPLETED: 'Terminé',
  CANCELLED: 'Annulé',
} as const;

export const EVENT_PRIORITIES = {
  NORMAL: 'Normal',
  HIGH: 'Haute',
  CRITICAL: 'Critique',
} as const;

export const EVENT_DATE_RANGES = {
  ALL: 'Tous',
  UPCOMING: 'À venir',
  TODAY: "Aujourd'hui",
  PAST: 'Passés',
} as const;

export const ASSIGNMENT_STATUSES = {
  PROPOSED: 'Proposé',
  CONFIRMED: 'Confirmé',
  DECLINED: 'Refusé',
  CANCELLED: 'Annulé',
  COMPLETED: 'Terminé',
} as const;

export const WORKER_TYPES = {
  HARD_WORKER: 'Profil performant',
  BALANCED: 'Profil équilibré',
  SOFT_WORKER: 'Profil souple',
} as const;

export type WorkerType = keyof typeof WORKER_TYPES;

export interface EventDetailData {
  event: {
    id: string;
    name: string;
    client_name: string;
    city_id: string;
    city: string;
    address: string;
    latitude: number | null;
    longitude: number | null;
    start_datetime: string;
    end_datetime: string;
    guest_count: number;
    event_type: string;
    alcohol_service: boolean;
    food_products_count: number;
    priority: string;
    urgent: boolean;
    required_response_minutes: number | null;
    status: string;
    notes: string | null;
    /**
     * false when the venue position came from the city reference or the global
     * technical fallback instead of the event's own coordinates. Any distance
     * derived from this venue must then be presented as approximate.
     */
    has_exact_location: boolean;
  };
  staffing: {
    requested: number;
    selected: number;
    missing: number;
    percentage: number;
  };
  assignments: {
    id: string;
    server_id: string;
    server_name: string;
    first_name: string;
    last_name: string;
    gender: string;
    city: string;
    role: string;
    required_gender: string | null;
    score: number | null;
    distance_km: number | null;
    years_experience: number;
    skill_level: number;
    availability_status: string;
    status: 'PROPOSED' | 'CONFIRMED' | 'DECLINED' | 'CANCELLED' | 'COMPLETED';
    reasons: string[];
    conflict?: boolean;
    conflict_reason?: string | null;
  }[];
  requirements_detail: {
    requirement_id: string;
    role_name: string;
    required_gender: string | null;
    quantity: number;
    selected: number;
    missing: number;
    minimum_experience: number;
    minimum_skill_level: number;
  }[];
  transport?: {
    groups: {
      group_id: string;
      driver_server_id: string;
      driver_name: string;
      vehicle: string;
      capacity: number;
      passenger_count: number;
      estimated_distance_km: number | null;
      /** driver -> pickups -> venue. Prefer this over estimated_distance_km. */
      estimated_route_distance_km: number | null;
      /** false when the venue leg used the city reference or the global fallback. */
      has_exact_location: boolean;
      passengers: {
        server_id: string;
        name: string;
        pickup_order: number;
        pickup_status: string;
        distance_km: number | null;
      }[];
      status: string;
    }[];
    total_groups: number;
    total_passengers: number;
  };
}

export const USER_ROLES = {
  ADMIN: 'Administrateur',
  MANAGER: 'Manager',
  STAFF: 'Serveur',
} as const;

export type UserRole = keyof typeof USER_ROLES;

export const USER_ROLE_OPTIONS: { value: UserRole; label: string }[] = [
  { value: 'ADMIN', label: USER_ROLES.ADMIN },
  { value: 'MANAGER', label: USER_ROLES.MANAGER },
  { value: 'STAFF', label: USER_ROLES.STAFF },
];

export interface UserListItem {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface UserListResponse {
  items: UserListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export type UserFilters = {
  search: string;
  role: string;
  is_active: string;
};

export interface UserCreateRequest {
  email: string;
  password: string;
  role: UserRole;
  is_active: boolean;
}

export interface UserUpdateRequest {
  email?: string;
  role?: UserRole;
  is_active?: boolean;
  password?: string;
}

export interface DeactivateResponse {
  id: string;
  is_active: boolean;
  message: string;
}

export type AuditLogAction =
  | 'USER_CREATED'
  | 'USER_UPDATED'
  | 'USER_DEACTIVATED'
  // Step 24C-D-7: server-file and attestation administration. These keep
  // target_user_id NULL and identify the server through detail.server_id.
  | 'PROFILE_PHOTO_UPLOADED'
  | 'PROFILE_PHOTO_DELETED'
  | 'ATTESTATION_UPLOADED'
  | 'ATTESTATION_VERIFIED'
  | 'ATTESTATION_REJECTED'
  | 'ATTESTATION_SUPERSEDED';

export interface AuditLogItem {
  id: string;
  actor_user_id: string | null;
  target_user_id: string | null;
  action: AuditLogAction;
  detail: Record<string, unknown> | null;
  created_at: string;
  actor_email: string | null;
  target_email: string | null;
}

export interface AuditLogListResponse {
  items: AuditLogItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export type AuditLogFilters = {
  action: string;
  actor_user_id: string;
  target_user_id: string;
  created_after: string;
  created_before: string;
};

/* ---------------------------------------------------------------------------
 * Step 24C-D-10: event print-data contract.
 *
 * A faithful mirror of `EventPrintDataResponse` returned by
 * `GET /api/events/{event_id}/print-data` (Step 24C-D-8B). These types exist so
 * the print page consumes that ONE dedicated endpoint. Nothing here is
 * reconstructed from the event-detail, staffing or transport endpoints.
 *
 * PRIVACY. Two fields in this contract must never reach the rendered sheet:
 *   - `EventPrintEventResponse.latitude` / `.longitude`
 *   - `EventPrintTransportGroupResponse.estimated_route_distance_km` is fine,
 *     but the raw `departure_latitude` / `pickup_latitude` values are NOT part
 *     of this contract at all: the backend never returns them, because they are
 *     internal route data, not printable facts.
 * They are declared here only so the type matches the response exactly. The
 * print view renders a venue by ADDRESS and CITY only; no coordinate is ever
 * displayed. See `print/page.tsx`.
 * ------------------------------------------------------------------------ */

/** A real `server_skills` row: the server's real capability for a skill. */
export interface EventPrintActualSkillResponse {
  skill_id: string;
  skill_name: string;
  level: number;
  years_experience: number;
}

/**
 * VERIFIED attestation metadata only.
 *
 * The backend filters on VERIFIED, so `status` is always 'VERIFIED'. A PENDING
 * or REJECTED document is a document that has NOT been verified and must never
 * be presented on an operational sheet as a qualification.
 *
 * Deliberately no file path, no storage key, no URL, no document bytes.
 */
export interface EventPrintVerifiedAttestationResponse {
  attestation_id: string;
  qualification_name: string;
  status: string;
  verified_at?: string | null;
}

/** One staffing requirement: what the event NEEDS. */
export interface EventPrintRequirementResponse {
  requirement_id: string;
  role_name: string;
  quantity: number;
  required_gender?: string | null;
  minimum_experience: number;
  /**
   * A bare numeric THRESHOLD, named for what it is.
   *
   * `event_requirements` has no `skill_id`, so no skill identity can be
   * attached to this value and none is inferred from `role_name`. It is a
   * requirement and must never be presented as the server's own level -- that
   * is `EventPrintAssignmentResponse.actual_skills`.
   */
  required_minimum_skill_level: number;
  selected: number;
  missing: number;
}

/** One assigned server: the actual team for this event. */
export interface EventPrintAssignmentResponse {
  server_id: string;
  first_name: string;
  last_name: string;
  gender?: string | null;
  city?: string | null;
  years_experience?: number | null;
  role: string;
  assignment_status: string;
  assigned_at?: string | null;
  confirmed_at?: string | null;
  /**
   * The requirement minimum this assignment was matched against, repeated per
   * row so a printed line is self-contained.
   *
   * A REQUIREMENT, not a capability: never render this as the server's actual
   * skill level. Compare `actual_skills` on the same object.
   */
  required_minimum_skill_level: number;
  /**
   * Always null in practice: no selection score is persisted on an assignment,
   * and recomputing one here would invent data for a printed sheet.
   */
  score?: number | null;
  /** Step 24C-D-9. Null means the size was never recorded. */
  uniform_size?: ServerUniformSize | null;
  /**
   * A boolean ONLY. There is no public photo URL and none is invented: the
   * bytes are fetched from the existing authenticated endpoint on demand.
   */
  profile_photo_available: boolean;
  actual_skills: EventPrintActualSkillResponse[];
  verified_attestations: EventPrintVerifiedAttestationResponse[];
}

/** Event and venue facts for the sheet header. */
export interface EventPrintEventResponse {
  id: string;
  name: string;
  client_name?: string | null;
  event_type?: string | null;
  start_datetime?: string | null;
  end_datetime?: string | null;
  city?: string | null;
  address?: string | null;
  /**
   * Resolved VENUE coordinates.
   *
   * INTERNAL LOCATION DATA -- NEVER RENDERED. Declared for contract accuracy
   * only. The print view shows the venue by address and city.
   */
  latitude?: number | null;
  /** INTERNAL LOCATION DATA -- NEVER RENDERED. See `latitude`. */
  longitude?: number | null;
  guest_count?: number | null;
  status: string;
  priority?: string | null;
  urgent: boolean;
  /**
   * The RELATIVE response budget only. The backend computes no absolute
   * deadline, so none is displayed and none is invented here.
   */
  required_response_minutes?: number | null;
  notes?: string | null;
  /** Whether the venue coordinates above are the event's exact ones. */
  has_exact_location: boolean;
}

/** One confirmed transport group. */
export interface EventPrintPassengerResponse {
  server_id: string;
  name: string;
  pickup_order: number;
  pickup_status: string;
  /** Human-readable label. The raw coordinate is never part of this contract. */
  pickup_location_label: string;
}

/** A driver and their passengers. Cancelled groups are excluded by the backend. */
export interface EventPrintTransportGroupResponse {
  transport_group_id: string;
  driver_server_id: string;
  driver_name: string;
  vehicle: string;
  vehicle_type?: string | null;
  capacity: number;
  passenger_count: number;
  departure_time?: string | null;
  departure_location_label: string;
  destination_label: string;
  estimated_duration_minutes?: number | null;
  estimated_distance_km?: number | null;
  estimated_route_distance_km?: number | null;
  has_exact_location: boolean;
  status: string;
  passengers: EventPrintPassengerResponse[];
}

/** The complete print-data payload for one event. */
export interface EventPrintDataResponse {
  event: EventPrintEventResponse;
  requirements: EventPrintRequirementResponse[];
  assignments: EventPrintAssignmentResponse[];
  transport_groups: EventPrintTransportGroupResponse[];
}

export const AUDIT_LOG_ACTION_OPTIONS: { value: AuditLogAction; label: string }[] = [
  { value: 'USER_CREATED', label: 'Utilisateur créé' },
  { value: 'USER_UPDATED', label: 'Utilisateur mis à jour' },
  { value: 'USER_DEACTIVATED', label: 'Utilisateur désactivé' },
  { value: 'PROFILE_PHOTO_UPLOADED', label: 'Photo de profil ajoutée' },
  { value: 'PROFILE_PHOTO_DELETED', label: 'Photo de profil supprimée' },
  { value: 'ATTESTATION_UPLOADED', label: 'Attestation ajoutée' },
  { value: 'ATTESTATION_VERIFIED', label: 'Attestation vérifiée' },
  { value: 'ATTESTATION_REJECTED', label: 'Attestation rejetée' },
  { value: 'ATTESTATION_SUPERSEDED', label: 'Attestation remplacée' },
];
