"""Step 24C-D-11: server-side profile photo optimization.

Why this module exists
----------------------
The Step 24C-D-10 read-only audit proved the print sheet's *metadata* path was
already efficient: ``get_event_print_data`` issues a constant 8 SQL statements on
a single connection, with no per-server SQL loop, and its payload only grows
because the response genuinely contains N assignments. It was deliberately left
untouched.

The real cost was image delivery. The print page makes one authenticated request
per server that has a photo and waits for all of them before printing, and each
response carried the photo at its *original* uploaded size (up to 2 MiB). At 100
servers that is tens to hundreds of megabytes on a phone connection.

So the fix belongs at upload time, not at delivery time: shrink the bytes once,
store the small version, and let the existing endpoint deliver something a
print sheet can actually use.

Design decisions
----------------
* **Downscale only.** A photo already smaller than the target is never enlarged.
* **Aspect ratio preserved.** A single bounding-box scale, no crop.
* **Metadata removed.** Re-encoding without passing ``exif``/``icc_profile``
  discards EXIF, GPS tags, camera serials and colour profiles. A profile photo
  never needs them and they are privacy-relevant.
* **Orientation applied, not carried.** ``ImageOps.exif_transpose`` bakes the
  EXIF orientation flag into the pixels before it is dropped, so a phone photo
  taken in portrait is not stored sideways.
* **Transparency flattened onto white.** JPEG has no alpha channel. Matting onto
  white keeps a transparent-background PNG/WebP looking correct instead of
  turning the background black.
* **Never larger than the input.** If the re-encoded result would not actually be
  smaller, the original bytes are kept unchanged. Optimization can therefore only
  ever reduce payload and storage, never grow them.

Failure policy
--------------
Optimization is best effort and is never a reason to reject an upload. Magic-byte
validation in ``server_file_service`` remains the only gate for what is accepted.
If Pillow cannot open or fully decode the payload -- truncated, exotic, or a
decompression-bomb attempt caught by Pillow's own pixel-count guard, in which
case the original bytes are kept without ever decoding them -- the caller stores
the original bytes. A previously valid upload can never start failing because of
this step.
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import settings


@dataclass(frozen=True)
class OptimizedImage:
    """Outcome of an optimization attempt.

    ``mime_type`` always describes ``data``, so a caller can persist the pair
    without re-deriving anything. When ``optimized`` is False the payload and
    MIME type are exactly what came in.
    """

    data: bytes
    mime_type: str
    optimized: bool
    source_width: int | None = None
    source_height: int | None = None
    width: int | None = None
    height: int | None = None


def optimize_profile_photo(
    data: bytes,
    source_mime_type: str,
    max_dimension: int | None = None,
    quality: int | None = None,
) -> OptimizedImage:
    """Return an optimized representation of a validated profile photo.

    ``source_mime_type`` must be the MIME type already established by
    magic-byte validation, so this function never re-derives trust from the
    client. On any decoding failure the input is returned unchanged with
    ``optimized=False``.
    """
    max_dimension = max_dimension or settings.PROFILE_PHOTO_MAX_DIMENSION
    quality = quality or settings.PROFILE_PHOTO_JPEG_QUALITY
    output_mime_type = settings.PROFILE_PHOTO_OUTPUT_MIME_TYPE

    fallback = OptimizedImage(data=data, mime_type=source_mime_type, optimized=False)

    try:
        with Image.open(io.BytesIO(data)) as image:
            # Force the decode now, inside the guard, so a truncated or
            # oversized payload fails here instead of during save. Pillow's
            # own MAX_IMAGE_PIXELS check raises DecompressionBombError on a
            # tiny header claiming an enormous canvas; that is caught below and
            # the original bytes are stored without ever being expanded.
            image.load()
            source_width, source_height = image.size

            # Bake EXIF orientation into the pixels. Must happen before the
            # metadata is discarded, and before resizing so the resize works on
            # the visually correct orientation.
            oriented = ImageOps.exif_transpose(image) or image

            rgb = _to_rgb(oriented)

            # Single bounding-box scale: aspect ratio is preserved by
            # construction, and no upscaling.
            scaled = _downscale(rgb, max_dimension)

            buffer = io.BytesIO()
            scaled.save(
                buffer,
                format="JPEG",
                quality=quality,
                optimize=True,
                # No exif=, no icc_profile=, no xmp= : every metadata block is
                # dropped, including GPS.
                progressive=False,
            )
            encoded = buffer.getvalue()
            width, height = scaled.size

    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        # Includes Image.DecompressionBombWarning's hard-limit sibling
        # DecompressionBombError, which subclasses Exception via Warning's
        # sibling path; anything Pillow refuses is treated as "leave it alone".
        return fallback

    # Never store more bytes than we were given. A 2x2 PNG re-encoded as JPEG is
    # larger than the original; in that case the original wins.
    if len(encoded) >= len(data):
        return fallback

    return OptimizedImage(
        data=encoded,
        mime_type=output_mime_type,
        optimized=True,
        source_width=source_width,
        source_height=source_height,
        width=width,
        height=height,
    )


def profile_photo_etag(data: bytes) -> str:
    """A strong, opaque ETag for stored photo bytes.

    Derived from the content itself rather than from the row id, so it is stable
    for identical bytes and changes whenever the photo is replaced. Truncated to
    128 bits, which is far beyond collision risk for this purpose.

    Deliberately NOT derived from the database id or any other internal
    identifier: an ETag is echoed back to the client in a header, and internal
    storage ids must not leak through it.
    """
    digest = hashlib.sha256(data).hexdigest()[:32]
    return f'"{digest}"'


def _to_rgb(image: Image.Image) -> Image.Image:
    """Flatten any input mode onto an opaque white RGB canvas."""
    if image.mode == "RGB":
        return image
    if image.mode in ("RGBA", "LA") or "transparency" in image.info:
        rgba = image.convert("RGBA")
        white = Image.new("RGB", rgba.size, (255, 255, 255))
        white.paste(rgba, mask=rgba.split()[-1])
        return white
    # P, L, CMYK, I;16 and anything else. Converting CMYK through RGBA rather
    # than straight to RGB is what keeps its channels from being read swapped.
    return image.convert("RGBA").convert("RGB")


def _downscale(image: Image.Image, max_dimension: int) -> Image.Image:
    """Shrink so neither side exceeds ``max_dimension``. Never enlarges."""
    width, height = image.size
    longest = max(width, height)
    if longest <= max_dimension:
        return image

    scale = max_dimension / float(longest)
    target = (
        max(1, round(width * scale)),
        max(1, round(height * scale)),
    )
    # LANCZOS is the high-quality downsampling filter: it is the right choice
    # when shrinking (it low-pass filters before decimating, so it does not
    # alias thin features like facial detail).
    resample = getattr(Image, "Resampling", Image).LANCZOS
    return image.resize(target, resample)
