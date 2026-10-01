"""Apontamento de peças boas e refugo por etapa

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-30
"""
import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "apontamentos",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("etapa_id", sa.String(36), sa.ForeignKey("ordem_etapas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("maquina_id", sa.String(36), sa.ForeignKey("maquinas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("operador_id", sa.String(36), sa.ForeignKey("operadores.id", ondelete="SET NULL"), nullable=True),
        sa.Column("usuario_id", sa.String(36), sa.ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True),
        sa.Column("boas", sa.Integer(), nullable=False),
        sa.Column("refugo", sa.Integer(), nullable=False),
        sa.Column(
            "motivo_refugo_id", sa.String(36), sa.ForeignKey("motivos_refugo.id", ondelete="RESTRICT"), nullable=True
        ),
        sa.Column("em", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_apontamentos_etapa_id", "apontamentos", ["etapa_id"])
    op.create_index("ix_apontamentos_em", "apontamentos", ["em"])


def downgrade() -> None:
    op.drop_table("apontamentos")
