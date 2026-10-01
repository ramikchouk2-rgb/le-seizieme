"""Step 24C-D-6: attestation API models.

These models are metadata only. No model in this file can carry document bytes,
a public URL, or any location data.
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class AttestationFileMetadataResponse(BaseModel):
    """Descriptive metadata about the stored document. Never the bytes."""

    id: str
    mime_type: str
    original_filename: Optional[str] = None
    file_size: int


class ServerAttestationResponse(BaseModel):
    """One attestation record.

    `counts_as_verified_qualification` is the field the UI and any consumer must
    use to decide whether this document is a real qualification. It is true only
    for status VERIFIED, which requires an explicit Manager/Admin decision.
    """

    id: str
    server_id: str
    file_id: str
    status: str
    status_label: str
    counts_as_verified_qualification: bool
    qualification_name: str
    issuing_organization: Optional[str] = None
    issued_on: Optional[str] = None
    expires_on: Optional[str] = None
    rejection_reason: Optional[str] = None
    verified_at: Optional[str] = None
    verified_by: Optional[str] = None
    superseded_by_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    file: AttestationFileMetadataResponse


class ServerAttestationListResponse(BaseModel):
    items: list[ServerAttestationResponse]
    total: int
    # Convenience aggregate so the UI can state the qualification count without
    # recounting. Derived only from VERIFIED rows.
    verified_count: int


class ServerAttestationCreateRequest(BaseModel):
    """Metadata accompanying an uploaded document.

    `status` is deliberately absent: an upload can only ever produce PENDING.
    """

    qualification_name: str = Field(min_length=1, max_length=200)
    issuing_organization: Optional[str] = Field(default=None, max_length=200)
    issued_on: Optional[date] = None
    expires_on: Optional[date] = None

    @field_validator("qualification_name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        cleaned = (v or "").strip()
        if not cleaned:
            raise ValueError("L'intitulé de la qualification est obligatoire.")
        return cleaned


class AttestationRejectRequest(BaseModel):
    """Rejection requires a reason; it is the audit trail for the decision."""

    rejection_reason: str = Field(min_length=1)

    @field_validator("rejection_reason")
    @classmethod
    def reason_not_blank(cls, v: str) -> str:
        cleaned = (v or "").strip()
        if not cleaned:
            raise ValueError("Un motif de rejet est obligatoire.")
        return cleaned


class AttestationSupersedeRequest(BaseModel):
    superseded_by_id: Optional[str] = None
