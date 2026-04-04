from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, timezone
from app.database import get_db
from app.models import (
    Child as ChildModel,
    Parent as ParentModel,
)
from app.schemas import ChildCreate, Child, ChildWithParents
from app.auth import get_current_user
from app.models import User as UserModel

router = APIRouter(prefix="/children", tags=["Children"])


@router.post("/", response_model=ChildWithParents, status_code=status.HTTP_201_CREATED)
def create_child(
    child: ChildCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    if child.class_id:
        from app.models import ClassRoom as ClassModel
        cls = db.query(ClassModel).filter(
            ClassModel.id == child.class_id,
            ClassModel.daycare_id == current_user.daycare_id,
            ClassModel.is_deleted == False
        ).first()
        if not cls:
            raise HTTPException(status_code=404, detail="Class not found")
    if child.parent_ids:
        parents = db.query(ParentModel).filter(
            ParentModel.id.in_(child.parent_ids),
            ParentModel.daycare_id == current_user.daycare_id,
            ParentModel.is_deleted == False
        ).all()
        if len(parents) != len(child.parent_ids):
            raise HTTPException(
                status_code=400,
                detail="One or more parent IDs are invalid or do not belong to your daycare"
            )
    else:
        parents = []
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
    db_child.parents = parents
    db.add(db_child)
    db.commit()
    db.refresh(db_child)
    return db_child


@router.get("/", response_model=List[ChildWithParents])
def list_children(
    class_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    query = db.query(ChildModel).filter(
        ChildModel.daycare_id == current_user.daycare_id,
        ChildModel.is_deleted == False
    )
    if class_id:
        query = query.filter(ChildModel.class_id == class_id)
    if status_filter:
        query = query.filter(ChildModel.status == status_filter)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (ChildModel.first_name.ilike(search_pattern)) |
            (ChildModel.last_name.ilike(search_pattern))
        )
    query = query.options(joinedload(ChildModel.parents)).offset(skip).limit(limit)
    return query.all()


@router.get("/{child_id}", response_model=ChildWithParents)
def get_child(
    child_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    child = db.query(ChildModel).filter(
        ChildModel.id == child_id,
        ChildModel.daycare_id == current_user.daycare_id,
        ChildModel.is_deleted == False
    ).options(joinedload(ChildModel.parents)).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    return child


@router.put("/{child_id}", response_model=ChildWithParents)
def update_child(
    child_id: int,
    child: ChildCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    db_child = db.query(ChildModel).filter(
        ChildModel.id == child_id,
        ChildModel.daycare_id == current_user.daycare_id,
        ChildModel.is_deleted == False
    ).first()
    if not db_child:
        raise HTTPException(status_code=404, detail="Child not found")
    if child.class_id:
        from app.models import ClassRoom as ClassModel
        cls = db.query(ClassModel).filter(
            ClassModel.id == child.class_id,
            ClassModel.daycare_id == current_user.daycare_id,
            ClassModel.is_deleted == False
        ).first()
        if not cls:
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
            parents = db.query(ParentModel).filter(
                ParentModel.id.in_(child.parent_ids),
                ParentModel.daycare_id == current_user.daycare_id,
                ParentModel.is_deleted == False
            ).all()
            if len(parents) != len(child.parent_ids):
                raise HTTPException(
                    status_code=400,
                    detail="One or more parent IDs are invalid or do not belong to your daycare"
                )
            db_child.parents = parents
        else:
            db_child.parents = []
    db.commit()
    db.refresh(db_child)
    return db_child


@router.delete("/{child_id}")
def delete_child(
    child_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    db_child = db.query(ChildModel).filter(
        ChildModel.id == child_id,
        ChildModel.daycare_id == current_user.daycare_id,
        ChildModel.is_deleted == False
    ).first()
    if not db_child:
        raise HTTPException(status_code=404, detail="Child not found")
    db_child.is_deleted = True
    db_child.status = "inactive"
    db.commit()
    return {"message": "Child deleted successfully"}
