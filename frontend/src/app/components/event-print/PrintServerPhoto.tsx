'use client';

import { useEffect, useState } from 'react';

import { getServerProfilePhoto } from '@/app/lib/api';

interface PrintServerPhotoProps {
  serverId: string;
  firstName: string;
  lastName: string;
  /**
   * `profile_photo_available` from the print-data contract.
   *
   * This is a BOOLEAN and nothing more. When it is false no request is made at
   * all, so a sheet with no photos issues no image traffic.
   */
  hasProfilePhoto: boolean;
  /** Called once this photo has settled (loaded or failed), so printing can wait. */
  onSettled?: () => void;
}

/**
 * A server's profile photo for the printable sheet, with an explicit
 * "Photo non disponible" placeholder.
 *
 * Step 24C-D-10. Two deliberate choices:
 *
 * 1. NO INVENTED URL. The print-data endpoint returns availability only, so
 *    there is no public photo URL to point an `<img>` at. The bytes come from
 *    the EXISTING authenticated endpoint through `getServerProfilePhoto`,
 *    exactly as the rest of the app does, and are rendered from a blob object
 *    URL. No endpoint is made public and no security is weakened. If the bytes
 *    cannot be fetched the sheet degrades to the placeholder rather than
 *    exposing a storage path or a file id.
 *
 * 2. THE SHEET WAITS FOR PHOTOS. A photo that resolves after `window.print()`
 *    would print blank. `onSettled` lets the page hold the print trigger until
 *    every photo has settled.
 */
export default function PrintServerPhoto({
  serverId,
  firstName,
  lastName,
  hasProfilePhoto,
  onSettled,
}: PrintServerPhotoProps) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [settled, setSettled] = useState(!hasProfilePhoto);

  useEffect(() => {
    // Availability is known false: nothing to fetch, already settled.
    if (!hasProfilePhoto) {
      setObjectUrl(null);
      setSettled(true);
      return;
    }

    let cancelled = false;
    let createdUrl: string | null = null;
    setSettled(false);

    getServerProfilePhoto(serverId)
      .then((blob) => {
        if (cancelled) return;
        if (!blob) {
          // 404 from the content endpoint: the photo was deleted or the
          // metadata is stale. Both are the same placeholder, no detail shown.
          setObjectUrl(null);
          return;
        }
        createdUrl = URL.createObjectURL(blob);
        setObjectUrl(createdUrl);
      })
      .catch(() => {
        // Never surface the reason: a failed fetch is a missing photo here.
        if (!cancelled) setObjectUrl(null);
      })
      .finally(() => {
        if (cancelled) return;
        setSettled(true);
        onSettled?.();
      });

    return () => {
      cancelled = true;
      if (createdUrl) URL.revokeObjectURL(createdUrl);
    };
    // `onSettled` is intentionally not a dependency: it is a notification, not
    // an input, and re-running the fetch when the parent re-creates the
    // callback would issue a duplicate image request.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [serverId, hasProfilePhoto]);

  const altText = firstName || lastName ? `Photo de ${firstName} ${lastName}`.trim() : 'Photo du serveur';

  return (
    <div className="print-photo shrink-0">
      {objectUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={objectUrl}
          alt={altText}
          className="print-photo-img"
          data-testid="print-photo-image"
        />
      ) : (
        <div
          className="print-photo-placeholder"
          data-testid="print-photo-placeholder"
          role="img"
          aria-label="Photo non disponible"
        >
          {/* A neutral placeholder: never a broken image, never a broken icon. */}
          <span>Photo non disponible</span>
        </div>
      )}
      {!settled && (
        // Screen-only hint. Prints as nothing, because it only exists while a
        // photo is still loading and printing waits for that to finish.
        <span className="print-only-hidden" aria-hidden="true" />
      )}
    </div>
  );
}