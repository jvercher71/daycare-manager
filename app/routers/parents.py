from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.database import get_db
from app.models import Parent as ParentModel
from app.schemas import ParentCreate, Parent
from app.auth import get_current_user
from app.models import User as UserModel

router = APIRouter(prefix="/parents", tags=["Parents"])


@router.post("/", response_model=Parent, status_code=status.HTTP_201_CREATED)
def create_parent(
    parent: ParentCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    db_parent = ParentModel(
        **parent.model_dump(),
        daycare_id=current_user.daycare_id,
        created_by=current_user.id
    )
    db.add(db_parent)
    db.commit()
    db.refresh(db_parent)
    return db_parent


@router.get("/", response_model=List[Parent])
def list_parents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    query = db.query(ParentModel).filter(
        ParentModel.daycare_id == current_user.daycare_id,
        ParentModel.is_deleted == False
    )
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (ParentModel.first_name.ilike(search_pattern)) |
            (ParentModel.last_name.ilike(search_pattern)) |
            (ParentModel.email.ilike(search_pattern))
        )
    query = query.options(joinedload(ParentModel.children))
    return query.offset(skip).limit(limit).all()


@router.get("/{parent_id}", response_model=Parent)
def get_parent(
    parent_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    parent = db.query(ParentModel).filter(
        ParentModel.id == parent_id,
        ParentModel.daycare_id == current_user.daycare_id,
        ParentModel.is_deleted == False
    ).options(joinedload(ParentModel.children)).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")
    return parent


@router.put("/{parent_id}", response_model=Parent)
def update_parent(
    parent_id: int,
    parent: ParentCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    db_parent = db.query(ParentModel).filter(
        ParentModel.id == parent_id,
        ParentModel.daycare_id == current_user.daycare_id,
        ParentModel.is_deleted == False
    ).first()
    if not db_parent:
        raise HTTPException(status_code=404, detail="Parent not found")
    for key, value in parent.model_dump().items():
        setattr(db_parent, key, value)
    db.commit()
    db.refresh(db_parent)
    return db_parent


@router.delete("/{parent_id}")
def delete_parent(
    parent_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    db_parent = db.query(ParentModel).filter(
        ParentModel.id == parent_id,
        ParentModel.daycare_id == current_user.daycare_id,
        ParentModel.is_deleted == False
    ).first()
    if not db_parent:
        raise HTTPException(status_code=404, detail="Parent not found")
    db_parent.is_deleted = True
    db.commit()
    return {"message": "Parent deleted successfully"}
