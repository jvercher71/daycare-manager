from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from typing import Optional
from app.database import get_db
from app.models import Child as ChildModel, Parent as ParentModel, ClassRoom as ClassModel
from app.schemas import ChildCreate, Child, ChildWithParents, PaginatedResponse
from app.auth import get_current_user
from app.models import User as UserModel

router = APIRouter(prefix="/children", tags=["Children"])


@router.post("/", response_model=ChildWithParents, status_code=status.HTTP_201_CREATED)
async def create_child(
    child: ChildCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    if child.class_id:
        cls_result = await db.execute(
            select(ClassModel).where(
                ClassModel.id == child.class_id,
                ClassModel.daycare_id == current_user.daycare_id,
                ClassModel.is_deleted == False
            )
        )
        if not cls_result.scalars().first():
            raise HTTPException(status_code=404, detail="Class not found")

    parents = []
    if child.parent_ids:
        parents_result = await db.execute(
            select(ParentModel).where(
                ParentModel.id.in_(child.parent_ids),
                ParentModel.daycare_id == current_user.daycare_id,
                ParentModel.is_deleted == False
            )
        )
        parents = parents_result.scalars().all()
        if len(parents) != len(child.parent_ids):
            raise HTTPException(
                status_code=400,
                detail="One or more parent IDs are invalid or do not belong to your daycare"
            )

    db_child = ChildModel(
        first_name=child.first_name,
        last_name=child.last_name,
        date_of_birth=child.date_of_birth,
        allergies=child.allergies,
        medical_notes=child.medical_notes,
        photo_url=child.photo_url,
        class_id=child.class_id,
        daycare_id=current_user.daycare_id,
        created_by=current_user.id
    )
    db_child.parents = list(parents)
    db.add(db_child)
    await db.commit()
    await db.refresh(db_child)
    # Re-fetch with parents loaded eagerly
    result = await db.execute(
        select(ChildModel)
        .where(ChildModel.id == db_child.id)
        .options(joinedload(ChildModel.parents))
    )
    return result.unique().scalars().first()


@router.get("/", response_model=PaginatedResponse[ChildWithParents])
async def list_children(
    class_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    query = select(ChildModel).where(
        ChildModel.daycare_id == current_user.daycare_id,
        ChildModel.is_deleted == False
    )
    if class_id:
        query = query.where(ChildModel.class_id == class_id)
    if status_filter:
        query = query.where(ChildModel.status == status_filter)
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (ChildModel.first_name.ilike(search_pattern)) |
            (ChildModel.last_name.ilike(search_pattern))
        )
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar()
    result = await db.execute(
        query.options(joinedload(ChildModel.parents)).offset(skip).limit(limit)
    )
    items = result.unique().scalars().all()
    return {"total": total, "skip": skip, "limit": limit, "items": items}


@router.get("/{child_id}", response_model=ChildWithParents)
async def get_child(
    child_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    result = await db.execute(
        select(ChildModel)
        .where(
            ChildModel.id == child_id,
            ChildModel.daycare_id == current_user.daycare_id,
            ChildModel.is_deleted == False
        )
        .options(joinedload(ChildModel.parents))
    )
    child = result.unique().scalars().first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    return child


@router.put("/{child_id}", response_model=ChildWithParents)
async def update_child(
    child_id: int,
    child: ChildCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    result = await db.execute(
        select(ChildModel).where(
            ChildModel.id == child_id,
            ChildModel.daycare_id == current_user.daycare_id,
            ChildModel.is_deleted == False
        )
    )
    db_child = result.scalars().first()
    if not db_child:
        raise HTTPException(status_code=404, detail="Child not found")

    if child.class_id:
        cls_result = await db.execute(
            select(ClassModel).where(
                ClassModel.id == child.class_id,
                ClassModel.daycare_id == current_user.daycare_id,
                ClassModel.is_deleted == False
            )
        )
        if not cls_result.scalars().first():
            raise HTTPException(status_code=404, detail="Class not found")

    db_child.first_name = child.first_name
    db_child.last_name = child.last_name
    db_child.date_of_birth = child.date_of_birth
    db_child.allergies = child.allergies
    db_child.medical_notes = child.medical_notes
    db_child.photo_url = child.photo_url
    db_child.class_id = child.class_id

    if child.parent_ids is not None:
        if child.parent_ids:
            parents_result = await db.execute(
                select(ParentModel).where(
                    ParentModel.id.in_(child.parent_ids),
                    ParentModel.daycare_id == current_user.daycare_id,
                    ParentModel.is_deleted == False
                )
            )
            parents = parents_result.scalars().all()
            if len(parents) != len(child.parent_ids):
                raise HTTPException(
                    status_code=400,
                    detail="One or more parent IDs are invalid or do not belong to your daycare"
                )
            db_child.parents = list(parents)
        else:
            db_child.parents = []

    await db.commit()
    # Re-fetch with parents loaded
    result = await db.execute(
        select(ChildModel)
        .where(ChildModel.id == child_id)
        .options(joinedload(ChildModel.parents))
    )
    return result.unique().scalars().first()


@router.delete("/{child_id}")
async def delete_child(
    child_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    result = await db.execute(
        select(ChildModel).where(
            ChildModel.id == child_id,
            ChildModel.daycare_id == current_user.daycare_id,
            ChildModel.is_deleted == False
        )
    )
    db_child = result.scalars().first()
    if not db_child:
        raise HTTPException(status_code=404, detail="Child not found")
    db_child.is_deleted = True
    db_child.status = "inactive"
    await db.commit()
    return {"message": "Child deleted successfully"}
