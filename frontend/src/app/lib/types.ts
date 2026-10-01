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
