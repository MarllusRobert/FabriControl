"""Ordens de produção com etapas e histórico

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-30
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ordens_producao",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("numero", sa.Integer(), nullable=False, unique=True),
        sa.Column("produto_id", sa.String(36), sa.ForeignKey("produtos.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.Column("prazo", sa.Date(), nullable=True),
        sa.Column("prioridade", sa.String(10), nullable=False),
        sa.Column("status", sa.String(15), nullable=False),
        sa.Column("motivo_pausa", sa.String(300), nullable=True),
        sa.Column("observacao", sa.String(500), nullable=True),
        sa.Column("criado_por_id", sa.String(36), sa.ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("concluida_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ordens_producao_produto_id", "ordens_producao", ["produto_id"])
    op.create_index("ix_ordens_producao_status", "ordens_producao", ["status"])

    op.create_table(
        "ordem_etapas",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ordem_id", sa.String(36), sa.ForeignKey("ordens_producao.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequencia", sa.Integer(), nullable=False),
        sa.Column("setor_id", sa.String(36), sa.ForeignKey("setores.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("operacao", sa.String(160), nullable=False),
        sa.Column("tempo_padrao_seg", sa.Numeric(10, 2), nullable=True),
        sa.Column("status", sa.String(15), nullable=False),
        sa.Column("maquina_id", sa.String(36), sa.ForeignKey("maquinas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("iniciada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("concluida_em", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("ordem_id", "sequencia", name="uq_ordem_etapa_sequencia"),
    )
    op.create_index("ix_ordem_etapas_ordem_id", "ordem_etapas", ["ordem_id"])

    op.create_table(
        "ordem_eventos",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ordem_id", sa.String(36), sa.ForeignKey("ordens_producao.id", ondelete="CASCADE"), nullable=False),
        sa.Column("em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usuario_id", sa.String(36), sa.ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("descricao", sa.String(300), nullable=False),
    )
    op.create_index("ix_ordem_eventos_ordem_id", "ordem_eventos", ["ordem_id"])


def downgrade() -> None:
    op.drop_table("ordem_eventos")
    op.drop_table("ordem_etapas")
    op.drop_table("ordens_producao")
