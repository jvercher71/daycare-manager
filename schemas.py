from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class UserCreate(BaseModel):
    email: str
    username: str
    password: str
    role: str = "staff"


class User(BaseModel):
    id: int
    email: str
    username: str
    role: str
    is_active: bool
    daycare_id: Optional[int] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class DaycareCreate(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    logo_url: Optional[str] = None


class Daycare(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    logo_url: Optional[str] = None

    class Config:
        from_attributes = True


class ParentCreate(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: str
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    notes: Optional[str] = None


class Parent(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: str
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    notes: Optional[str] = None
    daycare_id: Optional[int] = None
    children: List["Child"] = []

    class Config:
        from_attributes = True


class ChildCreate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: datetime
    allergies: Optional[str] = None
    medical_notes: Optional[str] = None
    photo_url: Optional[str] = None
    class_id: Optional[int] = None
    parent_ids: List[int] = []


class Child(BaseModel):
    id: int
    first_name: str
    last_name: str
    date_of_birth: Optional[datetime] = None
    allergies: Optional[str] = None
    medical_notes: Optional[str] = None
    photo_url: Optional[str] = None
    status: str = "active"
    class_id: Optional[int] = None
    daycare_id: Optional[int] = None

    class Config:
        from_attributes = True


class ChildWithParents(Child):
    parents: List[Parent] = []


class ClassCreate(BaseModel):
    name: str
    age_range: Optional[str] = None
    max_capacity: Optional[int] = None
    teacher_name: Optional[str] = None


class ClassOut(BaseModel):
    id: int
    name: str
    age_range: Optional[str] = None
    max_capacity: Optional[int] = None
    teacher_name: Optional[str] = None
    daycare_id: Optional[int] = None

    class Config:
        from_attributes = True


class AttendanceCreate(BaseModel):
    child_id: int
    signed_in_by: Optional[str] = None
    notes: Optional[str] = None


class AttendanceOut(BaseModel):
    id: int
    child_id: int
    sign_in_time: datetime
    sign_out_time: Optional[datetime] = None
    signed_in_by: Optional[str] = None
    signed_out_by: Optional[str] = None
    notes: Optional[str] = None
    date: datetime

    class Config:
        from_attributes = True


class DailyReportCreate(BaseModel):
    child_id: int
    meals: Optional[str] = None
    nap_start: Optional[datetime] = None
    nap_end: Optional[datetime] = None
    activities: Optional[str] = None
    mood: Optional[str] = None
    diaper_changes: Optional[int] = None
    notes: Optional[str] = None


class DailyReport(BaseModel):
    id: int
    child_id: int
    date: datetime
    meals: Optional[str] = None
    nap_start: Optional[datetime] = None
    nap_end: Optional[datetime] = None
    activities: Optional[str] = None
    mood: Optional[str] = None
    diaper_changes: Optional[int] = None
    notes: Optional[str] = None
    staff_name: Optional[str] = None

    class Config:
        from_attributes = True


class IncidentCreate(BaseModel):
    child_id: int
    incident_type: str
    description: str
    severity: Optional[str] = None
    action_taken: Optional[str] = None
    parent_notified: bool = False


class Incident(BaseModel):
    id: int
    child_id: int
    date: datetime
    incident_type: str
    description: str
    severity: Optional[str] = None
    action_taken: Optional[str] = None
    parent_notified: bool
    staff_name: Optional[str] = None

    class Config:
        from_attributes = True
