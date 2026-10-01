"""Posição da etapa na fila do centro de trabalho

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-30
"""
import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ordem_etapas", sa.Column("fila_posicao", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("ordem_etapas", "fila_posicao")
