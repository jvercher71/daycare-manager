"""Seed a full demo tenant ("Sprout Demo Daycare") that exercises every feature.

Creates a daycare, admin + staff users, classrooms, parents (incl. sibling
families and two-guardian children), 25 children, attendance history, daily
reports, incidents, invoices spanning every status, and payments.

Idempotent: re-running wipes the prior demo tenant (matched by name) and its
dependent rows, then re-seeds. Other tenants are untouched.

Run:  venv/bin/python -m scripts.seed_demo_data
"""
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, delete

from app.database import AsyncSessionLocal, init_db
from app.models import (
    Daycare, User, Parent, Child, ClassRoom, Attendance,
    DailyReport, Incident, Invoice, Payment, parent_child,
    UserRole, ChildStatus, InvoiceStatus, PaymentMethod,
)
from app.auth import get_password_hash

DEMO_DAYCARE_NAME = "Sprout Demo Daycare"
DEMO_PASSWORD = "DemoPass123"


def now() -> datetime:
    return datetime.now(timezone.utc)


def days_ago(n: int) -> datetime:
    return now() - timedelta(days=n)


def at(d: datetime, hour: int, minute: int = 0) -> datetime:
    return d.replace(hour=hour, minute=minute, second=0, microsecond=0)


def cents(dollars: float) -> int:
    return int(round(dollars * 100))


# --- static demo content ---------------------------------------------------

# (name, age_range, max_capacity, teacher)  +  birth-year used for that room
CLASSES = [
    ("Infants",   "6 weeks - 1 year", 8,  "Ms. Tanya Brooks",   2025),
    ("Toddlers",  "1 - 2 years",      12, "Mr. Devon Hill",     2024),
    ("Preschool", "3 - 4 years",      16, "Ms. Priya Nair",     2022),
    ("Pre-K",     "4 - 5 years",      18, "Ms. Gabriela Ortiz", 2021),
]

# 25 children: (first, last, room_index, allergies, medical_notes)
CHILDREN = [
    ("Liam", "Anderson", 0, None, None),
    ("Olivia", "Anderson", 2, "Peanuts", "EpiPen in cubby"),          # sibling pair
    ("Noah", "Brooks", 0, None, "Reflux - smaller bottles"),
    ("Emma", "Carter", 0, "Dairy", None),
    ("Ava", "Diaz", 0, None, None),
    ("Sophia", "Diaz", 1, None, None),                                # sibling pair
    ("Mason", "Evans", 1, "Eggs", None),
    ("Isabella", "Foster", 1, None, "Eczema - apply cream after nap"),
    ("Lucas", "Garcia", 1, None, None),
    ("Mia", "Garcia", 3, None, None),                                 # sibling pair
    ("Ethan", "Hughes", 1, None, None),
    ("Charlotte", "Ingram", 1, "Tree nuts", None),
    ("Logan", "Jackson", 2, None, None),
    ("Amelia", "Kelly", 2, None, "Asthma - inhaler with staff"),
    ("James", "Lopez", 2, None, None),
    ("Harper", "Lopez", 3, None, None),                              # sibling pair
    ("Benjamin", "Morgan", 2, "Strawberries", None),
    ("Evelyn", "Nguyen", 2, None, None),
    ("Henry", "Owens", 2, None, None),
    ("Abigail", "Patel", 3, None, None),
    ("Alexander", "Quinn", 3, None, "Lactose intolerant"),
    ("Emily", "Reed", 3, None, None),
    ("Daniel", "Sanchez", 3, None, None),
    ("Elizabeth", "Turner", 3, "Penicillin", None),
    ("Michael", "Walker", 3, None, None),
]

MOODS = ["Happy", "Calm", "Playful", "Sleepy", "Fussy", "Energetic"]
MEALS = [
    "Breakfast: oatmeal & banana (ate all). Lunch: chicken, rice, peas (most).",
    "Breakfast: yogurt & berries. Lunch: pasta with veggies (ate half).",
    "Breakfast: scrambled eggs & toast. Lunch: turkey sandwich, apple slices.",
    "Bottle 6oz at 9am. Pureed sweet potato at noon. Bottle 5oz at 3pm.",
]
ACTIVITIES = [
    "Circle time, finger painting, outdoor play.",
    "Story time, block building, music & movement.",
    "Sensory bins, sidewalk chalk, group snack.",
    "Tummy time, sensory toys, lullaby nap routine.",
]
INCIDENTS = [
    ("Minor fall", "Tripped on the play mat during free play; small bump on knee.", "low",
     "Applied cold pack, comforted child, monitored for 30 min.", True),
    ("Biting", "Bitten on the arm by another child during a toy dispute.", "medium",
     "Cleaned area, applied cold compress, separated children, documented both families.", True),
    ("Allergic reaction", "Mild hives after snack; suspected dairy exposure.", "high",
     "Removed food, administered antihistamine per care plan, called parent, monitored breathing.", True),
    ("Bumped head", "Knocked head on table edge while standing up.", "low",
     "Cold pack applied, no swelling, child alert and playing.", True),
    ("Fever", "Temperature 100.8F detected at afternoon check.", "medium",
     "Moved to quiet area, fluids offered, parent contacted for pickup.", False),
    ("Scratch", "Minor scratch on cheek from another child during play.", "low",
     "Cleaned with antiseptic wipe, no bandage needed.", False),
]


async def _wipe_existing_demo(session) -> None:
    """Delete any prior demo tenant and all its dependent rows."""
    result = await session.execute(
        select(Daycare.id).where(Daycare.name == DEMO_DAYCARE_NAME)
    )
    daycare_ids = [r[0] for r in result.all()]
    if not daycare_ids:
        return

    child_ids = [
        r[0] for r in (
            await session.execute(select(Child.id).where(Child.daycare_id.in_(daycare_ids)))
        ).all()
    ]
    invoice_ids = [
        r[0] for r in (
            await session.execute(select(Invoice.id).where(Invoice.daycare_id.in_(daycare_ids)))
        ).all()
    ]
    parent_ids = [
        r[0] for r in (
            await session.execute(select(Parent.id).where(Parent.daycare_id.in_(daycare_ids)))
        ).all()
    ]

    if invoice_ids:
        await session.execute(delete(Payment).where(Payment.invoice_id.in_(invoice_ids)))
    await session.execute(delete(Invoice).where(Invoice.daycare_id.in_(daycare_ids)))
    if child_ids:
        await session.execute(delete(Incident).where(Incident.child_id.in_(child_ids)))
        await session.execute(delete(DailyReport).where(DailyReport.child_id.in_(child_ids)))
        await session.execute(delete(Attendance).where(Attendance.child_id.in_(child_ids)))
        await session.execute(delete(parent_child).where(parent_child.c.child_id.in_(child_ids)))
    if parent_ids:
        await session.execute(delete(parent_child).where(parent_child.c.parent_id.in_(parent_ids)))
    await session.execute(delete(Child).where(Child.daycare_id.in_(daycare_ids)))
    await session.execute(delete(Parent).where(Parent.daycare_id.in_(daycare_ids)))
    await session.execute(delete(ClassRoom).where(ClassRoom.daycare_id.in_(daycare_ids)))
    await session.execute(delete(User).where(User.daycare_id.in_(daycare_ids)))
    await session.execute(delete(Daycare).where(Daycare.id.in_(daycare_ids)))
    await session.commit()


async def seed() -> None:
    await init_db()
    async with AsyncSessionLocal() as session:
        await _wipe_existing_demo(session)

        # --- daycare -------------------------------------------------------
        daycare = Daycare(
            name=DEMO_DAYCARE_NAME,
            address="142 Maple Street, Springfield, IL 62704",
            phone="(217) 555-0142",
            email="hello@sproutdemo.com",
        )
        session.add(daycare)
        await session.flush()

        # --- users (1 admin + 2 staff) ------------------------------------
        admin = User(
            email="admin@sproutdemo.com", username="Demo Admin",
            hashed_password=get_password_hash(DEMO_PASSWORD),
            role=UserRole.ADMIN.value, is_active=True, daycare_id=daycare.id,
        )
        staff1 = User(
            email="teacher@sproutdemo.com", username="Priya Nair",
            hashed_password=get_password_hash(DEMO_PASSWORD),
            role=UserRole.STAFF.value, is_active=True, daycare_id=daycare.id,
        )
        staff2 = User(
            email="frontdesk@sproutdemo.com", username="Devon Hill",
            hashed_password=get_password_hash(DEMO_PASSWORD),
            role=UserRole.STAFF.value, is_active=True, daycare_id=daycare.id,
        )
        session.add_all([admin, staff1, staff2])
        await session.flush()

        # --- classes -------------------------------------------------------
        classrooms = []
        for name, age_range, cap, teacher, _year in CLASSES:
            c = ClassRoom(
                name=name, age_range=age_range, max_capacity=cap,
                teacher_name=teacher, daycare_id=daycare.id, created_by=admin.id,
            )
            session.add(c)
            classrooms.append(c)
        await session.flush()

        # --- parents (one per family surname) + children ------------------
        # NOTE: links are written straight into the parent_child association
        # table. Mutating child.parents on a persisted row would trigger an
        # async lazy-load of the backref and fail.
        parents_by_surname: dict[str, Parent] = {}
        primary_parent_of: dict[int, Parent] = {}
        children = []
        for idx, (first, last, room_idx, allergies, medical) in enumerate(CHILDREN):
            if last not in parents_by_surname:
                p = Parent(
                    first_name="Parent", last_name=last,
                    email=f"{last.lower()}.family@example.com",
                    phone=f"(217) 555-{1000 + idx:04d}",
                    address=f"{100 + idx} Oak Avenue, Springfield, IL",
                    emergency_contact=f"Grandparent {last}",
                    emergency_phone=f"(217) 555-{2000 + idx:04d}",
                    notes="Prefers text messages for daily updates." if idx % 4 == 0 else None,
                    daycare_id=daycare.id, created_by=admin.id,
                )
                session.add(p)
                await session.flush()
                parents_by_surname[last] = p

            room = classrooms[room_idx]
            birth_year = CLASSES[room_idx][4]
            # spread birthdays across the year deterministically
            dob = datetime(birth_year, (idx % 12) + 1, (idx % 27) + 1, tzinfo=timezone.utc)
            child = Child(
                first_name=first, last_name=last, date_of_birth=dob,
                allergies=allergies, medical_notes=medical,
                status=ChildStatus.ACTIVE.value, class_id=room.id,
                daycare_id=daycare.id, created_by=admin.id,
            )
            session.add(child)
            await session.flush()
            await session.execute(
                parent_child.insert().values(
                    parent_id=parents_by_surname[last].id, child_id=child.id
                )
            )
            primary_parent_of[child.id] = parents_by_surname[last]
            children.append(child)
        await session.flush()

        # one child marked inactive (withdrawn) to exercise status filtering
        children[-1].status = ChildStatus.INACTIVE.value

        # a couple of two-guardian children: add a second parent
        second_guardians = [
            ("Jordan", children[0]),   # Liam Anderson
            ("Casey", children[4]),    # Ava Diaz
        ]
        for gfirst, child in second_guardians:
            g = Parent(
                first_name=gfirst, last_name=child.last_name,
                email=f"{gfirst.lower()}.{child.last_name.lower()}@example.com",
                phone="(217) 555-0199",
                emergency_contact="Aunt/Uncle", emergency_phone="(217) 555-0200",
                daycare_id=daycare.id, created_by=admin.id,
            )
            session.add(g)
            await session.flush()
            await session.execute(
                parent_child.insert().values(parent_id=g.id, child_id=child.id)
            )
        await session.flush()

        active_children = [c for c in children if c.status == ChildStatus.ACTIVE.value]

        # --- attendance (last 5 weekdays) ---------------------------------
        staff_names = ["Priya Nair", "Devon Hill", "Tanya Brooks"]
        att_count = 0
        for d_off in range(5, 0, -1):
            day = days_ago(d_off)
            if day.weekday() >= 5:  # skip Sat/Sun
                continue
            for i, child in enumerate(active_children):
                if (i + d_off) % 5 == 0:  # ~20% absent each day
                    continue
                att = Attendance(
                    child_id=child.id, date=at(day, 0),
                    sign_in_time=at(day, 7, (i % 6) * 10),
                    sign_out_time=at(day, 16, (i % 5) * 12),
                    signed_in_by=f"Parent {child.last_name}",
                    signed_out_by=f"Parent {child.last_name}",
                    notes="Late pickup - traffic" if i % 9 == 0 else None,
                )
                session.add(att)
                att_count += 1

        # today: some children currently signed in (no sign-out yet)
        today = now()
        for i, child in enumerate(active_children[:12]):
            session.add(Attendance(
                child_id=child.id, date=at(today, 0),
                sign_in_time=at(today, 8, (i % 6) * 5),
                sign_out_time=None,
                signed_in_by=f"Parent {child.last_name}",
            ))
            att_count += 1

        # --- daily reports (last 3 days, subset of children) --------------
        report_count = 0
        for d_off in (2, 1, 0):
            day = days_ago(d_off)
            for i, child in enumerate(active_children):
                if i % 2 != d_off % 2:  # vary which children get reports
                    continue
                is_infant = child.class_id == classrooms[0].id
                session.add(DailyReport(
                    child_id=child.id, date=at(day, 17),
                    meals=MEALS[3] if is_infant else MEALS[i % 3],
                    nap_start=at(day, 12, 30), nap_end=at(day, 14, 15),
                    activities=ACTIVITIES[3] if is_infant else ACTIVITIES[i % 3],
                    mood=MOODS[i % len(MOODS)],
                    diaper_changes=(3 + i % 3) if is_infant else None,
                    notes="Had a great day!" if i % 5 == 0 else None,
                    staff_name=staff_names[i % len(staff_names)],
                ))
                report_count += 1

        # --- incidents -----------------------------------------------------
        for i, (itype, desc, sev, action, notified) in enumerate(INCIDENTS):
            child = active_children[(i * 3) % len(active_children)]
            session.add(Incident(
                child_id=child.id, date=at(days_ago(i + 1), 11, 20),
                incident_type=itype, description=desc, severity=sev,
                action_taken=action, parent_notified=notified,
                staff_name=staff_names[i % len(staff_names)],
            ))

        # --- invoices + payments (every status represented) ---------------
        # statuses cycled across children: draft, sent, partial, paid, overdue, void
        await session.flush()
        invoice_count = payment_count = 0
        plan = [
            # (status_intent, amount, due_offset_days, payment)
            ("draft",   950.00, None, None),
            ("sent",   1000.00,  10,  None),
            ("partial", 1200.00,  5,  ("partial", PaymentMethod.CARD.value)),
            ("paid",    900.00,  -2,  ("full", PaymentMethod.CHECK.value)),
            ("overdue", 1100.00, -10, None),
            ("void",    800.00,   7,  None),
        ]
        for i, child in enumerate(active_children):
            intent, amount, due_off, pay = plan[i % len(plan)]
            primary_parent = primary_parent_of[child.id]
            due_date = None if due_off is None else (now() + timedelta(days=due_off))
            status_value = (
                InvoiceStatus.SENT.value if intent == "overdue" else
                InvoiceStatus.DRAFT.value if intent == "draft" else
                InvoiceStatus.SENT.value if intent in ("sent", "partial", "paid") else
                InvoiceStatus.VOID.value
            )
            inv = Invoice(
                daycare_id=daycare.id, child_id=child.id, parent_id=primary_parent.id,
                description=f"May 2026 tuition - {child.first_name} {child.last_name}",
                amount_cents=cents(amount),
                issue_date=days_ago(20),
                due_date=due_date,
                status=status_value,
                notes="Monthly tuition" if i % 3 == 0 else None,
                created_by=admin.id,
            )
            session.add(inv)
            await session.flush()
            invoice_count += 1

            if pay:
                kind, method = pay
                pay_amount = amount if kind == "full" else round(amount * 0.4, 2)
                p = Payment(
                    invoice_id=inv.id, amount_cents=cents(pay_amount), method=method,
                    reference="CHK 2041" if method == PaymentMethod.CHECK.value else "TXN-DEMO-001",
                    payment_date=days_ago(3), notes="Recorded at front desk",
                    recorded_by="Demo Admin",
                )
                session.add(p)
                payment_count += 1
                # reflect payment in stored status
                inv.status = InvoiceStatus.PAID.value if kind == "full" else InvoiceStatus.PARTIAL.value

        await session.commit()

        # --- summary -------------------------------------------------------
        print("\n  Seeded '%s' (daycare id=%d)\n" % (DEMO_DAYCARE_NAME, daycare.id))
        print("   Users        : 3 (1 admin, 2 staff)")
        print("   Classrooms   : %d" % len(classrooms))
        print("   Parents      : %d" % (len(parents_by_surname) + len(second_guardians)))
        print("   Children     : %d (24 active, 1 inactive)" % len(children))
        print("   Attendance   : %d records (incl. %d currently signed in today)" % (att_count, 12))
        print("   Daily reports: %d" % report_count)
        print("   Incidents    : %d" % len(INCIDENTS))
        print("   Invoices     : %d (draft/sent/partial/paid/overdue/void)" % invoice_count)
        print("   Payments     : %d" % payment_count)
        print("\n  Login:  admin@sproutdemo.com  /  %s   (role: admin)" % DEMO_PASSWORD)
        print("          teacher@sproutdemo.com /  %s   (role: staff)\n" % DEMO_PASSWORD)


if __name__ == "__main__":
    asyncio.run(seed())
