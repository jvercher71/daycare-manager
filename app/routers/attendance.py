from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, timezone
from app.database import get_db
from app.models import (
    Attendance as AttendanceModel,
    Child as ChildModel,
)
from app.schemas import AttendanceCreate, AttendanceOut
from app.auth import get_current_user
from app.models import User as UserModel

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.post("/signin", response_model=AttendanceOut, status_code=status.HTTP_201_CREATED)
def sign_in(
    attendance: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    child = db.query(ChildModel).filter(
        ChildModel.id == attendance.child_id,
        ChildModel.daycare_id == current_user.daycare_id,
        ChildModel.is_deleted == False
    ).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    existing = db.query(AttendanceModel).filter(
        AttendanceModel.child_id == attendance.child_id,
        AttendanceModel.date >= today,
        AttendanceModel.sign_out_time == None
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Child is already signed in")
    db_attendance = AttendanceModel(
        child_id=attendance.child_id,
        sign_in_time=datetime.now(timezone.utc),
        signed_in_by=attendance.signed_in_by or current_user.username,
        notes=attendance.notes,
        date=today
    )
    db.add(db_attendance)
    db.commit()
    db.refresh(db_attendance)
    return db_attendance


@router.post("/signout/{attendance_id}", response_model=AttendanceOut)
def sign_out(
    attendance_id: int,
    signed_out_by: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    db_attendance = db.query(AttendanceModel).filter(AttendanceModel.id == attendance_id).first()
    if not db_attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    if db_attendance.sign_out_time:
        raise HTTPException(status_code=400, detail="Child is already signed out")
    db_attendance.sign_out_time = datetime.now(timezone.utc)
    db_attendance.signed_out_by = signed_out_by or current_user.username
    db.commit()
    db.refresh(db_attendance)
    return db_attendance


@router.get("/today", response_model=List[AttendanceOut])
def get_today_attendance(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    children = db.query(ChildModel).filter(
        ChildModel.daycare_id == current_user.daycare_id,
        ChildModel.is_deleted == False
    ).all()
    child_ids = [c.id for c in children]
    if not child_ids:
        return []
    return db.query(AttendanceModel).filter(
        AttendanceModel.child_id.in_(child_ids),
        AttendanceModel.date >= today
    ).order_by(AttendanceModel.sign_in_time.desc()).all()


@router.get("/", response_model=List[AttendanceOut])
def list_attendance(
    child_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    children = db.query(ChildModel).filter(
        ChildModel.daycare_id == current_user.daycare_id,
        ChildModel.is_deleted == False
    ).all()
    child_ids = [c.id for c in children]
    if not child_ids:
        return []
    query = db.query(AttendanceModel).filter(AttendanceModel.child_id.in_(child_ids))
    if child_id:
        query = query.filter(AttendanceModel.child_id == child_id)
    if date_from:
        query = query.filter(AttendanceModel.date >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(AttendanceModel.date <= datetime.fromisoformat(date_to))
    return query.order_by(AttendanceModel.sign_in_time.desc()).offset(skip).limit(limit).all()
