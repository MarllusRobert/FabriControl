"""Produtos com roteiro de fabricação e posição do setor no fluxo

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-30
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("setores", sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"))

    op.create_table(
        "produtos",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("codigo", sa.String(30), nullable=False, unique=True),
        sa.Column("descricao", sa.String(160), nullable=False),
        sa.Column("unidade", sa.String(6), nullable=False),
        sa.Column("comprimento_mm", sa.Integer(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "roteiro_etapas",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("produto_id", sa.String(36), sa.ForeignKey("produtos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequencia", sa.Integer(), nullable=False),
        sa.Column("setor_id", sa.String(36), sa.ForeignKey("setores.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("operacao", sa.String(160), nullable=False),
        sa.Column("tempo_padrao_seg", sa.Numeric(10, 2), nullable=True),
        sa.UniqueConstraint("produto_id", "sequencia", name="uq_roteiro_produto_sequencia"),
    )
    op.create_index("ix_roteiro_etapas_produto_id", "roteiro_etapas", ["produto_id"])


def downgrade() -> None:
    op.drop_table("roteiro_etapas")
    op.drop_table("produtos")
    op.drop_column("setores", "ordem")
