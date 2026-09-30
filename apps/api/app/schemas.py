from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.constants import PERFIS, STATUS_MAQUINA

Perfil = Literal["administrador", "pcp", "supervisor", "operador", "qualidade"]
StatusMaquina = Literal["ativa", "manutencao", "inativa"]

assert set(Perfil.__args__) == set(PERFIS)
assert set(StatusMaquina.__args__) == set(STATUS_MAQUINA)


def _email(value: str) -> str:
    cleaned = value.strip().lower()
    if "@" not in cleaned or cleaned.startswith("@") or cleaned.endswith("@"):
        raise ValueError("Informe um e-mail válido.")
    return cleaned


def _codigo(value: str) -> str:
    cleaned = value.strip().upper()
    if not cleaned:
        raise ValueError("Informe o código.")
    return cleaned


def _texto(value: str) -> str:
    cleaned = " ".join(value.split())
    if len(cleaned) < 2:
        raise ValueError("Informe ao menos 2 caracteres.")
    return cleaned


# ---------- Acesso ----------


class SetupIn(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=180)
    senha: str = Field(min_length=8, max_length=72)

    _valida_email = field_validator("email")(_email)


class LoginIn(BaseModel):
    email: str
    senha: str = Field(min_length=1, max_length=72)

    _valida_email = field_validator("email")(_email)


class TrocaSenhaIn(BaseModel):
    senha_atual: str = Field(min_length=1, max_length=72)
    nova_senha: str = Field(min_length=8, max_length=72)


class MenuItem(BaseModel):
    tela: str
    label: str
    href: str


class UsuarioOut(BaseModel):
    id: str
    nome: str
    email: str
    perfil: str
    perfil_label: str
    ativo: bool
    telas: list[str]
    acoes: list[str]
    menu: list[MenuItem]
    inicio: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UsuarioOut


class UsuarioCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=180)
    senha: str = Field(min_length=8, max_length=72)
    perfil: Perfil

    _valida_email = field_validator("email")(_email)


class UsuarioUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=120)
    senha: str | None = Field(default=None, min_length=8, max_length=72)
    perfil: Perfil | None = None
    ativo: bool | None = None


# ---------- Cadastros ----------


class SetorIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=20)
    nome: str = Field(min_length=2, max_length=80)
    ordem: int = Field(default=0, ge=0, le=99)
    ativo: bool = True

    _valida_codigo = field_validator("codigo")(_codigo)
    _valida_nome = field_validator("nome")(_texto)


class SetorOut(BaseModel):
    id: str
    codigo: str
    nome: str
    ordem: int
    ativo: bool
    maquinas: int = 0


class MaquinaIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=20)
    nome: str = Field(min_length=2, max_length=120)
    setor_id: str
    ciclo_padrao_seg: float = Field(gt=0, le=86400)
    status: StatusMaquina = "ativa"
    observacao: str | None = Field(default=None, max_length=500)

    _valida_codigo = field_validator("codigo")(_codigo)
    _valida_nome = field_validator("nome")(_texto)


class MaquinaUpdate(BaseModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=20)
    nome: str | None = Field(default=None, min_length=2, max_length=120)
    setor_id: str | None = None
    ciclo_padrao_seg: float | None = Field(default=None, gt=0, le=86400)
    status: StatusMaquina | None = None
    observacao: str | None = Field(default=None, max_length=500)

    @field_validator("codigo")
    @classmethod
    def valida_codigo(cls, value: str | None) -> str | None:
        return None if value is None else _codigo(value)

    @field_validator("nome")
    @classmethod
    def valida_nome(cls, value: str | None) -> str | None:
        return None if value is None else _texto(value)


class RoteiroIn(BaseModel):
    setor_id: str
    operacao: str = Field(min_length=2, max_length=160)
    tempo_padrao_seg: float | None = Field(default=None, gt=0, le=86400)

    _valida_operacao = field_validator("operacao")(_texto)


class ProdutoIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=30)
    descricao: str = Field(min_length=2, max_length=160)
    unidade: str = Field(default="PC", min_length=1, max_length=6)
    comprimento_mm: int | None = Field(default=None, gt=0, le=20000)
    ativo: bool = True
    roteiro: list[RoteiroIn] = Field(min_length=1, max_length=20)

    _valida_codigo = field_validator("codigo")(_codigo)
    _valida_descricao = field_validator("descricao")(_texto)
    _valida_unidade = field_validator("unidade")(_codigo)


class RoteiroOut(BaseModel):
    sequencia: int
    setor_id: str
    setor_nome: str
    operacao: str
    tempo_padrao_seg: float | None


class ProdutoOut(BaseModel):
    id: str
    codigo: str
    descricao: str
    unidade: str
    comprimento_mm: int | None
    ativo: bool
    roteiro: list[RoteiroOut]


Prioridade = Literal["baixa", "normal", "alta", "urgente"]


class OrdemIn(BaseModel):
    produto_id: str
    quantidade: int = Field(gt=0, le=1_000_000)
    prazo: date | None = None
    prioridade: Prioridade = "normal"
    observacao: str | None = Field(default=None, max_length=500)


class MaquinaEscolhaIn(BaseModel):
    maquina_id: str | None = None


class MotivoIn(BaseModel):
    motivo: str = Field(min_length=3, max_length=300)

    _valida_motivo = field_validator("motivo")(_texto)


class OrdemEtapaOut(BaseModel):
    sequencia: int
    setor_id: str
    setor_nome: str
    operacao: str
    status: str
    status_label: str
    maquina_id: str | None
    maquina_codigo: str | None
    iniciada_em: datetime | None
    concluida_em: datetime | None


class OrdemOut(BaseModel):
    id: str
    numero: int
    produto_id: str
    produto_codigo: str
    produto_descricao: str
    comprimento_mm: int | None
    unidade: str
    quantidade: int
    prazo: date | None
    prioridade: str
    status: str
    status_label: str
    atrasada: bool
    motivo_pausa: str | None
    observacao: str | None
    etapa_atual: int | None
    total_etapas: int
    etapas: list[OrdemEtapaOut]
    criado_em: datetime
    concluida_em: datetime | None


class OrdemEventoOut(BaseModel):
    em: datetime
    tipo: str
    descricao: str
    usuario_nome: str | None


class OrdemDetalheOut(OrdemOut):
    eventos: list[OrdemEventoOut]


class MaquinaOut(BaseModel):
    id: str
    codigo: str
    nome: str
    setor_id: str
    setor_nome: str
    ciclo_padrao_seg: float
    pecas_por_hora: float
    status: str
    status_label: str
    recebe_ordem: bool
    observacao: str | None
    atualizado_em: datetime


# ---------- Equipe ----------


class TurnoIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=10)
    nome: str = Field(min_length=2, max_length=60)
    inicio: time
    fim: time
    ativo: bool = True

    _valida_codigo = field_validator("codigo")(_codigo)
    _valida_nome = field_validator("nome")(_texto)

    @field_validator("inicio", "fim")
    @classmethod
    def sem_segundos(cls, value: time) -> time:
        return value.replace(second=0, microsecond=0, tzinfo=None)


class TurnoOut(BaseModel):
    id: str
    codigo: str
    nome: str
    inicio: str
    fim: str
    duracao_min: int
    vira_meia_noite: bool
    ativo: bool
    operadores: int = 0


class OperadorIn(BaseModel):
    matricula: str = Field(min_length=1, max_length=20)
    nome: str = Field(min_length=2, max_length=120)
    turno_id: str
    setor_id: str
    ativo: bool = True

    _valida_matricula = field_validator("matricula")(_codigo)
    _valida_nome = field_validator("nome")(_texto)


class OperadorOut(BaseModel):
    id: str
    matricula: str
    nome: str
    turno_id: str
    turno_nome: str
    turno_horario: str
    setor_id: str
    setor_nome: str
    ativo: bool
