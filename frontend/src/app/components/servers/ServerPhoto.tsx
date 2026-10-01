'use client';

import { useEffect, useState } from 'react';

import { getServerProfilePhoto } from '@/app/lib/api';

const SIZE_CLASSES: Record<string, string> = {
  sm: 'w-8 h-8 text-xs',
  md: 'w-12 h-12 text-sm',
  lg: 'w-16 h-16 text-base',
  xl: 'w-32 h-32 text-2xl',
};

interface ServerPhotoProps {
  serverId: string;
  firstName: string;
  lastName: string;
  /** From list/detail metadata. When false, no photo request is made at all. */
  hasProfilePhoto?: boolean;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
  /** Bump this to force a reload after an upload or a deletion. */
  refreshToken?: number;
}

/**
 * Renders a server's profile photo, falling back to initials.
 *
 * Step 24C-D-5. The photo bytes come from an authenticated endpoint and are
 * fetched only when the caller already knows a photo exists, so a list view
 * with no photos issues no image requests at all. The object URL is revoked on
 * unmount and whenever the source changes, so no blob is leaked.
 *
 * No storage detail (URL, path, id) is ever surfaced to the user; a failure to
 * load simply degrades to initials.
 */
export default function ServerPhoto({
  serverId,
  firstName,
  lastName,
  hasProfilePhoto,
  size = 'md',
  className = '',
  refreshToken = 0,
}: ServerPhotoProps) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);

  const initials = `${firstName?.[0] ?? ''}${lastName?.[0] ?? ''}`.toUpperCase();
  const sizeClass = SIZE_CLASSES[size] ?? SIZE_CLASSES.md;

  useEffect(() => {
    // No photo known: render initials and make no request.
    if (!hasProfilePhoto) {
      setObjectUrl(null);
      setLoading(false);
      setFailed(false);
      return;
    }

    let cancelled = false;
    let createdUrl: string | null = null;
    setLoading(true);
    setFailed(false);

    getServerProfilePhoto(serverId)
      .then((blob) => {
        if (cancelled) return;
        if (!blob) {
          setObjectUrl(null);
          setFailed(true);
          return;
        }
        createdUrl = URL.createObjectURL(blob);
        setObjectUrl(createdUrl);
      })
      .catch(() => {
        // Never surface the reason: the UI just falls back to initials.
        if (!cancelled) {
          setObjectUrl(null);
          setFailed(true);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
      if (createdUrl) URL.revokeObjectURL(createdUrl);
    };
  }, [serverId, hasProfilePhoto, refreshToken]);

  const showPhoto = Boolean(objectUrl) && !failed;

  return (
    <div
      className={`${sizeClass} rounded-full flex items-center justify-center overflow-hidden shrink-0 ${
        showPhoto ? 'bg-gray-100' : 'bg-[#D4AF37]/10 text-[#D4AF37] font-bold'
      } ${className}`}
      aria-hidden="true"
    >
      {showPhoto ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={objectUrl as string}
          alt=""
          className="w-full h-full object-cover"
        />
      ) : (
        <span className={loading ? 'opacity-40 animate-pulse' : ''}>{initials}</span>
      )}
    </div>
  );
}