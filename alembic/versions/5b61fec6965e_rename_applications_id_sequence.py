"""rename applications id sequence

Revision ID: 5b61fec6965e
Revises: edf5f5feeed8
Create Date: 2026-09-14 17:21:45.489348

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '5b61fec6965e'
down_revision: Union[str, Sequence[str], None] = 'edf5f5feeed8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "ALTER SEQUENCE items_id_seq RENAME TO applications_id_seq"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "ALTER SEQUENCE applications_id_seq RENAME TO items_id_seq"
    )
