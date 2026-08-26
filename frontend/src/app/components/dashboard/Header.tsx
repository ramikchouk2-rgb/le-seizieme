'use client';

import { useMemo } from 'react';
import { getCurrentUser } from '@/app/lib/api';

const ROLE_LABELS: Record<string, string> = {
  admin: 'Administrateur',
  manager: 'Manager',
  staff: 'Staff',
};

export default function Header({ title = 'Dashboard' }: { title?: string }) {
  const user = useMemo(() => getCurrentUser(), []);

  return (
    <header className="sticky top-0 z-40 bg-white/80 backdrop-blur-md border-b border-gray-200">
      <div className="flex items-center justify-between px-8 py-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{title}</h2>
          <p className="text-sm text-gray-500">Le Seizième — Gestion événementielle</p>
        </div>

        <div className="flex items-center gap-4">
          <button aria-label="Notifications" className="relative p-2 text-gray-600 hover:text-gray-900 transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
            </svg>
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-[#D4AF37] rounded-full"></span>
          </button>

          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-[#D4AF37]/10 flex items-center justify-center text-[#D4AF37] font-bold text-sm border border-[#D4AF37]/20">
              {user?.email?.[0]?.toUpperCase() || 'B'}
            </div>
            <div className="hidden md:block">
              <p className="text-sm font-medium text-gray-900">{user?.email || 'Boss'}</p>
              <p className="text-xs text-gray-500">{ROLE_LABELS[user?.role || 'admin'] || 'Administrateur'}</p>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
