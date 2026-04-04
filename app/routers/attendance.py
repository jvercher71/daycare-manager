from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime, timezone
from app.database import get_db
from app.models import Attendance as AttendanceModel, Child as ChildModel
from app.schemas import AttendanceCreate, AttendanceOut, PaginatedResponse
from app.auth import get_current_user
from app.models import User as UserModel

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.post("/signin", response_model=AttendanceOut, status_code=status.HTTP_201_CREATED)
async def sign_in(
    attendance: AttendanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    child_result = await db.execute(
        select(ChildModel).where(
            ChildModel.id == attendance.child_id,
            ChildModel.daycare_id == current_user.daycare_id,
            ChildModel.is_deleted == False
        )
    )
    if not child_result.scalars().first():
        raise HTTPException(status_code=404, detail="Child not found")

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    existing_result = await db.execute(
        select(AttendanceModel).where(
            AttendanceModel.child_id == attendance.child_id,
            AttendanceModel.date >= today,
            AttendanceModel.sign_out_time == None
        )
    )
    if existing_result.scalars().first():
        raise HTTPException(status_code=400, detail="Child is already signed in")

    db_attendance = AttendanceModel(
        child_id=attendance.child_id,
        sign_in_time=datetime.now(timezone.utc),
        signed_in_by=attendance.signed_in_by or current_user.username,
        notes=attendance.notes,
        date=today
    )
    db.add(db_attendance)
    await db.commit()
    await db.refresh(db_attendance)
    return db_attendance


@router.post("/signout/{attendance_id}", response_model=AttendanceOut)
async def sign_out(
    attendance_id: int,
    signed_out_by: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    result = await db.execute(
        select(AttendanceModel).where(AttendanceModel.id == attendance_id)
    )
    db_attendance = result.scalars().first()
    if not db_attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    if db_attendance.sign_out_time:
        raise HTTPException(status_code=400, detail="Child is already signed out")
    db_attendance.sign_out_time = datetime.now(timezone.utc)
    db_attendance.signed_out_by = signed_out_by or current_user.username
    await db.commit()
    await db.refresh(db_attendance)
    return db_attendance


@router.get("/today", response_model=list[AttendanceOut])
async def get_today_attendance(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    children_result = await db.execute(
        select(ChildModel.id).where(
            ChildModel.daycare_id == current_user.daycare_id,
            ChildModel.is_deleted == False
        )
    )
    child_ids = children_result.scalars().all()
    if not child_ids:
        return []
    result = await db.execute(
        select(AttendanceModel)
        .where(
            AttendanceModel.child_id.in_(child_ids),
            AttendanceModel.date >= today
        )
        .order_by(AttendanceModel.sign_in_time.desc())
    )
    return result.scalars().all()


@router.get("/", response_model=PaginatedResponse[AttendanceOut])
async def list_attendance(
    child_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    children_result = await db.execute(
        select(ChildModel.id).where(
            ChildModel.daycare_id == current_user.daycare_id,
            ChildModel.is_deleted == False
        )
    )
    child_ids = children_result.scalars().all()
    if not child_ids:
        return {"total": 0, "skip": skip, "limit": limit, "items": []}

    query = select(AttendanceModel).where(AttendanceModel.child_id.in_(child_ids))
    if child_id:
        query = query.where(AttendanceModel.child_id == child_id)
    if date_from:
        query = query.where(AttendanceModel.date >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.where(AttendanceModel.date <= datetime.fromisoformat(date_to))

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar()
    result = await db.execute(
        query.order_by(AttendanceModel.sign_in_time.desc()).offset(skip).limit(limit)
    )
    items = result.scalars().all()
    return {"total": total, "skip": skip, "limit": limit, "items": items}
