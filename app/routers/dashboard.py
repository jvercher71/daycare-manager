from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
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
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # Get all child IDs for this daycare
    children_result = await db.execute(
        select(ChildModel.id).where(
            ChildModel.daycare_id == current_user.daycare_id,
            ChildModel.is_deleted == False
        )
    )
    child_ids = children_result.scalars().all()
    total_children = len(child_ids)

    total_parents_result = await db.execute(
        select(func.count()).select_from(ParentModel).where(
            ParentModel.daycare_id == current_user.daycare_id,
            ParentModel.is_deleted == False
        )
    )
    total_parents = total_parents_result.scalar()

    total_classes_result = await db.execute(
        select(func.count()).select_from(ClassModel).where(
            ClassModel.daycare_id == current_user.daycare_id,
            ClassModel.is_deleted == False
        )
    )
    total_classes = total_classes_result.scalar()

    currently_present = 0
    today_attendance_count = 0
    today_incidents = 0

    if child_ids:
        present_result = await db.execute(
            select(func.count()).select_from(AttendanceModel).where(
                AttendanceModel.child_id.in_(child_ids),
                AttendanceModel.date >= today,
                AttendanceModel.sign_out_time == None
            )
        )
        currently_present = present_result.scalar()

        today_att_result = await db.execute(
            select(func.count()).select_from(AttendanceModel).where(
                AttendanceModel.child_id.in_(child_ids),
                AttendanceModel.date >= today
            )
        )
        today_attendance_count = today_att_result.scalar()

        incidents_result = await db.execute(
            select(func.count()).select_from(IncidentModel).where(
                IncidentModel.child_id.in_(child_ids),
                IncidentModel.date >= today
            )
        )
        today_incidents = incidents_result.scalar()

    return {
        "total_children": total_children,
        "total_parents": total_parents,
        "total_classes": total_classes,
        "currently_present": currently_present,
        "today_attendance": today_attendance_count,
        "today_incidents": today_incidents
    }
