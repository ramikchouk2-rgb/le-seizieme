import { ServerFilters, ServerProfile } from '@/app/components/dashboard/types';

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

export const ALL_SKILLS = [
  'Food',
  'Service à table',
  'Buffet',
  'Barman',
  'Bar',
  'Cocktail',
  'Mise en place',
  'Débarrassage',
] as const;

export const DEFAULT_FILTERS: ServerFilters = {
  search: '',
  city: '',
  gender: '',
  availability: '',
  worker_type: '',
  has_vehicle: '',
  can_transport: '',
  location_verified: '',
  experience_range: '',
  skill: '',
  sort_by: 'last_name',
  sort_order: 'asc',
};
