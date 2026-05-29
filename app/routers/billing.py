from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime, timezone
from app.database import get_db
from app.models import (
    Invoice as InvoiceModel,
    Payment as PaymentModel,
    Child as ChildModel,
    Parent as ParentModel,
    InvoiceStatus,
    User as UserModel,
)
from app.schemas import (
    InvoiceCreate,
    InvoiceUpdate,
    Invoice,
    PaymentCreate,
    Payment,
    BillingSummary,
)
from app.auth import get_current_user, require_role

router = APIRouter(prefix="/billing", tags=["Billing"])


# --- helpers ---------------------------------------------------------------

def _to_cents(dollars: float) -> int:
    """Convert a dollar amount to an integer number of cents, safely rounded."""
    return int(round(dollars * 100))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """SQLite returns naive datetimes; treat them as UTC for safe comparison."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _paid_cents(invoice: InvoiceModel) -> int:
    return sum(p.amount_cents for p in invoice.payments)


def _recompute_status(invoice: InvoiceModel) -> None:
    """Update the stored status based on payments. Does not touch void/draft intentionally."""
    if invoice.status in (InvoiceStatus.VOID.value,):
        return
    paid = _paid_cents(invoice)
    if paid >= invoice.amount_cents and invoice.amount_cents > 0:
        invoice.status = InvoiceStatus.PAID.value
    elif paid > 0:
        invoice.status = InvoiceStatus.PARTIAL.value
    elif invoice.status == InvoiceStatus.PAID.value:
        # payments were removed
        invoice.status = InvoiceStatus.SENT.value


def _display_status(invoice: InvoiceModel) -> str:
    """Compute an effective status for display, flagging overdue without persisting it."""
    if invoice.status in (InvoiceStatus.PAID.value, InvoiceStatus.VOID.value, InvoiceStatus.DRAFT.value):
        return invoice.status
    due = _as_aware(invoice.due_date)
    if due and due < _now() and (invoice.amount_cents - _paid_cents(invoice)) > 0:
        return InvoiceStatus.OVERDUE.value
    return invoice.status


async def _get_owned_invoice(invoice_id: int, db: AsyncSession, user: UserModel) -> InvoiceModel:
    """Fetch a non-deleted invoice owned by the user's daycare, payments eager-loaded.

    Payments must be eager-loaded: the async session cannot lazy-load a
    relationship on demand outside of an explicit query.
    """
    result = await db.execute(
        select(InvoiceModel)
        .where(
            InvoiceModel.id == invoice_id,
            InvoiceModel.daycare_id == user.daycare_id,
            InvoiceModel.is_deleted == False,
        )
        .options(selectinload(InvoiceModel.payments))
    )
    invoice = result.scalars().first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


# --- invoices --------------------------------------------------------------

@router.post("/invoices", response_model=Invoice, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    payload: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    if current_user.daycare_id is None:
        raise HTTPException(status_code=400, detail="User is not associated with a daycare")

    # Validate the optional child/parent belong to this daycare.
    if payload.child_id is not None:
        result = await db.execute(
            select(ChildModel).where(
                ChildModel.id == payload.child_id,
                ChildModel.daycare_id == current_user.daycare_id,
                ChildModel.is_deleted == False,
            )
        )
        if not result.scalars().first():
            raise HTTPException(status_code=404, detail="Child not found")
    if payload.parent_id is not None:
        result = await db.execute(
            select(ParentModel).where(
                ParentModel.id == payload.parent_id,
                ParentModel.daycare_id == current_user.daycare_id,
                ParentModel.is_deleted == False,
            )
        )
        if not result.scalars().first():
            raise HTTPException(status_code=404, detail="Parent not found")

    invoice = InvoiceModel(
        daycare_id=current_user.daycare_id,
        child_id=payload.child_id,
        parent_id=payload.parent_id,
        description=payload.description,
        amount_cents=_to_cents(payload.amount),
        due_date=payload.due_date,
        notes=payload.notes,
        status=payload.status,
        issue_date=_now(),
        created_by=current_user.id,
    )
    db.add(invoice)
    await db.commit()
    # Re-fetch with payments eager-loaded so the response can serialize them.
    return await _get_owned_invoice(invoice.id, db, current_user)


@router.get("/invoices", response_model=List[Invoice])
async def list_invoices(
    status_filter: Optional[str] = Query(None, alias="status"),
    child_id: Optional[int] = None,
    parent_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    query = select(InvoiceModel).where(
        InvoiceModel.daycare_id == current_user.daycare_id,
        InvoiceModel.is_deleted == False,
    )
    if child_id is not None:
        query = query.where(InvoiceModel.child_id == child_id)
    if parent_id is not None:
        query = query.where(InvoiceModel.parent_id == parent_id)

    result = await db.execute(
        query.options(selectinload(InvoiceModel.payments))
        .order_by(InvoiceModel.issue_date.desc())
        .offset(skip)
        .limit(limit)
    )
    invoices = result.scalars().all()

    # Apply the computed overdue status for display (not persisted).
    for inv in invoices:
        inv.status = _display_status(inv)

    if status_filter:
        sf = status_filter.lower().strip()
        invoices = [inv for inv in invoices if inv.status == sf]
    return invoices


@router.get("/invoices/{invoice_id}", response_model=Invoice)
async def get_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    invoice = await _get_owned_invoice(invoice_id, db, current_user)
    invoice.status = _display_status(invoice)
    return invoice


@router.patch("/invoices/{invoice_id}", response_model=Invoice)
async def update_invoice(
    invoice_id: int,
    payload: InvoiceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(require_role("admin")),
):
    invoice = await _get_owned_invoice(invoice_id, db, current_user)
    if payload.description is not None:
        invoice.description = payload.description
    if payload.amount is not None:
        invoice.amount_cents = _to_cents(payload.amount)
    if payload.due_date is not None:
        invoice.due_date = payload.due_date
    if payload.notes is not None:
        invoice.notes = payload.notes
    if payload.status is not None:
        invoice.status = payload.status
    # Keep paid/partial accurate if amount or status changed.
    _recompute_status(invoice)
    await db.commit()
    invoice = await _get_owned_invoice(invoice_id, db, current_user)
    invoice.status = _display_status(invoice)
    return invoice


@router.delete("/invoices/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(require_role("admin")),
):
    invoice = await _get_owned_invoice(invoice_id, db, current_user)
    invoice.is_deleted = True
    await db.commit()
    return None


# --- payments --------------------------------------------------------------

@router.post("/invoices/{invoice_id}/payments", response_model=Invoice, status_code=status.HTTP_201_CREATED)
async def record_payment(
    invoice_id: int,
    payload: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    invoice = await _get_owned_invoice(invoice_id, db, current_user)
    if invoice.status == InvoiceStatus.VOID.value:
        raise HTTPException(status_code=400, detail="Cannot record a payment against a void invoice")

    payment = PaymentModel(
        invoice_id=invoice.id,
        amount_cents=_to_cents(payload.amount),
        method=payload.method,
        reference=payload.reference,
        payment_date=payload.payment_date or _now(),
        notes=payload.notes,
        recorded_by=current_user.username,
    )
    db.add(payment)
    await db.commit()
    # Reload the payments collection (refresh, not re-query: the invoice is already
    # in the identity map with payments loaded, so selectinload wouldn't reload it).
    await db.refresh(invoice, attribute_names=["payments"])
    _recompute_status(invoice)
    await db.commit()
    invoice.status = _display_status(invoice)
    return invoice


@router.get("/invoices/{invoice_id}/payments", response_model=List[Payment])
async def list_payments(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    invoice = await _get_owned_invoice(invoice_id, db, current_user)
    return sorted(invoice.payments, key=lambda p: p.payment_date or datetime.min, reverse=True)


# --- summary ---------------------------------------------------------------

@router.get("/summary", response_model=BillingSummary)
async def billing_summary(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    result = await db.execute(
        select(InvoiceModel)
        .where(
            InvoiceModel.daycare_id == current_user.daycare_id,
            InvoiceModel.is_deleted == False,
        )
        .options(selectinload(InvoiceModel.payments))
    )
    invoices = result.scalars().all()

    now = _now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_invoiced = 0
    outstanding = 0
    overdue_count = 0
    overdue_cents = 0
    draft_count = 0
    paid_count = 0
    collected_this_month = 0

    for inv in invoices:
        if inv.status == InvoiceStatus.VOID.value:
            continue
        paid = _paid_cents(inv)
        balance = inv.amount_cents - paid
        total_invoiced += inv.amount_cents
        if inv.status == InvoiceStatus.DRAFT.value:
            draft_count += 1
        if balance <= 0 and inv.amount_cents > 0:
            paid_count += 1
        else:
            outstanding += balance
            due = _as_aware(inv.due_date)
            if due and due < now and balance > 0:
                overdue_count += 1
                overdue_cents += balance

        for p in inv.payments:
            pd = _as_aware(p.payment_date)
            if pd and pd >= month_start:
                collected_this_month += p.amount_cents

    return BillingSummary(
        total_invoiced_cents=total_invoiced,
        outstanding_cents=outstanding,
        collected_this_month_cents=collected_this_month,
        overdue_count=overdue_count,
        overdue_cents=overdue_cents,
        draft_count=draft_count,
        paid_count=paid_count,
    )
