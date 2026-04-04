from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.database import get_db
from app.models import (
    Child as ChildModel,
    Parent as ParentModel,
    ClassRoom as ClassModel,
    Attendance as AttendanceModel,
    Incident as IncidentModel,
)
from app.auth import get_current_user
from app.models import User as UserModel

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    children = db.query(ChildModel).filter(
        ChildModel.daycare_id == current_user.daycare_id,
        ChildModel.is_deleted == False
    ).all()
    child_ids = [c.id for c in children]
    total_children = len(children)
    total_parents = db.query(ParentModel).filter(
        ParentModel.daycare_id == current_user.daycare_id,
        ParentModel.is_deleted == False
    ).count()
    total_classes = db.query(ClassModel).filter(
        ClassModel.daycare_id == current_user.daycare_id,
        ClassModel.is_deleted == False
    ).count()
    currently_present = 0
    today_attendance_count = 0
    today_incidents = 0
    if child_ids:
        currently_present = db.query(AttendanceModel).filter(
            AttendanceModel.child_id.in_(child_ids),
            AttendanceModel.date >= today,
            AttendanceModel.sign_out_time == None
        ).count()
        today_attendance_count = db.query(AttendanceModel).filter(
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
        "today_attendance": today_attendance_count,
        "today_incidents": today_incidents
    }
