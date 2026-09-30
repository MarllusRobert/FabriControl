from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.constants import CATEGORIAS_REFUGO, TIPOS_PARADA
from app.db import get_db
from app.deps import require_acao, require_tela
from app.models import MotivoParada, MotivoRefugo, Usuario
from app.schemas import (
    CategoriaRefugo,
    MotivoParadaIn,
    MotivoParadaOut,
    MotivoRefugoIn,
    MotivoRefugoOut,
    OpcaoOut,
    OpcoesMotivosOut,
    TipoParada,
)

router = APIRouter(prefix="/motivos", tags=["motivos"])
ver = require_tela("motivos")
editar = require_acao("gerenciar_equipe")


def _parada_out(m: MotivoParada) -> MotivoParadaOut:
    return MotivoParadaOut(
        id=m.id,
        codigo=m.codigo,
        descricao=m.descricao,
        tipo=m.tipo,
        tipo_label=TIPOS_PARADA[m.tipo],
        planejada=m.tipo == "planejada",
        ativo=m.ativo,
    )


def _refugo_out(m: MotivoRefugo) -> MotivoRefugoOut:
    return MotivoRefugoOut(
        id=m.id,
        codigo=m.codigo,
        descricao=m.descricao,
        categoria=m.categoria,
        categoria_label=CATEGORIAS_REFUGO[m.categoria],
        ativo=m.ativo,
    )


def _livre(db: Session, modelo, codigo: str, descricao: str, ignorar_id: str | None = None) -> None:
    filtro = or_(modelo.codigo == codigo, func.lower(modelo.descricao) == descricao.lower())
    consulta = select(modelo.id).where(filtro)
    if ignorar_id:
        consulta = consulta.where(modelo.id != ignorar_id)
    if db.scalar(consulta):
        raise HTTPException(status_code=409, detail="Já existe um motivo com este código ou descrição.")


@router.get("/opcoes", response_model=OpcoesMotivosOut)
def opcoes(_user: Usuario = Depends(ver)) -> OpcoesMotivosOut:
    return OpcoesMotivosOut(
        tipos_parada=[OpcaoOut(valor=v, label=l) for v, l in TIPOS_PARADA.items()],
        categorias_refugo=[OpcaoOut(valor=v, label=l) for v, l in CATEGORIAS_REFUGO.items()],
    )


# ---------- Parada ----------


@router.get("/parada", response_model=list[MotivoParadaOut])
def listar_paradas(
    tipo: TipoParada | None = None,
    ativos: bool = False,
    _user: Usuario = Depends(ver),
    db: Session = Depends(get_db),
) -> list[MotivoParadaOut]:
    consulta = select(MotivoParada)
    if tipo:
        consulta = consulta.where(MotivoParada.tipo == tipo)
    if ativos:
        consulta = consulta.where(MotivoParada.ativo.is_(True))
    motivos = db.scalars(consulta.order_by(MotivoParada.tipo.desc(), MotivoParada.codigo)).all()
    return [_parada_out(m) for m in motivos]


@router.post("/parada", response_model=MotivoParadaOut, status_code=201)
def criar_parada(payload: MotivoParadaIn, _user: Usuario = Depends(editar), db: Session = Depends(get_db)) -> MotivoParadaOut:
    _livre(db, MotivoParada, payload.codigo, payload.descricao)
    motivo = MotivoParada(**payload.model_dump())
    db.add(motivo)
    db.commit()
    return _parada_out(motivo)


@router.put("/parada/{motivo_id}", response_model=MotivoParadaOut)
def atualizar_parada(
    motivo_id: str, payload: MotivoParadaIn, _user: Usuario = Depends(editar), db: Session = Depends(get_db)
) -> MotivoParadaOut:
    motivo = db.get(MotivoParada, motivo_id)
    if motivo is None:
        raise HTTPException(status_code=404, detail="Motivo de parada não encontrado.")
    _livre(db, MotivoParada, payload.codigo, payload.descricao, ignorar_id=motivo.id)
    for campo, valor in payload.model_dump().items():
        setattr(motivo, campo, valor)
    db.commit()
    return _parada_out(motivo)


# ---------- Refugo ----------


@router.get("/refugo", response_model=list[MotivoRefugoOut])
def listar_refugos(
    categoria: CategoriaRefugo | None = None,
    ativos: bool = False,
    _user: Usuario = Depends(ver),
    db: Session = Depends(get_db),
) -> list[MotivoRefugoOut]:
    consulta = select(MotivoRefugo)
    if categoria:
        consulta = consulta.where(MotivoRefugo.categoria == categoria)
    if ativos:
        consulta = consulta.where(MotivoRefugo.ativo.is_(True))
    motivos = db.scalars(consulta.order_by(MotivoRefugo.categoria, MotivoRefugo.codigo)).all()
    return [_refugo_out(m) for m in motivos]


@router.post("/refugo", response_model=MotivoRefugoOut, status_code=201)
def criar_refugo(payload: MotivoRefugoIn, _user: Usuario = Depends(editar), db: Session = Depends(get_db)) -> MotivoRefugoOut:
    _livre(db, MotivoRefugo, payload.codigo, payload.descricao)
    motivo = MotivoRefugo(**payload.model_dump())
    db.add(motivo)
    db.commit()
    return _refugo_out(motivo)


@router.put("/refugo/{motivo_id}", response_model=MotivoRefugoOut)
def atualizar_refugo(
    motivo_id: str, payload: MotivoRefugoIn, _user: Usuario = Depends(editar), db: Session = Depends(get_db)
) -> MotivoRefugoOut:
    motivo = db.get(MotivoRefugo, motivo_id)
    if motivo is None:
        raise HTTPException(status_code=404, detail="Motivo de refugo não encontrado.")
    _livre(db, MotivoRefugo, payload.codigo, payload.descricao, ignorar_id=motivo.id)
    for campo, valor in payload.model_dump().items():
        setattr(motivo, campo, valor)
    db.commit()
    return _refugo_out(motivo)
