import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.config import settings
from app.routers.health import router as health_router
from app.routers.auth import router as auth_router
from app.routers.events import router as events_router
from app.routers.transport import router as transport_router
from app.routers.urgent import router as urgent_router
from app.routers.gamification import router as gamification_router
from app.routers.servers import router as servers_router
from app.routers.availability import router as availability_router
from app.routers.dashboard import router as dashboard_router

logger = logging.getLogger(__name__)


class UnhandledExceptionResponse(BaseModel):
    detail: str


app = FastAPI(title=settings.PROJECT_NAME)

settings.validate_production()

cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Une erreur interne est survenue."},
    )

app.include_router(health_router, prefix=settings.API_V1_STR, tags=["health"])
app.include_router(auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(events_router, prefix=settings.API_V1_STR, tags=["events"])
app.include_router(transport_router, prefix=settings.API_V1_STR, tags=["transport"])
app.include_router(urgent_router, prefix=settings.API_V1_STR, tags=["urgent"])
app.include_router(gamification_router, prefix=settings.API_V1_STR, tags=["gamification"])
app.include_router(servers_router, prefix=settings.API_V1_STR, tags=["servers"])
app.include_router(availability_router, prefix=settings.API_V1_STR, tags=["availability"])
app.include_router(dashboard_router, prefix=settings.API_V1_STR, tags=["dashboard"])
