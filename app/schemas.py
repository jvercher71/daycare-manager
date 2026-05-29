import os
import re
import html
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, field_validator, EmailStr, ConfigDict, computed_field
from app.models import UserRole, InvoiceStatus, PaymentMethod


def sanitize_string(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = html.escape(value, quote=True)
    value = value.strip()
    return value


class UserCreate(BaseModel):
    email: str
    username: str
    password: str
    role: str = "staff"

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(pattern, v):
            raise ValueError("Invalid email format")
        return v.lower()

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(v) > 50:
            raise ValueError("Username must not exceed 50 characters")
        if not re.match(r"^[a-zA-Z0-9 _-]+$", v):
            raise ValueError("Username can only contain letters, numbers, spaces, hyphens, and underscores")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 128:
            raise ValueError("Password must not exceed 128 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        v = v.lower()
        if v not in [UserRole.ADMIN.value, UserRole.STAFF.value]:
            raise ValueError(f"Role must be one of: {UserRole.ADMIN.value}, {UserRole.STAFF.value}")
        return v


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    role: str
    is_active: bool
    daycare_id: Optional[int] = None


class Token(BaseModel):
    access_token: str
    token_type: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 128:
            raise ValueError("Password must not exceed 128 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class PasswordResetRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(pattern, v):
            raise ValueError("Invalid email format")
        return v.lower()


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 128:
            raise ValueError("Password must not exceed 128 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class DaycareCreate(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    logo_url: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name is required")
        if len(v) > 100:
            raise ValueError("Name must not exceed 100 characters")
        return sanitize_string(v)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = sanitize_string(v)
            if len(v) > 20:
                raise ValueError("Phone must not exceed 20 characters")
        return v


class Daycare(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    logo_url: Optional[str] = None


class ParentCreate(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: str
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name is required")
        if len(v) > 50:
            raise ValueError("Name must not exceed 50 characters")
        return sanitize_string(v)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
            if not re.match(pattern, v):
                raise ValueError("Invalid email format")
            return v.lower()
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Phone is required")
        if len(v) > 20:
            raise ValueError("Phone must not exceed 20 characters")
        return sanitize_string(v)

    @field_validator("notes", "address", "emergency_contact", "emergency_phone")
    @classmethod
    def sanitize_optional(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_string(v)


class ParentBrief(BaseModel):
    """Parent without the nested ``children`` collection.

    Used when a parent is embedded inside a child (ChildWithParents) so that
    serialization never has to load ``parent.children`` — which would trigger
    an async lazy-load and fail.
    """
    model_config = ConfigDict(from_attributes=True)

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
    is_deleted: bool = False


class Parent(ParentBrief):
    children: List["Child"] = []


class ChildCreate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: datetime
    allergies: Optional[str] = None
    medical_notes: Optional[str] = None
    photo_url: Optional[str] = None
    class_id: Optional[int] = None
    parent_ids: List[int] = []

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name is required")
        if len(v) > 50:
            raise ValueError("Name must not exceed 50 characters")
        return sanitize_string(v)

    @field_validator("allergies", "medical_notes")
    @classmethod
    def sanitize_text(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_string(v)


class Child(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    is_deleted: bool = False


class ChildWithParents(Child):
    parents: List[ParentBrief] = []


class ClassCreate(BaseModel):
    name: str
    age_range: Optional[str] = None
    max_capacity: Optional[int] = None
    teacher_name: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name is required")
        if len(v) > 100:
            raise ValueError("Name must not exceed 100 characters")
        return sanitize_string(v)

    @field_validator("max_capacity")
    @classmethod
    def validate_capacity(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("Max capacity must be a positive number")
        return v

    @field_validator("teacher_name", "age_range")
    @classmethod
    def sanitize_optional(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_string(v)


class ClassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    age_range: Optional[str] = None
    max_capacity: Optional[int] = None
    teacher_name: Optional[str] = None
    daycare_id: Optional[int] = None
    is_deleted: bool = False


class AttendanceCreate(BaseModel):
    child_id: int
    signed_in_by: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("notes")
    @classmethod
    def sanitize_notes(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_string(v)


class AttendanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    child_id: int
    sign_in_time: datetime
    sign_out_time: Optional[datetime] = None
    signed_in_by: Optional[str] = None
    signed_out_by: Optional[str] = None
    notes: Optional[str] = None
    date: datetime


class DailyReportCreate(BaseModel):
    child_id: int
    meals: Optional[str] = None
    nap_start: Optional[datetime] = None
    nap_end: Optional[datetime] = None
    activities: Optional[str] = None
    mood: Optional[str] = None
    diaper_changes: Optional[int] = None
    notes: Optional[str] = None

    @field_validator("meals", "activities", "notes", "mood")
    @classmethod
    def sanitize_text(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_string(v)

    @field_validator("diaper_changes")
    @classmethod
    def validate_diaper_changes(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("Diaper changes must be non-negative")
        return v


class DailyReport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class IncidentCreate(BaseModel):
    child_id: int
    incident_type: str
    description: str
    severity: Optional[str] = None
    action_taken: Optional[str] = None
    parent_notified: bool = False

    @field_validator("incident_type")
    @classmethod
    def validate_incident_type(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Incident type is required")
        if len(v) > 50:
            raise ValueError("Incident type must not exceed 50 characters")
        return sanitize_string(v)

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Description is required")
        return sanitize_string(v)

    @field_validator("action_taken")
    @classmethod
    def sanitize_action(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_string(v)


class Incident(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    child_id: int
    date: datetime
    incident_type: str
    description: str
    severity: Optional[str] = None
    action_taken: Optional[str] = None
    parent_notified: bool
    staff_name: Optional[str] = None


from typing import Optional, List, TypeVar, Generic

T = TypeVar("T")

_VALID_INVOICE_STATUSES = {s.value for s in InvoiceStatus}
_VALID_PAYMENT_METHODS = {m.value for m in PaymentMethod}


class InvoiceCreate(BaseModel):
    description: str
    amount: float  # in dollars; converted to cents on the server
    child_id: Optional[int] = None
    parent_id: Optional[int] = None
    due_date: Optional[datetime] = None
    notes: Optional[str] = None
    status: str = InvoiceStatus.DRAFT.value

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Description is required")
        if len(v) > 200:
            raise ValueError("Description must not exceed 200 characters")
        return sanitize_string(v)

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Amount must be greater than zero")
        if v > 1_000_000:
            raise ValueError("Amount is unrealistically large")
        return round(v, 2)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in _VALID_INVOICE_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(sorted(_VALID_INVOICE_STATUSES))}")
        return v

    @field_validator("notes")
    @classmethod
    def sanitize_notes(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_string(v)


class InvoiceUpdate(BaseModel):
    description: Optional[str] = None
    amount: Optional[float] = None
    due_date: Optional[datetime] = None
    notes: Optional[str] = None
    status: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            if v <= 0:
                raise ValueError("Amount must be greater than zero")
            if v > 1_000_000:
                raise ValueError("Amount is unrealistically large")
            return round(v, 2)
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.lower().strip()
            if v not in _VALID_INVOICE_STATUSES:
                raise ValueError(f"Status must be one of: {', '.join(sorted(_VALID_INVOICE_STATUSES))}")
        return v

    @field_validator("description", "notes")
    @classmethod
    def sanitize_text(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_string(v)


class PaymentCreate(BaseModel):
    amount: float  # in dollars
    method: str = PaymentMethod.CASH.value
    reference: Optional[str] = None
    payment_date: Optional[datetime] = None
    notes: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Payment amount must be greater than zero")
        if v > 1_000_000:
            raise ValueError("Amount is unrealistically large")
        return round(v, 2)

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in _VALID_PAYMENT_METHODS:
            raise ValueError(f"Method must be one of: {', '.join(sorted(_VALID_PAYMENT_METHODS))}")
        return v

    @field_validator("reference", "notes")
    @classmethod
    def sanitize_text(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_string(v)


class Payment(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int
    amount_cents: int
    method: str
    reference: Optional[str] = None
    processor: Optional[str] = None
    processor_txn_id: Optional[str] = None
    payment_date: Optional[datetime] = None
    notes: Optional[str] = None
    recorded_by: Optional[str] = None

    @computed_field
    @property
    def amount(self) -> float:
        return round(self.amount_cents / 100, 2)


class Invoice(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    daycare_id: int
    child_id: Optional[int] = None
    parent_id: Optional[int] = None
    description: str
    amount_cents: int
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    status: str
    notes: Optional[str] = None
    is_deleted: bool = False
    created_at: Optional[datetime] = None
    payments: List[Payment] = []

    @computed_field
    @property
    def amount(self) -> float:
        return round(self.amount_cents / 100, 2)

    @computed_field
    @property
    def amount_paid_cents(self) -> int:
        return sum(p.amount_cents for p in self.payments)

    @computed_field
    @property
    def amount_paid(self) -> float:
        return round(self.amount_paid_cents / 100, 2)

    @computed_field
    @property
    def balance_cents(self) -> int:
        return self.amount_cents - self.amount_paid_cents

    @computed_field
    @property
    def balance(self) -> float:
        return round(self.balance_cents / 100, 2)


class BillingSummary(BaseModel):
    total_invoiced_cents: int
    outstanding_cents: int
    collected_this_month_cents: int
    overdue_count: int
    overdue_cents: int
    draft_count: int
    paid_count: int

    @computed_field
    @property
    def total_invoiced(self) -> float:
        return round(self.total_invoiced_cents / 100, 2)

    @computed_field
    @property
    def outstanding(self) -> float:
        return round(self.outstanding_cents / 100, 2)

    @computed_field
    @property
    def collected_this_month(self) -> float:
        return round(self.collected_this_month_cents / 100, 2)

    @computed_field
    @property
    def overdue(self) -> float:
        return round(self.overdue_cents / 100, 2)


class PaginatedResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(from_attributes=True)

    total: int
    skip: int
    limit: int
    items: List[T]
