'use client';

import { useState, useCallback, useRef } from 'react';

type AnnouncementType = 'success' | 'error' | 'polite';

interface Announcement {
  id: number;
  message: string;
  type: AnnouncementType;
}

let announcementId = 0;

export function useAnnouncer() {
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const announce = useCallback((message: string, type: AnnouncementType = 'polite') => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    const id = ++announcementId;
    setAnnouncements((prev) => [...prev, { id, message, type }]);

    timeoutRef.current = setTimeout(() => {
      setAnnouncements((prev) => prev.filter((a) => a.id !== id));
    }, 5000);
  }, []);

  const announceSuccess = useCallback(
    (message: string) => announce(message, 'success'),
    [announce]
  );

  const announceError = useCallback(
    (message: string) => announce(message, 'error'),
    [announce]
  );

  return {
    announcements,
    announce,
    announceSuccess,
    announceError,
  };
}
