from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Daycare as DaycareModel
from app.schemas import DaycareCreate, Daycare
from app.auth import get_current_user, require_role
from app.models import User as UserModel

router = APIRouter(prefix="/daycares", tags=["Daycares"])


@router.post("/", response_model=Daycare, status_code=status.HTTP_201_CREATED)
def create_daycare(
    daycare: DaycareCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_role("admin"))
):
    db_daycare = DaycareModel(**daycare.model_dump())
    db.add(db_daycare)
    db.commit()
    db.refresh(db_daycare)
    return db_daycare


@router.get("/", response_model=List[Daycare])
def list_daycares(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    return db.query(DaycareModel).all()


@router.get("/{daycare_id}", response_model=Daycare)
def get_daycare(
    daycare_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    db_daycare = db.query(DaycareModel).filter(DaycareModel.id == daycare_id).first()
    if not db_daycare:
        raise HTTPException(status_code=404, detail="Daycare not found")
    return db_daycare


@router.put("/{daycare_id}", response_model=Daycare)
def update_daycare(
    daycare_id: int,
    daycare: DaycareCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_role("admin"))
):
    db_daycare = db.query(DaycareModel).filter(DaycareModel.id == daycare_id).first()
    if not db_daycare:
        raise HTTPException(status_code=404, detail="Daycare not found")
    for key, value in daycare.model_dump().items():
        setattr(db_daycare, key, value)
    db.commit()
    db.refresh(db_daycare)
    return db_daycare
