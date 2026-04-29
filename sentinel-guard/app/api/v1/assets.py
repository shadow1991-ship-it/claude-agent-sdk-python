import secrets
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.asset import Asset, VerificationStatus
from app.models.user import User
from app.schemas.asset import AssetCreate, AssetOut, VerificationChallenge, VerifyAssetRequest
from app.services.verification.manager import VerificationManager

router = APIRouter(prefix="/assets", tags=["Assets"])
_verifier = VerificationManager()


@router.post("", response_model=AssetOut, status_code=status.HTTP_201_CREATED)
async def register_asset(
    payload: AssetCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user.organization_id:
        raise HTTPException(status_code=400, detail="User must belong to an organization")

    token = _verifier.generate_token()
    asset = Asset(
        organization_id=user.organization_id,
        owner_id=user.id,
        value=payload.value,
        asset_type=payload.asset_type,
        description=payload.description,
        verification_method=payload.verification_method,
        verification_token=token,
    )
    db.add(asset)
    await db.flush()
    return asset


@router.get("/{asset_id}/challenge", response_model=VerificationChallenge)
async def get_challenge(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    asset = await _get_owned_asset(asset_id, user, db)
    challenge = _verifier.get_challenge(asset)
    return VerificationChallenge(
        asset_id=str(asset.id),
        method=asset.verification_method,
        token=asset.verification_token or "",
        **challenge,
    )


@router.post("/{asset_id}/verify", response_model=AssetOut)
async def verify_asset(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    asset = await _get_owned_asset(asset_id, user, db)

    if asset.verification_status == VerificationStatus.VERIFIED:
        return asset

    success = await _verifier.verify(asset, db)
    if not success:
        raise HTTPException(
            status_code=422,
            detail="Verification failed. Ensure the DNS record or file is in place and retry.",
        )
    return asset


@router.get("", response_model=list[AssetOut])
async def list_assets(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Asset)
        .where(Asset.organization_id == user.organization_id, Asset.is_active == True)
        .order_by(Asset.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    asset = await _get_owned_asset(asset_id, user, db)
    asset.is_active = False
    await db.flush()


async def _get_owned_asset(asset_id: str, user: User, db: AsyncSession) -> Asset:
    try:
        uid = uuid.UUID(asset_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid asset ID")

    result = await db.execute(
        select(Asset).where(
            Asset.id == uid,
            Asset.organization_id == user.organization_id,
            Asset.is_active == True,
        )
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset
