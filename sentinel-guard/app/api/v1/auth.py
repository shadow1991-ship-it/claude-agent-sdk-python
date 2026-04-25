import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.models.user import User, APIKey
from app.models.organization import Organization
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, RefreshRequest, UserOut, APIKeyCreate, APIKeyOut

router = APIRouter(prefix="/auth", tags=["Authentication"])

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(name: str) -> str:
    return _SLUG_RE.sub("-", name.lower()).strip("-")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
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
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
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
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
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


@router.post("/api-keys", response_model=APIKeyOut)
async def create_api_key(
    payload: APIKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(__import__("app.api.deps", fromlist=["get_current_user"]).get_current_user),
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
