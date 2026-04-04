from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Table, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    STAFF = "staff"


class ChildStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


parent_child = Table(
    'parent_child',
    Base.metadata,
    Column('parent_id', Integer, ForeignKey('parents.id'), primary_key=True),
    Column('child_id', Integer, ForeignKey('children.id'), primary_key=True)
)


class Daycare(Base):
    __tablename__ = "daycares"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    users = relationship("User", back_populates="daycare")
    classes = relationship("ClassRoom", back_populates="daycare")
    parents = relationship("Parent", back_populates="daycare")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default=UserRole.STAFF)
    is_active = Column(Boolean, default=True)
    daycare_id = Column(Integer, ForeignKey("daycares.id"), index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    daycare = relationship("Daycare", back_populates="users")


class Parent(Base):
    __tablename__ = "parents"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=False)
    address = Column(String, nullable=True)
    emergency_contact = Column(String, nullable=True)
    emergency_phone = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    daycare_id = Column(Integer, ForeignKey("daycares.id"), index=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    daycare = relationship("Daycare", back_populates="parents")
    children = relationship("Child", secondary=parent_child, back_populates="parents")


class Child(Base):
    __tablename__ = "children"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    date_of_birth = Column(DateTime(timezone=True), nullable=False)
    allergies = Column(Text, nullable=True)
    medical_notes = Column(Text, nullable=True)
    photo_url = Column(String, nullable=True)
    status = Column(String, default=ChildStatus.ACTIVE)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=True, index=True)
    daycare_id = Column(Integer, ForeignKey("daycares.id"), index=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    parents = relationship("Parent", secondary=parent_child, back_populates="children")
    classroom = relationship("ClassRoom", back_populates="children")
    attendance_records = relationship("Attendance", back_populates="child")
    daily_reports = relationship("DailyReport", back_populates="child")
    incidents = relationship("Incident", back_populates="child")


class ClassRoom(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    age_range = Column(String, nullable=True)
    max_capacity = Column(Integer, nullable=True)
    teacher_name = Column(String, nullable=True)
    daycare_id = Column(Integer, ForeignKey("daycares.id"), index=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    daycare = relationship("Daycare", back_populates="classes")
    children = relationship("Child", back_populates="classroom")


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False, index=True)
    sign_in_time = Column(DateTime(timezone=True), nullable=False)
    sign_out_time = Column(DateTime(timezone=True), nullable=True)
    signed_in_by = Column(String, nullable=True)
    signed_out_by = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    child = relationship("Child", back_populates="attendance_records")


class DailyReport(Base):
    __tablename__ = "daily_reports"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False, index=True)
    date = Column(DateTime(timezone=True), nullable=False)
    meals = Column(Text, nullable=True)
    nap_start = Column(DateTime(timezone=True), nullable=True)
    nap_end = Column(DateTime(timezone=True), nullable=True)
    activities = Column(Text, nullable=True)
    mood = Column(String, nullable=True)
    diaper_changes = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    staff_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    child = relationship("Child", back_populates="daily_reports")


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False, index=True)
    date = Column(DateTime(timezone=True), nullable=False)
    incident_type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String, nullable=True)
    action_taken = Column(Text, nullable=True)
    parent_notified = Column(Boolean, default=False)
    staff_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    child = relationship("Child", back_populates="incidents")
