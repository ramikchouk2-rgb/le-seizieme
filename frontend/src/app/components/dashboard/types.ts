export * from '@/app/lib/types';

export interface Server {
  id: string;
  first_name: string;
  last_name: string;
  gender: string;
  city: string;
  years_experience: number;
  worker_type: string;
  availability_status: string;
  vehicle?: {
    brand: string;
    model: string;
    seats_total: number;
    can_transport_coworkers: boolean;
  };
}

export interface Event {
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
  requirements: EventRequirement[];
  selected_count?: number;
}

export interface EventRequirement {
  role_name: string;
  quantity: number;
  required_gender: string | null;
  minimum_experience: number;
  minimum_skill_level: number;
  accepted?: number;
  remaining?: number;
}

export interface Ranking {
  rank: number;
  server_id: string;
  server_name: string;
  points: number;
}

export interface UrgentEvent {
  event_id: string;
  name: string;
  is_urgent: boolean;
  status: string;
  requirements: {
    role: string;
    requested: number;
    accepted: number;
    remaining: number;
  }[];
  waves: {
    wave_number: number;
    offers_sent: number;
    pending: number;
    accepted: number;
    declined: number;
    expired: number;
  }[];
  staffing: {
    total_required: number;
    total_confirmed: number;
    total_remaining: number;
  };
}

export interface StaffAssignment {
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
}

export interface EventDetailData {
  event: Event;
  staffing: EventStaffing;
  assignments: StaffAssignment[];
  requirements_detail: {
    requirement_id: string;
    role_name: string;
    required_gender: string | null;
    quantity: number;
    selected: number;
    missing: number;
    minimum_experience: number;
    minimum_skill_level: number;
    assignments?: StaffAssignment[];
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

export interface EventStaffing {
  requested: number;
  selected: number;
  missing: number;
  percentage: number;
}

export interface EventFilters {
  search: string;
  city: string;
  status: string;
  priority: string;
  urgent: string;
  staffing: string;
  dateRange: string;
  sort_by: string;
  sort_order: 'asc' | 'desc';
}
