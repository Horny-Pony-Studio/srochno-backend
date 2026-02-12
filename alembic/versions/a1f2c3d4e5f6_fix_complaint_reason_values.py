"""fix_complaint_reason_values

Revision ID: a1f2c3d4e5f6
Revises: 9b7accc62b32
Create Date: 2026-02-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a1f2c3d4e5f6'
down_revision: Union[str, None] = '9b7accc62b32'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No-op: enum already has correct English values (NO_RESPONSE, CANCELLED_ORDER, etc.)
    pass


def downgrade() -> None:
    pass
