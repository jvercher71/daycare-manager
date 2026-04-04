from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from app.database import get_db
from app.models import (
    Incident as IncidentModel,
    Child as ChildModel,
)
from app.schemas import IncidentCreate, Incident
from app.auth import get_current_user
from app.models import User as UserModel

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.post("/", response_model=Incident, status_code=status.HTTP_201_CREATED)
def create_incident(
    incident: IncidentCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    child = db.query(ChildModel).filter(
        ChildModel.id == incident.child_id,
        ChildModel.daycare_id == current_user.daycare_id,
        ChildModel.is_deleted == False
    ).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    db_incident = IncidentModel(
        **incident.model_dump(),
        date=datetime.now(timezone.utc),
        staff_name=current_user.username
    )
    db.add(db_incident)
    db.commit()
    db.refresh(db_incident)
    return db_incident


@router.get("/", response_model=List[Incident])
def list_incidents(
    child_id: Optional[int] = None,
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
    query = db.query(IncidentModel).filter(IncidentModel.child_id.in_(child_ids))
    if child_id:
        query = query.filter(IncidentModel.child_id == child_id)
    return query.order_by(IncidentModel.date.desc()).offset(skip).limit(limit).all()
