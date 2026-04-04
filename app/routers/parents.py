from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from typing import Optional
from app.database import get_db
from app.models import Parent as ParentModel
from app.schemas import ParentCreate, Parent, PaginatedResponse
from app.auth import get_current_user
from app.models import User as UserModel

router = APIRouter(prefix="/parents", tags=["Parents"])


@router.post("/", response_model=Parent, status_code=status.HTTP_201_CREATED)
async def create_parent(
    parent: ParentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    db_parent = ParentModel(
        **parent.model_dump(),
        daycare_id=current_user.daycare_id,
        created_by=current_user.id
    )
    db.add(db_parent)
    await db.commit()
    await db.refresh(db_parent)
    # Re-fetch with children eager-loaded
    result = await db.execute(
        select(ParentModel)
        .where(ParentModel.id == db_parent.id)
        .options(joinedload(ParentModel.children))
    )
    return result.unique().scalars().first()


@router.get("/", response_model=PaginatedResponse[Parent])
async def list_parents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    query = select(ParentModel).where(
        ParentModel.daycare_id == current_user.daycare_id,
        ParentModel.is_deleted == False
    )
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (ParentModel.first_name.ilike(search_pattern)) |
            (ParentModel.last_name.ilike(search_pattern)) |
            (ParentModel.email.ilike(search_pattern))
        )
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar()
    result = await db.execute(
        query.options(joinedload(ParentModel.children)).offset(skip).limit(limit)
    )
    items = result.unique().scalars().all()
    return {"total": total, "skip": skip, "limit": limit, "items": items}


@router.get("/{parent_id}", response_model=Parent)
async def get_parent(
    parent_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    result = await db.execute(
        select(ParentModel)
        .where(
            ParentModel.id == parent_id,
            ParentModel.daycare_id == current_user.daycare_id,
            ParentModel.is_deleted == False
        )
        .options(joinedload(ParentModel.children))
    )
    parent = result.unique().scalars().first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")
    return parent


@router.put("/{parent_id}", response_model=Parent)
async def update_parent(
    parent_id: int,
    parent: ParentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    result = await db.execute(
        select(ParentModel).where(
            ParentModel.id == parent_id,
            ParentModel.daycare_id == current_user.daycare_id,
            ParentModel.is_deleted == False
        )
    )
    db_parent = result.scalars().first()
    if not db_parent:
        raise HTTPException(status_code=404, detail="Parent not found")
    for key, value in parent.model_dump().items():
        setattr(db_parent, key, value)
    await db.commit()
    # Re-fetch with children eager-loaded
    result = await db.execute(
        select(ParentModel)
        .where(ParentModel.id == parent_id)
        .options(joinedload(ParentModel.children))
    )
    return result.unique().scalars().first()


@router.delete("/{parent_id}")
async def delete_parent(
    parent_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    result = await db.execute(
        select(ParentModel).where(
            ParentModel.id == parent_id,
            ParentModel.daycare_id == current_user.daycare_id,
            ParentModel.is_deleted == False
        )
    )
    db_parent = result.scalars().first()
    if not db_parent:
        raise HTTPException(status_code=404, detail="Parent not found")
    db_parent.is_deleted = True
    await db.commit()
    return {"message": "Parent deleted successfully"}
