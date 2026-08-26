'use client';

import { useAnnouncer } from './Announcer';

export function LiveAnnouncer() {
  const { announcements } = useAnnouncer();

  const politeMessages = announcements.filter((a) => a.type !== 'error');
  const errorMessages = announcements.filter((a) => a.type === 'error');

  return (
    <>
      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {politeMessages.map((announcement) => (
          <div key={announcement.id} role="status">
            {announcement.message}
          </div>
        ))}
      </div>
      {errorMessages.length > 0 && (
        <div aria-live="assertive" aria-atomic="true" className="sr-only">
          {errorMessages.map((announcement) => (
            <div key={announcement.id} role="alert">
              {announcement.message}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
