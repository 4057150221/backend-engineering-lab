"""replace items with applications

Revision ID: edf5f5feeed8
Revises: ba7612f262f6
Create Date: 2026-09-14 16:30:04.639408

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'edf5f5feeed8'
down_revision: Union[str, Sequence[str], None] = 'ba7612f262f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table("items", "applications")
    op.alter_column(
        table_name="applications",
        column_name="title",
        new_column_name="company",
        existing_type=sa.String(length=100),
        existing_nullable=False,
    )
    op.alter_column(
        table_name="applications",
        column_name="description",
        new_column_name="notes",
        existing_type=sa.String(length=300),
        type_=sa.String(length=500),
        existing_nullable=True,
    )

    op.add_column(
        "applications",
        sa.Column(
            "position",
            sa.String(length=100),
            nullable=False,
        ),
    )
    op.add_column(
        "applications",
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'saved'"),
        ),
    )
    op.add_column(
        "applications",
        sa.Column(
            "applied_at",
            sa.Date(),
            nullable=True,
        ),
    )

    op.add_column(
        "applications",
        sa.Column(
            "owner_id",
            sa.Integer(),
            nullable=False,
        ),
    )

    op.create_foreign_key(
        constraint_name="fk_applications_owner_id_users",
        source_table="applications",
        referent_table="users",
        local_cols=["owner_id"],
        remote_cols=["id"],
    )
    op.create_index(
        index_name="ix_applications_owner_id",
        table_name="applications",
        columns=["owner_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        index_name="ix_applications_owner_id",
        table_name="applications",
    )

    op.drop_constraint(
        constraint_name="fk_applications_owner_id_users",
        table_name="applications",
        type_="foreignkey",
    )

    op.drop_column("applications", "owner_id")
    op.drop_column("applications", "applied_at")
    op.drop_column("applications", "status")
    op.drop_column("applications", "position")

    op.alter_column(
        table_name="applications",
        column_name="notes",
        new_column_name="description",
        existing_type=sa.String(length=500),
        type_=sa.String(length=300),
        existing_nullable=True,
    )
    op.alter_column(
        table_name="applications",
        column_name="company",
        new_column_name="title",
        existing_type=sa.String(length=100),
        existing_nullable=False,
    )
    op.rename_table("applications", "items")
