from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime, timezone
from app.database import get_db
from app.models import DailyReport as DailyReportModel, Child as ChildModel
from app.schemas import DailyReportCreate, DailyReport, PaginatedResponse
from app.auth import get_current_user
from app.models import User as UserModel

router = APIRouter(prefix="/daily-reports", tags=["Daily Reports"])


@router.post("/", response_model=DailyReport, status_code=status.HTTP_201_CREATED)
async def create_daily_report(
    report: DailyReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    child_result = await db.execute(
        select(ChildModel).where(
            ChildModel.id == report.child_id,
            ChildModel.daycare_id == current_user.daycare_id,
            ChildModel.is_deleted == False
        )
    )
    if not child_result.scalars().first():
        raise HTTPException(status_code=404, detail="Child not found")

    db_report = DailyReportModel(
        **report.model_dump(),
        date=datetime.now(timezone.utc),
        staff_name=current_user.username
    )
    db.add(db_report)
    await db.commit()
    await db.refresh(db_report)
    return db_report


@router.get("/", response_model=PaginatedResponse[DailyReport])
async def list_daily_reports(
    child_id: Optional[int] = None,
    date: Optional[str] = None,
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

    query = select(DailyReportModel).where(DailyReportModel.child_id.in_(child_ids))
    if child_id:
        query = query.where(DailyReportModel.child_id == child_id)
    if date:
        query = query.where(DailyReportModel.date >= datetime.fromisoformat(date))

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar()
    result = await db.execute(
        query.order_by(DailyReportModel.date.desc()).offset(skip).limit(limit)
    )
    items = result.scalars().all()
    return {"total": total, "skip": skip, "limit": limit, "items": items}
