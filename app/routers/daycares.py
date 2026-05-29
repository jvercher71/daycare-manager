from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from typing import Optional
from app.database import get_db
from app.models import Daycare as DaycareModel
from app.schemas import DaycareCreate, Daycare, PaginatedResponse
from app.auth import get_current_user, require_role
from app.models import User as UserModel

router = APIRouter(prefix="/daycares", tags=["Daycares"])


@router.post("/", response_model=Daycare, status_code=status.HTTP_201_CREATED)
async def create_daycare(
    daycare: DaycareCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(require_role("admin"))
):
    db_daycare = DaycareModel(**daycare.model_dump())
    db.add(db_daycare)
    await db.commit()
    await db.refresh(db_daycare)
    # Associate the creating user with this daycare (single-site model) so that
    # daycare-scoped resources (children, invoices, etc.) work for them.
    if current_user.daycare_id is None:
        current_user.daycare_id = db_daycare.id
        db.add(current_user)
        await db.commit()
    return db_daycare


@router.get("/", response_model=PaginatedResponse[Daycare])
async def list_daycares(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    # Scope to the current user's daycare so tenants don't see each other's data.
    if current_user.daycare_id is None:
        return {"total": 0, "skip": skip, "limit": limit, "items": []}
    query = select(DaycareModel).where(DaycareModel.id == current_user.daycare_id)
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar()
    result = await db.execute(query.offset(skip).limit(limit))
    items = result.scalars().all()
    return {"total": total, "skip": skip, "limit": limit, "items": items}


@router.get("/{daycare_id}", response_model=Daycare)
async def get_daycare(
    daycare_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    result = await db.execute(select(DaycareModel).where(DaycareModel.id == daycare_id))
    db_daycare = result.scalars().first()
    if not db_daycare:
        raise HTTPException(status_code=404, detail="Daycare not found")
    return db_daycare


@router.put("/{daycare_id}", response_model=Daycare)
async def update_daycare(
    daycare_id: int,
    daycare: DaycareCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(require_role("admin"))
):
    result = await db.execute(select(DaycareModel).where(DaycareModel.id == daycare_id))
    db_daycare = result.scalars().first()
    if not db_daycare:
        raise HTTPException(status_code=404, detail="Daycare not found")
    for key, value in daycare.model_dump().items():
        setattr(db_daycare, key, value)
    await db.commit()
    await db.refresh(db_daycare)
    return db_daycare
