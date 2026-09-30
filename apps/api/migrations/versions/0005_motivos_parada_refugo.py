"""Motivos de parada e de refugo

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-30
"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "motivos_parada",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("codigo", sa.String(10), nullable=False, unique=True),
        sa.Column("descricao", sa.String(120), nullable=False, unique=True),
        sa.Column("tipo", sa.String(15), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "motivos_refugo",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("codigo", sa.String(10), nullable=False, unique=True),
        sa.Column("descricao", sa.String(120), nullable=False, unique=True),
        sa.Column("categoria", sa.String(20), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("motivos_refugo")
    op.drop_table("motivos_parada")
