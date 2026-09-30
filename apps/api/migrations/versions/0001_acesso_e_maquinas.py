"""Usuários com perfil, centros de trabalho e máquinas

Revision ID: 0001
Revises:
Create Date: 2026-09-30
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("email", sa.String(180), nullable=False),
        sa.Column("senha_hash", sa.String(120), nullable=False),
        sa.Column("versao_senha", sa.Integer(), nullable=False),
        sa.Column("perfil", sa.String(20), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_usuarios_email", "usuarios", ["email"], unique=True)

    op.create_table(
        "setores",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("codigo", sa.String(20), nullable=False, unique=True),
        sa.Column("nome", sa.String(80), nullable=False, unique=True),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "maquinas",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("codigo", sa.String(20), nullable=False, unique=True),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("setor_id", sa.String(36), sa.ForeignKey("setores.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("ciclo_padrao_seg", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("observacao", sa.String(500), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_maquinas_setor_id", "maquinas", ["setor_id"])
    op.create_index("ix_maquinas_status", "maquinas", ["status"])


def downgrade() -> None:
    op.drop_table("maquinas")
    op.drop_table("setores")
    op.drop_index("ix_usuarios_email", table_name="usuarios")
    op.drop_table("usuarios")
