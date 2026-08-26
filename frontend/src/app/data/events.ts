import {
  Event,
  EventRequirement,
  EventStaffing,
  EventFilters,
} from '@/app/components/dashboard/types';

export const ALL_CITIES = [
  'Tunis',
  'Ariana',
  'La Marsa',
  'Manouba',
  'Ben Arous',
  'Nabeul',
  'Hammamet',
  'Bizerte',
  'Sousse',
  'Monastir',
] as const;

export const EVENT_STATUSES = {
  PLANNED: 'Planifié',
  STAFFING: 'Recrutement',
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

export const DEFAULT_EVENT_FILTERS: EventFilters = {
  search: '',
  city: '',
  status: '',
  priority: '',
  urgent: '',
  staffing: '',
  dateRange: '',
  sort_by: 'start_datetime',
  sort_order: 'asc',
};
