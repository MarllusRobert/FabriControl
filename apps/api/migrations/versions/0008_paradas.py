"""Paradas de máquina

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-30
"""
import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paradas",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("maquina_id", sa.String(36), sa.ForeignKey("maquinas.id", ondelete="RESTRICT"), nullable=False),
        sa.Column(
            "motivo_parada_id", sa.String(36), sa.ForeignKey("motivos_parada.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("operador_id", sa.String(36), sa.ForeignKey("operadores.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ordem_id", sa.String(36), sa.ForeignKey("ordens_producao.id", ondelete="SET NULL"), nullable=True),
        sa.Column("usuario_id", sa.String(36), sa.ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True),
        sa.Column("inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fim", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observacao", sa.String(300), nullable=True),
    )
    op.create_index("ix_paradas_maquina_id", "paradas", ["maquina_id"])
    op.create_index("ix_paradas_inicio", "paradas", ["inicio"])
    # Uma máquina só pode ter uma parada em aberto.
    op.create_index("uq_paradas_maquina_aberta", "paradas", ["maquina_id"], unique=True, postgresql_where=sa.text("fim IS NULL"))


def downgrade() -> None:
    op.drop_table("paradas")
