from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from typing import List, Optional

from database import engine, get_db, Base, init_db
from models import (
    User as UserModel, Daycare as DaycareModel, Parent as ParentModel,
    Child as ChildModel, ClassRoom as ClassModel, Attendance as AttendanceModel,
    DailyReport as DailyReportModel, Incident as IncidentModel, parent_child
)
from schemas import (
    UserCreate, User, DaycareCreate, Daycare, ParentCreate, Parent,
    ChildCreate, Child, ChildWithParents, ClassCreate, ClassOut,
    AttendanceCreate, AttendanceOut, DailyReportCreate, DailyReport,
    IncidentCreate, Incident, Token
)
from auth import (
    authenticate_user, get_password_hash, create_access_token,
    get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
)

app = FastAPI(title="Daycare Manager API")

init_db()


@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")


app.mount("/static", StaticFiles(directory="static"), name="static")


# Auth endpoints
@app.post("/register", response_model=User)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(UserModel).filter(UserModel.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    db_user = UserModel(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/me", response_model=User)
def get_me(current_user: UserModel = Depends(get_current_user)):
    return current_user


# Daycare endpoints
@app.post("/daycares", response_model=Daycare)
def create_daycare(daycare: DaycareCreate, db: Session = Depends(get_db)):
    db_daycare = DaycareModel(**daycare.model_dump())
    db.add(db_daycare)
    db.commit()
    db.refresh(db_daycare)
    return db_daycare


@app.get("/daycares", response_model=List[Daycare])
def list_daycares(db: Session = Depends(get_db)):
    return db.query(DaycareModel).all()


@app.put("/daycares/{daycare_id}", response_model=Daycare)
def update_daycare(daycare_id: int, daycare: DaycareCreate, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    db_daycare = db.query(DaycareModel).filter(DaycareModel.id == daycare_id).first()
    if not db_daycare:
        raise HTTPException(status_code=404, detail="Daycare not found")
    for key, value in daycare.model_dump().items():
        setattr(db_daycare, key, value)
    db.commit()
    db.refresh(db_daycare)
    return db_daycare


# Parent endpoints
@app.post("/parents", response_model=Parent)
def create_parent(parent: ParentCreate, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    db_parent = ParentModel(**parent.model_dump(), daycare_id=current_user.daycare_id)
    db.add(db_parent)
    db.commit()
    db.refresh(db_parent)
    return db_parent


@app.get("/parents", response_model=List[Parent])
def list_parents(db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    return db.query(ParentModel).filter(ParentModel.daycare_id == current_user.daycare_id).all()


@app.get("/parents/{parent_id}", response_model=Parent)
def get_parent(parent_id: int, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    parent = db.query(ParentModel).filter(ParentModel.id == parent_id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")
    return parent


@app.put("/parents/{parent_id}", response_model=Parent)
def update_parent(parent_id: int, parent: ParentCreate, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    db_parent = db.query(ParentModel).filter(ParentModel.id == parent_id).first()
    if not db_parent:
        raise HTTPException(status_code=404, detail="Parent not found")
    for key, value in parent.model_dump().items():
        setattr(db_parent, key, value)
    db.commit()
    db.refresh(db_parent)
    return db_parent


@app.delete("/parents/{parent_id}")
def delete_parent(parent_id: int, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    db_parent = db.query(ParentModel).filter(ParentModel.id == parent_id).first()
    if not db_parent:
        raise HTTPException(status_code=404, detail="Parent not found")
    db.delete(db_parent)
    db.commit()
    return {"message": "Parent deleted"}


# Child endpoints
@app.post("/children", response_model=ChildWithParents)
def create_child(child: ChildCreate, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    db_child = ChildModel(
        first_name=child.first_name,
        last_name=child.last_name,
        date_of_birth=child.date_of_birth,
        allergies=child.allergies,
        medical_notes=child.medical_notes,
        photo_url=child.photo_url,
        class_id=child.class_id,
        daycare_id=current_user.daycare_id
    )
    if child.parent_ids:
        parents = db.query(ParentModel).filter(ParentModel.id.in_(child.parent_ids)).all()
        db_child.parents = parents
    db.add(db_child)
    db.commit()
    db.refresh(db_child)
    return db_child


@app.get("/children", response_model=List[ChildWithParents])
def list_children(class_id: Optional[int] = None, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    query = db.query(ChildModel).filter(ChildModel.daycare_id == current_user.daycare_id)
    if class_id:
        query = query.filter(ChildModel.class_id == class_id)
    return query.all()


@app.get("/children/{child_id}", response_model=ChildWithParents)
def get_child(child_id: int, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    child = db.query(ChildModel).filter(ChildModel.id == child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    return child


@app.put("/children/{child_id}", response_model=ChildWithParents)
def update_child(child_id: int, child: ChildCreate, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    db_child = db.query(ChildModel).filter(ChildModel.id == child_id).first()
    if not db_child:
        raise HTTPException(status_code=404, detail="Child not found")
    db_child.first_name = child.first_name
    db_child.last_name = child.last_name
    db_child.date_of_birth = child.date_of_birth
    db_child.allergies = child.allergies
    db_child.medical_notes = child.medical_notes
    db_child.photo_url = child.photo_url
    db_child.class_id = child.class_id
    if child.parent_ids:
        parents = db.query(ParentModel).filter(ParentModel.id.in_(child.parent_ids)).all()
        db_child.parents = parents
    db.commit()
    db.refresh(db_child)
    return db_child


@app.delete("/children/{child_id}")
def delete_child(child_id: int, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    db_child = db.query(ChildModel).filter(ChildModel.id == child_id).first()
    if not db_child:
        raise HTTPException(status_code=404, detail="Child not found")
    db.delete(db_child)
    db.commit()
    return {"message": "Child deleted"}


# Class endpoints
@app.post("/classes", response_model=ClassOut)
def create_class(cls: ClassCreate, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    db_class = ClassModel(**cls.model_dump(), daycare_id=current_user.daycare_id)
    db.add(db_class)
    db.commit()
    db.refresh(db_class)
    return db_class


@app.get("/classes", response_model=List[ClassOut])
def list_classes(db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    return db.query(ClassModel).filter(ClassModel.daycare_id == current_user.daycare_id).all()


@app.put("/classes/{class_id}", response_model=ClassOut)
def update_class(class_id: int, cls: ClassCreate, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    db_class = db.query(ClassModel).filter(ClassModel.id == class_id).first()
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")
    for key, value in cls.model_dump().items():
        setattr(db_class, key, value)
    db.commit()
    db.refresh(db_class)
    return db_class


@app.delete("/classes/{class_id}")
def delete_class(class_id: int, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    db_class = db.query(ClassModel).filter(ClassModel.id == class_id).first()
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")
    db.delete(db_class)
    db.commit()
    return {"message": "Class deleted"}


# Attendance endpoints
@app.post("/attendance/signin", response_model=AttendanceOut)
def sign_in(attendance: AttendanceCreate, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    existing = db.query(AttendanceModel).filter(
        AttendanceModel.child_id == attendance.child_id,
        AttendanceModel.date >= today,
        AttendanceModel.sign_out_time == None
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Child is already signed in")
    db_attendance = AttendanceModel(
        child_id=attendance.child_id,
        sign_in_time=datetime.utcnow(),
        signed_in_by=attendance.signed_in_by or current_user.username,
        notes=attendance.notes,
        date=today
    )
    db.add(db_attendance)
    db.commit()
    db.refresh(db_attendance)
    return db_attendance


@app.post("/attendance/signout/{attendance_id}", response_model=AttendanceOut)
def sign_out(attendance_id: int, signed_out_by: Optional[str] = None, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    db_attendance = db.query(AttendanceModel).filter(AttendanceModel.id == attendance_id).first()
    if not db_attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    if db_attendance.sign_out_time:
        raise HTTPException(status_code=400, detail="Child is already signed out")
    db_attendance.sign_out_time = datetime.utcnow()
    db_attendance.signed_out_by = signed_out_by or current_user.username
    db.commit()
    db.refresh(db_attendance)
    return db_attendance


@app.get("/attendance/today", response_model=List[AttendanceOut])
def get_today_attendance(db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    children = db.query(ChildModel).filter(ChildModel.daycare_id == current_user.daycare_id).all()
    child_ids = [c.id for c in children]
    return db.query(AttendanceModel).filter(
        AttendanceModel.child_id.in_(child_ids),
        AttendanceModel.date >= today
    ).order_by(AttendanceModel.sign_in_time.desc()).all()


@app.get("/attendance", response_model=List[AttendanceOut])
def list_attendance(child_id: Optional[int] = None, date_from: Optional[str] = None, date_to: Optional[str] = None, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    children = db.query(ChildModel).filter(ChildModel.daycare_id == current_user.daycare_id).all()
    child_ids = [c.id for c in children]
    query = db.query(AttendanceModel).filter(AttendanceModel.child_id.in_(child_ids))
    if child_id:
        query = query.filter(AttendanceModel.child_id == child_id)
    if date_from:
        query = query.filter(AttendanceModel.date >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(AttendanceModel.date <= datetime.fromisoformat(date_to))
    return query.order_by(AttendanceModel.sign_in_time.desc()).all()


# Daily Report endpoints
@app.post("/daily-reports", response_model=DailyReport)
def create_daily_report(report: DailyReportCreate, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    db_report = DailyReport(
        **report.model_dump(),
        date=datetime.utcnow(),
        staff_name=current_user.username
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report


@app.get("/daily-reports", response_model=List[DailyReport])
def list_daily_reports(child_id: Optional[int] = None, date: Optional[str] = None, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    children = db.query(ChildModel).filter(ChildModel.daycare_id == current_user.daycare_id).all()
    child_ids = [c.id for c in children]
    query = db.query(DailyReportModel).filter(DailyReportModel.child_id.in_(child_ids))
    if child_id:
        query = query.filter(DailyReportModel.child_id == child_id)
    if date:
        query = query.filter(DailyReportModel.date >= datetime.fromisoformat(date))
    return query.order_by(DailyReportModel.date.desc()).all()


# Incident endpoints
@app.post("/incidents", response_model=Incident)
def create_incident(incident: IncidentCreate, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    db_incident = IncidentModel(
        **incident.model_dump(),
        date=datetime.utcnow(),
        staff_name=current_user.username
    )
    db.add(db_incident)
    db.commit()
    db.refresh(db_incident)
    return db_incident


@app.get("/incidents", response_model=List[Incident])
def list_incidents(child_id: Optional[int] = None, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    children = db.query(ChildModel).filter(ChildModel.daycare_id == current_user.daycare_id).all()
    child_ids = [c.id for c in children]
    query = db.query(IncidentModel).filter(IncidentModel.child_id.in_(child_ids))
    if child_id:
        query = query.filter(IncidentModel.child_id == child_id)
    return query.order_by(IncidentModel.date.desc()).all()


# Dashboard stats
@app.get("/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    children = db.query(ChildModel).filter(ChildModel.daycare_id == current_user.daycare_id).all()
    child_ids = [c.id for c in children]
    total_children = len(children)
    total_parents = db.query(ParentModel).filter(ParentModel.daycare_id == current_user.daycare_id).count()
    total_classes = db.query(ClassModel).filter(ClassModel.daycare_id == current_user.daycare_id).count()
    currently_present = db.query(AttendanceModel).filter(
        AttendanceModel.child_id.in_(child_ids),
        AttendanceModel.date >= today,
        AttendanceModel.sign_out_time == None
    ).count()
    today_attendance = db.query(AttendanceModel).filter(
        AttendanceModel.child_id.in_(child_ids),
        AttendanceModel.date >= today
    ).count()
    today_incidents = db.query(IncidentModel).filter(
        IncidentModel.child_id.in_(child_ids),
        IncidentModel.date >= today
    ).count()
    return {
        "total_children": total_children,
        "total_parents": total_parents,
        "total_classes": total_classes,
        "currently_present": currently_present,
        "today_attendance": today_attendance,
        "today_incidents": today_incidents
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
