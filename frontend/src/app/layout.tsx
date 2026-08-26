import type { Metadata } from 'next'
import { QueryProvider } from '@/app/lib/query-provider';
import { ErrorBoundary } from '@/app/lib/error-boundary';
import './globals.css'

export const metadata: Metadata = {
  title: 'Le Seizième',
  description: 'Plateforme professionnelle pour traiteur événementiel',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="fr">
      <body>
        <ErrorBoundary>
          <QueryProvider>
            {children}
          </QueryProvider>
        </ErrorBoundary>
      </body>
    </html>
  )
}
