import { UserFilters } from '@/app/lib/types';

export const DEFAULT_USER_FILTERS: UserFilters = {
  search: '',
  role: '',
  is_active: '',
};

export const USER_ROLE_OPTIONS = [
  { value: 'ADMIN', label: 'Administrateur' },
  { value: 'MANAGER', label: 'Manager' },
  { value: 'STAFF', label: 'Serveur' },
] as const;
