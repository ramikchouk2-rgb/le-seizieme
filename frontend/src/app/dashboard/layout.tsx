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
        {/*
          `dashboard-content-offset` is a print-only hook: `@media print` in
          globals.css sets its margin-left to 0 so the printable sheet is not
          pushed right by the (hidden) sidebar. `ml-64` still controls the
          screen layout. Step 24C-D-10.
        */}
        <div className="ml-64 dashboard-content-offset">
          <Header />
          <main id="main-content" className="p-8">
            {children}
          </main>
        </div>
      </div>
    </RouteGuard>
  );
}
