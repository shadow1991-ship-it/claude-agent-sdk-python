import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)
from app.api.deps import get_current_user
from app.main import limiter
from app.models.user import User, APIKey
from app.models.organization import Organization
from app.schemas.auth import (
    UserRegister, UserLogin, TokenResponse, RefreshRequest,
    UserOut, APIKeyCreate, APIKeyOut,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(name: str) -> str:
    return _SLUG_RE.sub("-", name.lower()).strip("-")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_REGISTER)
async def register(request: Request, payload: UserRegister, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    org = None
    if payload.organization_name:
        slug = _slugify(payload.organization_name)
        org = Organization(name=payload.organization_name, slug=f"{slug}-{secrets.token_hex(4)}")
        db.add(org)
        await db.flush()

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        organization_id=org.id if org else None,
    )
    db.add(user)
    await db.flush()
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.RATE_LOGIN)
async def login(request: Request, payload: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
async def refresh(request: Request, payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    data = decode_token(payload.refresh_token)
    if not data or data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await db.execute(select(User).where(User.id == uuid.UUID(data["sub"])))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/api-keys", response_model=APIKeyOut)
async def create_api_key(
    payload: APIKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    raw_key = f"sg_{secrets.token_urlsafe(32)}"
    expires_at = None
    if payload.expires_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=payload.expires_days)

    api_key = APIKey(
        user_id=current_user.id,
        name=payload.name,
        key_hash=hash_password(raw_key),
        expires_at=expires_at,
    )
    db.add(api_key)
    await db.flush()

    return APIKeyOut(
        id=str(api_key.id),
        name=api_key.name,
        key=raw_key,
        created_at=api_key.created_at.isoformat(),
    )


@router.get("/api-keys", response_model=list[APIKeyOut])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(APIKey)
        .where(APIKey.user_id == current_user.id, APIKey.is_active == True)
        .order_by(APIKey.created_at.desc())
    )
    return [
        APIKeyOut(
            id=str(k.id),
            name=k.name,
            key="sg_***hidden***",
            created_at=k.created_at.isoformat(),
        )
        for k in result.scalars().all()
    ]


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        uid = uuid.UUID(key_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid key ID")

    result = await db.execute(
        select(APIKey).where(APIKey.id == uid, APIKey.user_id == current_user.id)
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    key.is_active = False
    await db.flush()
