import { AuditLogFilters } from '@/app/lib/types';

export const DEFAULT_AUDIT_LOG_FILTERS: AuditLogFilters = {
  action: '',
  actor_user_id: '',
  target_user_id: '',
  created_after: '',
  created_before: '',
};