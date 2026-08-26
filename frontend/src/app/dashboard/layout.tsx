'use client';

import Sidebar from '@/app/components/dashboard/Sidebar';
import Header from '@/app/components/dashboard/Header';
import RouteGuard from '@/app/components/dashboard/RouteGuard';
import { LiveAnnouncer } from '@/app/components/ui/LiveAnnouncer';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <RouteGuard>
      <div className="min-h-screen bg-gray-50">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-[#D4AF37] focus:text-white focus:text-sm focus:font-medium focus:rounded-lg"
        >
          Passer au contenu principal
        </a>
        <LiveAnnouncer />
        <Sidebar />
        <div className="ml-64">
          <Header />
          <main id="main-content" className="p-8">
            {children}
          </main>
        </div>
      </div>
    </RouteGuard>
  );
}
