from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from pydantic import ValidationError as PydanticValidationError

from app.core.database import get_pool
from app.core.deps import get_current_user_dep, require_manager_or_admin
from app.models.attestations import (
    AttestationRejectRequest,
    AttestationSupersedeRequest,
    ServerAttestationCreateRequest,
    ServerAttestationListResponse,
    ServerAttestationResponse,
)
from app.models.servers import (
    ServerAvailabilityCreateRequest,
    ServerAvailabilityListResponse,
    ServerAvailabilityResponse,
    ServerAvailabilityUpdateRequest,
    ServerCreateRequest,
    ServerFileMetadataResponse,
    ServerListItem,
    ServerListResponse,
    ServerProfileResponse,
    ServerSkillCreateRequest,
    ServerSkillResponse,
    ServerSkillUpdateRequest,
    ServerStatsResponse,
    ServerUpdateRequest,
    ServerVehicleCreateRequest,
    ServerVehicleResponse,
    ServerVehicleUpdateRequest,
    ServerResponse,
)
from app.services.image_optimizer import profile_photo_etag
from app.services.server_file_service import (
    delete_current_profile_photo,
    get_current_profile_photo_content,
    server_exists,
    upload_profile_photo,
)
from app.services.server_attestation_service import (
    create_attestation,
    get_attestation,
    get_attestation_document,
    list_attestations,
    reject_attestation,
    supersede_attestation,
    verify_attestation,
)
from app.services.server_service import (
    add_server_skill,
    create_server,
    load_server_detail,
    load_server_list,
    load_server_stats,
    remove_server_skill,
    update_server,
    update_server_skill,
)

router = APIRouter()


@router.get("/servers", response_model=ServerListResponse, dependencies=[Depends(get_current_user_dep)])
async def get_servers(
    search: str | None = Query(default=None),
    city: str | None = Query(default=None),
    gender: str | None = Query(default=None),
    availability: str | None = Query(default=None),
    worker_type: str | None = Query(default=None),
    has_vehicle: bool | None = Query(default=None),
    can_transport: bool | None = Query(default=None),
    location_verified: bool | None = Query(default=None),
    min_experience: int | None = Query(default=None, ge=0),
    max_experience: int | None = Query(default=None, ge=0),
    skill: str | None = Query(default=None),
    sort_by: str | None = Query(default="first_name"),
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
) -> ServerListResponse:
    items, total = await load_server_list(
        search=search,
        city=city,
        gender=gender,
        availability=availability,
        worker_type=worker_type,
        has_vehicle=has_vehicle,
        can_transport=can_transport,
        location_verified=location_verified,
        min_experience=min_experience,
        max_experience=max_experience,
        skill=skill,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    total_pages = max(1, -(-total // page_size))
    return ServerListResponse(
        items=[ServerListItem(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/servers/stats", response_model=ServerStatsResponse, dependencies=[Depends(get_current_user_dep)])
async def get_servers_stats() -> ServerStatsResponse:
    stats = await load_server_stats()
    return ServerStatsResponse(**stats)


@router.get("/servers/{server_id}", response_model=ServerProfileResponse, dependencies=[Depends(get_current_user_dep)])
async def get_server_detail(server_id: str) -> ServerProfileResponse:
    data = await load_server_detail(server_id)
    if not data:
        raise HTTPException(status_code=404, detail="Server not found")
    return ServerProfileResponse(**data)


@router.post("/servers", response_model=ServerResponse, dependencies=[Depends(require_manager_or_admin)])
async def create_server_endpoint(payload: ServerCreateRequest) -> ServerResponse:
    result = await create_server(payload.model_dump())
    return ServerResponse(**result)


@router.patch("/servers/{server_id}", response_model=ServerResponse, dependencies=[Depends(require_manager_or_admin)])
async def update_server_endpoint(server_id: str, payload: ServerUpdateRequest) -> ServerResponse:
    result = await update_server(server_id, payload.model_dump(exclude_unset=True))
    return ServerResponse(**result)


@router.post("/servers/{server_id}/skills", response_model=ServerSkillResponse, dependencies=[Depends(require_manager_or_admin)])
async def add_skill_endpoint(server_id: str, payload: ServerSkillCreateRequest) -> ServerSkillResponse:
    result = await add_server_skill(server_id, payload.model_dump())
    return ServerSkillResponse(**result)


@router.patch("/servers/{server_id}/skills/{skill_id}", response_model=ServerSkillResponse, dependencies=[Depends(require_manager_or_admin)])
async def update_skill_endpoint(server_id: str, skill_id: str, payload: ServerSkillUpdateRequest) -> ServerSkillResponse:
    result = await update_server_skill(server_id, skill_id, payload.model_dump(exclude_unset=True))
    return ServerSkillResponse(**result)


@router.delete("/servers/{server_id}/skills/{skill_id}", dependencies=[Depends(require_manager_or_admin)])
async def remove_skill_endpoint(server_id: str, skill_id: str) -> dict[str, str]:
    await remove_server_skill(server_id, skill_id)
    return {"message": "Compétence supprimée avec succès."}


# =========================================================
# Server files / profile photo (Step 24C-D-5)
#
# There is deliberately NO public or unauthenticated image endpoint. Every route
# below reuses `require_manager_or_admin`, the same dependency the rest of the
# server-management surface uses, so photo management follows existing
# permissions. No staff self-service identity model is invented here.
# =========================================================


@router.put(
    "/servers/{server_id}/files/profile-photo",
    response_model=ServerFileMetadataResponse,
    status_code=201,
    dependencies=[Depends(require_manager_or_admin)],
)
async def upload_profile_photo_endpoint(
    server_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_manager_or_admin),
) -> ServerFileMetadataResponse:
    """Upload or replace a server's profile photo.
    Content is validated by magic bytes in the service layer; this handler only
    moves bytes and hands off. The response is metadata only.

    Step 24C-D-7: `current_user` is the authenticated Manager/Admin and becomes
    the audit actor. It can never come from the request body.
    """
    data = await file.read()
    metadata = await upload_profile_photo(
        server_id=server_id,
        data=data,
        declared_mime_type=file.content_type,
        original_filename=file.filename,
        actor_id=str(current_user["id"]),
    )
    return ServerFileMetadataResponse(**metadata)


@router.get(
    "/servers/{server_id}/files/profile-photo",
    dependencies=[Depends(require_manager_or_admin)],
)
async def get_profile_photo_endpoint(server_id: str, request: Request) -> Response:
    """Return the photo bytes to an authorized manager/admin.

    This is the ONLY endpoint that returns photo BYTEA. The response is
    explicitly marked private so a photo cannot be retained by a shared cache
    or intermediary. No public URL is generated or returned.

    Step 24C-D-11, delivery: the bytes are the optimized representation produced
    at upload time, so nothing about this response shape changed -- only its
    size. A print sheet that used to pull a 2 MiB original now pulls the
    downscaled, metadata-free version.

    Step 24C-D-11, connections: the server-exists check and the photo lookup
    share ONE pooled connection. Previously each helper acquired its own, so a
    single photo request could occupy two pool slots for the life of the request.

    Step 24C-D-11, caching: `private, no-cache` plus a content-derived strong
    ETag. This is a conditional-request policy, not a relaxation of privacy:
    `private` forbids any shared cache, and `no-cache` forces the browser to
    revalidate with the server before every reuse, so the Authorization header
    is still required every single time and an unauthorized client can never be
    served from a cache. What it buys is that a reprint or a page reload sends
    `If-None-Match` and receives a bodiless 304 instead of re-downloading N
    photos. The previous `no-store` is deliberately not simply relaxed to
    `max-age=<n>`: a heuristic freshness lifetime would let bytes be reused
    without re-authorization.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        if not await server_exists(server_id, conn=conn):
            raise HTTPException(status_code=404, detail="Serveur introuvable.")

        row = await get_current_profile_photo_content(server_id, conn=conn)

    if row is None:
        raise HTTPException(
            status_code=404, detail="Aucune photo de profil pour ce serveur."
        )

    content = bytes(row["content"])
    etag = profile_photo_etag(content)

    if_none_match = request.headers.get("if-none-match")
    if if_none_match and any(
        candidate.strip() in (etag, "*") for candidate in if_none_match.split(",")
    ):
        return Response(
            status_code=304,
            headers={
                "Cache-Control": "private, no-cache",
                "ETag": etag,
                "X-Content-Type-Options": "nosniff",
            },
        )

    return Response(
        content=content,
        media_type=row["mime_type"],
        headers={
            # Private per-server data: a shared cache must never store it.
            # `no-cache` (not `no-store`) allows the browser to KEEP the bytes
            # but requires revalidation before every reuse, which is what makes
            # the ETag conditional request above safe.
            "Cache-Control": "private, no-cache",
            "ETag": etag,
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "inline",
        },
    )


@router.delete(
    "/servers/{server_id}/files/profile-photo",
    dependencies=[Depends(require_manager_or_admin)],
)
async def delete_profile_photo_endpoint(
    server_id: str,
    current_user: dict = Depends(require_manager_or_admin),
) -> dict[str, Any]:
    """Deactivate the current profile photo (row retained as history).

    Step 24C-D-7: the actor comes from the authenticated user so the deletion can
    be audited. Authorization is unchanged.
    """
    if not await server_exists(server_id):
        raise HTTPException(status_code=404, detail="Serveur introuvable.")
    removed = await delete_current_profile_photo(server_id, actor_id=str(current_user["id"]))
    if not removed:
        raise HTTPException(
            status_code=404, detail="Aucune photo de profil pour ce serveur."
        )
    return {"message": "Photo de profil supprimée avec succès."}


# =========================================================
# Professional attestations (Step 24C-D-6)
#
# Routes follow the existing server-management convention (`/api/servers/...`,
# not a second `/api/v1` style) and reuse `require_manager_or_admin`, so
# attestations inherit exactly the permissions of the rest of server management.
# There is no STAFF self-service route.
# =========================================================


@router.post(
    "/servers/{server_id}/attestations",
    response_model=ServerAttestationResponse,
    status_code=201,
    dependencies=[Depends(require_manager_or_admin)],
)
async def create_attestation_endpoint(
    server_id: str,
    file: UploadFile = File(...),
    qualification_name: str | None = Form(default=None),
    issuing_organization: str | None = Form(default=None),
    issued_on: str | None = Form(default=None),
    expires_on: str | None = Form(default=None),
    current_user: dict = Depends(require_manager_or_admin),
) -> ServerAttestationResponse:
    """Upload a document and create a PENDING attestation.

    The response status is always PENDING: uploading never verifies anything.

    Metadata arrives as multipart form fields (this FastAPI version predates
    Pydantic-model form binding) and is then validated through the same request
    model the rest of the API uses, so the field rules stay in one place.
    """
    try:
        payload = ServerAttestationCreateRequest(
            qualification_name=qualification_name or "",
            issuing_organization=issuing_organization,
            issued_on=issued_on or None,
            expires_on=expires_on or None,
        )
    except PydanticValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=exc.errors()[0]["msg"] if exc.errors() else "Paramètres invalides.",
        ) from exc

    data = await file.read()
    result = await create_attestation(
        server_id=server_id,
        data=data,
        declared_mime_type=file.content_type,
        original_filename=file.filename,
        qualification_name=payload.qualification_name,
        issuing_organization=payload.issuing_organization,
        issued_on=payload.issued_on,
        expires_on=payload.expires_on,
        actor_id=str(current_user["id"]),
    )
    return ServerAttestationResponse(**result)


@router.get(
    "/servers/{server_id}/attestations",
    response_model=ServerAttestationListResponse,
    dependencies=[Depends(require_manager_or_admin)],
)
async def list_attestations_endpoint(
    server_id: str,
    include_superseded: bool = Query(default=True),
) -> ServerAttestationListResponse:
    items = await list_attestations(
        server_id, include_superseded=include_superseded
    )
    return ServerAttestationListResponse(
        items=[ServerAttestationResponse(**i) for i in items],
        total=len(items),
        # Only VERIFIED counts as a qualification.
        verified_count=sum(
            1 for i in items if i["counts_as_verified_qualification"]
        ),
    )


@router.get(
    "/servers/{server_id}/attestations/{attestation_id}",
    response_model=ServerAttestationResponse,
    dependencies=[Depends(require_manager_or_admin)],
)
async def get_attestation_endpoint(
    server_id: str, attestation_id: str
) -> ServerAttestationResponse:
    return ServerAttestationResponse(**await get_attestation(server_id, attestation_id))


@router.get(
    "/servers/{server_id}/attestations/{attestation_id}/file",
    dependencies=[Depends(require_manager_or_admin)],
)
async def get_attestation_file_endpoint(
    server_id: str, attestation_id: str
) -> Response:
    """Return the document bytes to an authorized Manager/Admin.

    The only attestation endpoint that returns content. Private and uncacheable,
    like the profile photo endpoint, and it never emits a public URL.
    """
    row = await get_attestation_document(server_id, attestation_id)
    return Response(
        content=bytes(row["content"]),
        media_type=row["mime_type"],
        headers={
            "Cache-Control": "private, no-store, max-age=0",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "inline",
        },
    )


@router.patch(
    "/servers/{server_id}/attestations/{attestation_id}/verify",
    response_model=ServerAttestationResponse,
    dependencies=[Depends(require_manager_or_admin)],
)
async def verify_attestation_endpoint(
    server_id: str,
    attestation_id: str,
    current_user: dict = Depends(require_manager_or_admin),
) -> ServerAttestationResponse:
    """Explicitly verify a PENDING attestation.

    The verifier is taken from the authenticated user; it cannot be supplied or
    overridden by the request body.
    """
    result = await verify_attestation(
        server_id, attestation_id, str(current_user["id"])
    )
    return ServerAttestationResponse(**result)


@router.patch(
    "/servers/{server_id}/attestations/{attestation_id}/reject",
    response_model=ServerAttestationResponse,
    dependencies=[Depends(require_manager_or_admin)],
)
async def reject_attestation_endpoint(
    server_id: str,
    attestation_id: str,
    payload: AttestationRejectRequest,
    current_user: dict = Depends(require_manager_or_admin),
) -> ServerAttestationResponse:
    """Reject a PENDING attestation. A reason is mandatory."""
    return ServerAttestationResponse(
        **await reject_attestation(
            server_id,
            attestation_id,
            payload.rejection_reason,
            actor_id=str(current_user["id"]),
        )
    )


@router.patch(
    "/servers/{server_id}/attestations/{attestation_id}/supersede",
    response_model=ServerAttestationResponse,
    dependencies=[Depends(require_manager_or_admin)],
)
async def supersede_attestation_endpoint(
    server_id: str,
    attestation_id: str,
    payload: AttestationSupersedeRequest,
    current_user: dict = Depends(require_manager_or_admin),
) -> ServerAttestationResponse:
    """Mark an attestation as replaced. The record is kept for history."""
    return ServerAttestationResponse(
        **await supersede_attestation(
            server_id,
            attestation_id,
            payload.superseded_by_id,
            actor_id=str(current_user["id"]),
        )
    )
