"""add_payment_invoices

Revision ID: b2c3d4e5f6a7
Revises: a1f2c3d4e5f6
Create Date: 2026-02-11 18:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1f2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE invoicestatus AS ENUM ('PENDING', 'PAID', 'EXPIRED');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """))

    op.execute(sa.text("""
        CREATE TABLE payment_invoices (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id),
            crypto_bot_invoice_id INTEGER NOT NULL UNIQUE,
            amount INTEGER NOT NULL,
            status invoicestatus NOT NULL DEFAULT 'PENDING',
            pay_url VARCHAR(512),
            mini_app_invoice_url VARCHAR(512),
            balance_transaction_id INTEGER REFERENCES balance_transactions(id),
            paid_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """))

    op.execute(sa.text("CREATE INDEX ix_payment_invoices_user_id ON payment_invoices (user_id)"))
    op.execute(sa.text("CREATE INDEX ix_payment_invoices_status ON payment_invoices (status)"))


def downgrade() -> None:
    op.drop_index('ix_payment_invoices_status', table_name='payment_invoices')
    op.drop_index('ix_payment_invoices_crypto_bot_invoice_id', table_name='payment_invoices')
    op.drop_index('ix_payment_invoices_user_id', table_name='payment_invoices')
    op.drop_table('payment_invoices')

    sa.Enum(name='invoicestatus').drop(op.get_bind(), checkfirst=True)
