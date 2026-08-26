from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer

from app.models.auth import LoginResponse, UserLoginRequest, UserResponse
from app.models.health import PingResponse
from app.services.auth_service import authenticate_user, create_access_token_for_user

router = APIRouter()


@router.get("/ping", response_model=PingResponse)
async def ping() -> PingResponse:
    return PingResponse(message="pong")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


@router.post("/login", response_model=LoginResponse)
async def login(payload: UserLoginRequest):
    user = await authenticate_user(payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Email ou mot de passe incorrect.",
        )

    access_token = create_access_token_for_user(user)
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=str(user["id"]),
            email=user["email"],
            role=user["role"],
            is_active=user["is_active"],
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(token: str = Depends(oauth2_scheme)):
    from app.services.auth_service import get_current_user
    user = await get_current_user(token)
    return UserResponse(
        id=str(user["id"]),
        email=user["email"],
        role=user["role"],
        is_active=user["is_active"],
    )
