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
  }[];
  points: {
    total_points: number;
    current_month_points: number;
    previous_month_points: number;
    rank: number | null;
  };
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
  note?: string;
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

export interface ActivityItem {
  id: string;
  type: 'event_created' | 'staff_assigned' | 'points_awarded';
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
    start_datetime: string;
    end_datetime: string;
    guest_count: number;
    event_type: string;
    alcohol_service: boolean;
    food_products_count: number;
    priority: string;
    urgent: boolean;
    is_urgent: boolean;
    required_response_minutes: number | null;
    status: string;
    notes: string | null;
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
