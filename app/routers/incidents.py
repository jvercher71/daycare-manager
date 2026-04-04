from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime, timezone
from app.database import get_db
from app.models import Incident as IncidentModel, Child as ChildModel
from app.schemas import IncidentCreate, Incident, PaginatedResponse
from app.auth import get_current_user
from app.models import User as UserModel

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.post("/", response_model=Incident, status_code=status.HTTP_201_CREATED)
async def create_incident(
    incident: IncidentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    child_result = await db.execute(
        select(ChildModel).where(
            ChildModel.id == incident.child_id,
            ChildModel.daycare_id == current_user.daycare_id,
            ChildModel.is_deleted == False
        )
    )
    if not child_result.scalars().first():
        raise HTTPException(status_code=404, detail="Child not found")

    db_incident = IncidentModel(
        **incident.model_dump(),
        date=datetime.now(timezone.utc),
        staff_name=current_user.username
    )
    db.add(db_incident)
    await db.commit()
    await db.refresh(db_incident)
    return db_incident


@router.get("/", response_model=PaginatedResponse[Incident])
async def list_incidents(
    child_id: Optional[int] = None,
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

    query = select(IncidentModel).where(IncidentModel.child_id.in_(child_ids))
    if child_id:
        query = query.where(IncidentModel.child_id == child_id)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar()
    result = await db.execute(
        query.order_by(IncidentModel.date.desc()).offset(skip).limit(limit)
    )
    items = result.scalars().all()
    return {"total": total, "skip": skip, "limit": limit, "items": items}
