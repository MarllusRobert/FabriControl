import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import PERFIS
from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(120))
    versao_senha: Mapped[int] = mapped_column(Integer, default=1)
    perfil: Mapped[str] = mapped_column(String(20))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    @property
    def telas(self) -> list[str]:
        return list(PERFIS[self.perfil]["telas"])

    @property
    def acoes(self) -> list[str]:
        return list(PERFIS[self.perfil]["acoes"])


class Setor(Base):
    """Centro de trabalho (ex.: Corte, Dobra, Solda, Pintura)."""

    __tablename__ = "setores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    nome: Mapped[str] = mapped_column(String(80), unique=True)
    # Posição no fluxo da fábrica; define a ordem das colunas do Kanban.
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Maquina(Base):
    __tablename__ = "maquinas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    nome: Mapped[str] = mapped_column(String(120))
    setor_id: Mapped[str] = mapped_column(String(36), ForeignKey("setores.id", ondelete="RESTRICT"), index=True)
    # Tempo padrão para produzir uma peça; base do cálculo de performance do OEE.
    ciclo_padrao_seg: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(20), default="ativa", index=True)
    observacao: Mapped[str | None] = mapped_column(String(500), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    setor: Mapped[Setor] = relationship(lazy="joined")


class Produto(Base):
    __tablename__ = "produtos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    codigo: Mapped[str] = mapped_column(String(30), unique=True)
    descricao: Mapped[str] = mapped_column(String(160))
    unidade: Mapped[str] = mapped_column(String(6), default="PC")
    # Comprimento da chapa cortada no desbobinador (ex.: 3000 ou 6000 mm).
    comprimento_mm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    roteiro: Mapped[list["RoteiroEtapa"]] = relationship(
        order_by="RoteiroEtapa.sequencia", cascade="all, delete-orphan", lazy="selectin"
    )


class RoteiroEtapa(Base):
    """Uma operação do caminho de fabricação do produto (ex.: 2 - Guilhotina: cortar a tira)."""

    __tablename__ = "roteiro_etapas"
    __table_args__ = (UniqueConstraint("produto_id", "sequencia", name="uq_roteiro_produto_sequencia"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    produto_id: Mapped[str] = mapped_column(String(36), ForeignKey("produtos.id", ondelete="CASCADE"), index=True)
    sequencia: Mapped[int] = mapped_column(Integer)
    setor_id: Mapped[str] = mapped_column(String(36), ForeignKey("setores.id", ondelete="RESTRICT"))
    operacao: Mapped[str] = mapped_column(String(160))
    tempo_padrao_seg: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    setor: Mapped[Setor] = relationship(lazy="joined")


class OrdemProducao(Base):
    __tablename__ = "ordens_producao"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    numero: Mapped[int] = mapped_column(Integer, unique=True)
    produto_id: Mapped[str] = mapped_column(String(36), ForeignKey("produtos.id", ondelete="RESTRICT"), index=True)
    quantidade: Mapped[int] = mapped_column(Integer)
    prazo: Mapped[date | None] = mapped_column(Date, nullable=True)
    prioridade: Mapped[str] = mapped_column(String(10), default="normal")
    status: Mapped[str] = mapped_column(String(15), default="planejada", index=True)
    motivo_pausa: Mapped[str | None] = mapped_column(String(300), nullable=True)
    observacao: Mapped[str | None] = mapped_column(String(500), nullable=True)
    criado_por_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    concluida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    produto: Mapped[Produto] = relationship(lazy="joined")
    # A ordem guarda a própria cópia do roteiro: mudar o produto depois não altera ordens já criadas.
    etapas: Mapped[list["OrdemEtapa"]] = relationship(
        order_by="OrdemEtapa.sequencia", cascade="all, delete-orphan", lazy="selectin"
    )
    eventos: Mapped[list["OrdemEvento"]] = relationship(
        order_by="OrdemEvento.em", cascade="all, delete-orphan", lazy="select"
    )

    @property
    def etapa_atual(self) -> "OrdemEtapa | None":
        return next((e for e in self.etapas if e.status != "concluida"), None)


class OrdemEtapa(Base):
    __tablename__ = "ordem_etapas"
    __table_args__ = (UniqueConstraint("ordem_id", "sequencia", name="uq_ordem_etapa_sequencia"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    ordem_id: Mapped[str] = mapped_column(String(36), ForeignKey("ordens_producao.id", ondelete="CASCADE"), index=True)
    sequencia: Mapped[int] = mapped_column(Integer)
    setor_id: Mapped[str] = mapped_column(String(36), ForeignKey("setores.id", ondelete="RESTRICT"))
    operacao: Mapped[str] = mapped_column(String(160))
    tempo_padrao_seg: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    # aguardando → na_fila → em_andamento → concluida
    status: Mapped[str] = mapped_column(String(15), default="aguardando")
    maquina_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("maquinas.id", ondelete="SET NULL"), nullable=True)
    iniciada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    concluida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    setor: Mapped[Setor] = relationship(lazy="joined")
    maquina: Mapped[Maquina | None] = relationship(lazy="joined")


class OrdemEvento(Base):
    """Histórico da ordem: quem fez o quê e quando (rastreabilidade)."""

    __tablename__ = "ordem_eventos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    ordem_id: Mapped[str] = mapped_column(String(36), ForeignKey("ordens_producao.id", ondelete="CASCADE"), index=True)
    em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    usuario_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    tipo: Mapped[str] = mapped_column(String(20))
    descricao: Mapped[str] = mapped_column(String(300))

    usuario: Mapped[Usuario | None] = relationship(lazy="joined")
