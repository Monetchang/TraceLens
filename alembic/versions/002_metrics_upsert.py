"""metrics upsert unique constraint

Revision ID: 002
Revises: 001
Create Date: 2026-03-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("metrics", sa.Column("similarity_mode", sa.String(50), nullable=False, server_default=""))
    conn = op.get_bind()
    conn.execute(sa.text(
        "DELETE FROM metrics a USING metrics b "
        "WHERE a.ctid < b.ctid AND a.run_id = b.run_id AND a.name = b.name AND a.similarity_mode = b.similarity_mode"
    ))
    op.create_unique_constraint("uq_metrics_run_name_mode", "metrics", ["run_id", "name", "similarity_mode"])


def downgrade() -> None:
    op.drop_constraint("uq_metrics_run_name_mode", "metrics", type_="unique")
    op.drop_column("metrics", "similarity_mode")
