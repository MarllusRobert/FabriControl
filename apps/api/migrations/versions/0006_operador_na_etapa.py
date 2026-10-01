"""Operador que executou cada etapa da ordem

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-30
"""
import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ordem_etapas",
        sa.Column("operador_id", sa.String(36), sa.ForeignKey("operadores.id", ondelete="SET NULL"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ordem_etapas", "operador_id")
