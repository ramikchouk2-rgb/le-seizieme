'use client';

import { useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { getCurrentUser } from '@/app/lib/api';
import type { UserResponse } from '@/app/lib/api-client';

const ADMIN_ONLY_PATHS = ['/dashboard/users'];

export function isAdmin(user: UserResponse | null): boolean {
  return (user?.role || '').toUpperCase() === 'ADMIN';
}

export function useAdminGuard() {
  const router = useRouter();
  const user = useMemo(() => getCurrentUser(), []);
  const isAllowed = isAdmin(user);

  return { user, isAllowed, router, ADMIN_ONLY_PATHS };
}
