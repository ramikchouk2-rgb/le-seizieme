'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { getCurrentUser } from '@/app/lib/api';
import { logout } from '@/app/lib/api-client';

const ROLE_LABELS: Record<string, string> = {
  admin: 'Administrateur',
  manager: 'Manager',
  staff: 'Staff',
};

const menuItems = [
  { href: '/dashboard', label: 'Dashboard', icon: '🏠' },
  { href: '/dashboard/servers', label: 'Serveurs', icon: '👥' },
  { href: '/dashboard/events', label: 'Événements', icon: '📅' },
  { href: '/dashboard/gamification', label: 'Gamification', icon: '🏆' },
];

export default function Sidebar() {
  const pathname = usePathname();
  const user = getCurrentUser();

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-[#0f0f0f] text-[#e5e5e5] flex flex-col z-50">
      <div className="p-6 border-b border-white/10">
        <h1 className="text-xl font-bold text-[#D4AF37] tracking-wide">Le Seizième</h1>
        <p className="text-xs text-gray-400 mt-1">Espace Boss</p>
      </div>

      <nav className="flex-1 overflow-y-auto sidebar-scroll p-4 space-y-1">
        {menuItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname?.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-[#D4AF37]/10 text-[#D4AF37] border border-[#D4AF37]/20'
                  : 'text-gray-300 hover:bg-white/5 hover:text-white'
              }`}
            >
              <span className="text-base">{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-white/10">
        <div className="flex items-center gap-3 px-4 py-3">
          <div className="w-8 h-8 rounded-full bg-[#D4AF37]/20 flex items-center justify-center text-[#D4AF37] text-sm font-bold">
            {user?.email?.[0]?.toUpperCase() || 'B'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">{user?.email || 'Boss'}</p>
            <p className="text-xs text-gray-400 truncate">{ROLE_LABELS[user?.role || 'admin'] || 'Administrateur'}</p>
          </div>
        </div>
        <button
          onClick={logout}
          className="w-full mt-2 px-4 py-2 text-sm font-medium rounded-lg border border-white/10 text-gray-300 hover:bg-white/5 hover:text-white transition-colors"
        >
          Déconnexion
        </button>
      </div>
    </aside>
  );
}
