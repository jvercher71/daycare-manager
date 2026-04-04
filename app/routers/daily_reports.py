from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from app.database import get_db
from app.models import (
    DailyReport as DailyReportModel,
    Child as ChildModel,
)
from app.schemas import DailyReportCreate, DailyReport
from app.auth import get_current_user
from app.models import User as UserModel

router = APIRouter(prefix="/daily-reports", tags=["Daily Reports"])


@router.post("/", response_model=DailyReport, status_code=status.HTTP_201_CREATED)
def create_daily_report(
    report: DailyReportCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    child = db.query(ChildModel).filter(
        ChildModel.id == report.child_id,
        ChildModel.daycare_id == current_user.daycare_id,
        ChildModel.is_deleted == False
    ).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    db_report = DailyReportModel(
        **report.model_dump(),
        date=datetime.now(timezone.utc),
        staff_name=current_user.username
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report


@router.get("/", response_model=List[DailyReport])
def list_daily_reports(
    child_id: Optional[int] = None,
    date: Optional[str] = None,
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
    query = db.query(DailyReportModel).filter(DailyReportModel.child_id.in_(child_ids))
    if child_id:
        query = query.filter(DailyReportModel.child_id == child_id)
    if date:
        query = query.filter(DailyReportModel.date >= datetime.fromisoformat(date))
    return query.order_by(DailyReportModel.date.desc()).offset(skip).limit(limit).all()
