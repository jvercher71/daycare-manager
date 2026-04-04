from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.database import get_db
from app.models import ClassRoom as ClassModel
from app.schemas import ClassCreate, ClassOut
from app.auth import get_current_user
from app.models import User as UserModel

router = APIRouter(prefix="/classes", tags=["Classes"])


@router.post("/", response_model=ClassOut, status_code=status.HTTP_201_CREATED)
def create_class(
    cls: ClassCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    db_class = ClassModel(
        **cls.model_dump(),
        daycare_id=current_user.daycare_id,
        created_by=current_user.id
    )
    db.add(db_class)
    db.commit()
    db.refresh(db_class)
    return db_class


@router.get("/", response_model=List[ClassOut])
def list_classes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    return db.query(ClassModel).filter(
        ClassModel.daycare_id == current_user.daycare_id,
        ClassModel.is_deleted == False
    ).offset(skip).limit(limit).all()


@router.get("/{class_id}", response_model=ClassOut)
def get_class(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    db_class = db.query(ClassModel).filter(
        ClassModel.id == class_id,
        ClassModel.daycare_id == current_user.daycare_id,
        ClassModel.is_deleted == False
    ).first()
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")
    return db_class


@router.put("/{class_id}", response_model=ClassOut)
def update_class(
    class_id: int,
    cls: ClassCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    db_class = db.query(ClassModel).filter(
        ClassModel.id == class_id,
        ClassModel.daycare_id == current_user.daycare_id,
        ClassModel.is_deleted == False
    ).first()
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")
    for key, value in cls.model_dump().items():
        setattr(db_class, key, value)
    db.commit()
    db.refresh(db_class)
    return db_class


@router.delete("/{class_id}")
def delete_class(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    db_class = db.query(ClassModel).filter(
        ClassModel.id == class_id,
        ClassModel.daycare_id == current_user.daycare_id,
        ClassModel.is_deleted == False
    ).first()
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")
    db_class.is_deleted = True
    db.commit()
    return {"message": "Class deleted successfully"}
