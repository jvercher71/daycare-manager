from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from app.database import get_db
from app.models import ClassRoom as ClassModel
from app.schemas import ClassCreate, ClassOut, PaginatedResponse
from app.auth import get_current_user
from app.models import User as UserModel

router = APIRouter(prefix="/classes", tags=["Classes"])


@router.post("/", response_model=ClassOut, status_code=status.HTTP_201_CREATED)
async def create_class(
    cls: ClassCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    db_class = ClassModel(
        **cls.model_dump(),
        daycare_id=current_user.daycare_id,
        created_by=current_user.id
    )
    db.add(db_class)
    await db.commit()
    await db.refresh(db_class)
    return db_class


@router.get("/", response_model=PaginatedResponse[ClassOut])
async def list_classes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    query = select(ClassModel).where(
        ClassModel.daycare_id == current_user.daycare_id,
        ClassModel.is_deleted == False
    )
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar()
    result = await db.execute(query.offset(skip).limit(limit))
    items = result.scalars().all()
    return {"total": total, "skip": skip, "limit": limit, "items": items}


@router.get("/{class_id}", response_model=ClassOut)
async def get_class(
    class_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    result = await db.execute(
        select(ClassModel).where(
            ClassModel.id == class_id,
            ClassModel.daycare_id == current_user.daycare_id,
            ClassModel.is_deleted == False
        )
    )
    db_class = result.scalars().first()
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")
    return db_class


@router.put("/{class_id}", response_model=ClassOut)
async def update_class(
    class_id: int,
    cls: ClassCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    result = await db.execute(
        select(ClassModel).where(
            ClassModel.id == class_id,
            ClassModel.daycare_id == current_user.daycare_id,
            ClassModel.is_deleted == False
        )
    )
    db_class = result.scalars().first()
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")
    for key, value in cls.model_dump().items():
        setattr(db_class, key, value)
    await db.commit()
    await db.refresh(db_class)
    return db_class


@router.delete("/{class_id}")
async def delete_class(
    class_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    result = await db.execute(
        select(ClassModel).where(
            ClassModel.id == class_id,
            ClassModel.daycare_id == current_user.daycare_id,
            ClassModel.is_deleted == False
        )
    )
    db_class = result.scalars().first()
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")
    db_class.is_deleted = True
    await db.commit()
    return {"message": "Class deleted successfully"}
