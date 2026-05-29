"""Add billing tables: invoices and payments

Revision ID: c5d6e7f8a9b0
Revises: 294c6d8f3574
Create Date: 2026-05-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5d6e7f8a9b0'
down_revision: Union[str, None] = '294c6d8f3574'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('daycare_id', sa.Integer(), nullable=False),
        sa.Column('child_id', sa.Integer(), nullable=True),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column('issue_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['daycare_id'], ['daycares.id'], ),
        sa.ForeignKeyConstraint(['child_id'], ['children.id'], ),
        sa.ForeignKeyConstraint(['parent_id'], ['parents.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_invoices_id'), 'invoices', ['id'], unique=False)
    op.create_index(op.f('ix_invoices_daycare_id'), 'invoices', ['daycare_id'], unique=False)

    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column('method', sa.String(), nullable=True),
        sa.Column('reference', sa.String(), nullable=True),
        sa.Column('processor', sa.String(), nullable=True),
        sa.Column('processor_txn_id', sa.String(), nullable=True),
        sa.Column('payment_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('recorded_by', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_payments_id'), 'payments', ['id'], unique=False)
    op.create_index(op.f('ix_payments_invoice_id'), 'payments', ['invoice_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_payments_invoice_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_id'), table_name='payments')
    op.drop_table('payments')
    op.drop_index(op.f('ix_invoices_daycare_id'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_id'), table_name='invoices')
    op.drop_table('invoices')
