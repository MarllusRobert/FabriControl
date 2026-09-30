"""Turnos de trabalho e operadores

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-30
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "turnos",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("codigo", sa.String(10), nullable=False, unique=True),
        sa.Column("nome", sa.String(60), nullable=False, unique=True),
        sa.Column("inicio", sa.Time(), nullable=False),
        sa.Column("fim", sa.Time(), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "operadores",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("matricula", sa.String(20), nullable=False, unique=True),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("turno_id", sa.String(36), sa.ForeignKey("turnos.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("setor_id", sa.String(36), sa.ForeignKey("setores.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_operadores_turno_id", "operadores", ["turno_id"])
    op.create_index("ix_operadores_setor_id", "operadores", ["setor_id"])


def downgrade() -> None:
    op.drop_table("operadores")
    op.drop_table("turnos")
