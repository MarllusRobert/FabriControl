from datetime import time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_acao, require_tela
from app.models import Operador, Setor, Turno, Usuario
from app.present import horario, operador_out, turno_out
from app.schemas import OperadorIn, OperadorOut, TurnoIn, TurnoOut

router = APIRouter(tags=["equipe"])
ver = require_tela("equipe")
editar = require_acao("gerenciar_equipe")


# ---------- Turnos ----------


def _operadores_ativos(db: Session, turno_id: str) -> int:
    consulta = select(func.count()).select_from(Operador).where(Operador.turno_id == turno_id, Operador.ativo.is_(True))
    return db.scalar(consulta) or 0


def _validar_turno(db: Session, payload: TurnoIn, ignorar_id: str | None = None) -> None:
    if payload.inicio == payload.fim:
        raise HTTPException(status_code=400, detail="O fim do turno precisa ser diferente do início.")
    filtro = or_(Turno.codigo == payload.codigo, func.lower(Turno.nome) == payload.nome.lower())
    consulta = select(Turno.id).where(filtro)
    if ignorar_id:
        consulta = consulta.where(Turno.id != ignorar_id)
    if db.scalar(consulta):
        raise HTTPException(status_code=409, detail="Já existe um turno com este código ou nome.")
    if not payload.ativo:
        return
    # Turnos ativos não podem se sobrepor: cada horário do dia pertence a um turno só.
    novo = Turno(inicio=payload.inicio, fim=payload.fim)
    outros = select(Turno).where(Turno.ativo.is_(True))
    if ignorar_id:
        outros = outros.where(Turno.id != ignorar_id)
    for outro in db.scalars(outros).all():
        if any(a < d and c < b for a, b in novo.faixas() for c, d in outro.faixas()):
            raise HTTPException(
                status_code=409,
                detail=f"Este horário se sobrepõe ao {outro.nome} ({horario(outro)}).",
            )


@router.get("/turnos", response_model=list[TurnoOut])
def listar_turnos(ativos: bool = False, _user: Usuario = Depends(ver), db: Session = Depends(get_db)) -> list[TurnoOut]:
    contagem = dict(
        db.execute(
            select(Operador.turno_id, func.count()).where(Operador.ativo.is_(True)).group_by(Operador.turno_id)
        ).all()
    )
    consulta = select(Turno)
    if ativos:
        consulta = consulta.where(Turno.ativo.is_(True))
    return [turno_out(t, contagem.get(t.id, 0)) for t in db.scalars(consulta.order_by(Turno.inicio)).all()]


@router.get("/turnos/do-horario", response_model=TurnoOut | None)
def turno_do_horario(hora: time, _user: Usuario = Depends(ver), db: Session = Depends(get_db)) -> TurnoOut | None:
    for turno in db.scalars(select(Turno).where(Turno.ativo.is_(True))).all():
        if turno.cobre(hora):
            return turno_out(turno, _operadores_ativos(db, turno.id))
    return None


@router.post("/turnos", response_model=TurnoOut, status_code=201)
def criar_turno(payload: TurnoIn, _user: Usuario = Depends(editar), db: Session = Depends(get_db)) -> TurnoOut:
    _validar_turno(db, payload)
    turno = Turno(codigo=payload.codigo, nome=payload.nome, inicio=payload.inicio, fim=payload.fim, ativo=payload.ativo)
    db.add(turno)
    db.commit()
    return turno_out(turno)


@router.put("/turnos/{turno_id}", response_model=TurnoOut)
def atualizar_turno(
    turno_id: str, payload: TurnoIn, _user: Usuario = Depends(editar), db: Session = Depends(get_db)
) -> TurnoOut:
    turno = db.get(Turno, turno_id)
    if turno is None:
        raise HTTPException(status_code=404, detail="Turno não encontrado.")
    _validar_turno(db, payload, ignorar_id=turno.id)
    ativos = _operadores_ativos(db, turno.id)
    if turno.ativo and not payload.ativo and ativos:
        raise HTTPException(
            status_code=400,
            detail=f"O {turno.nome} tem {ativos} operador(es) ativo(s); mude-os de turno antes de inativar.",
        )
    turno.codigo, turno.nome, turno.ativo = payload.codigo, payload.nome, payload.ativo
    turno.inicio, turno.fim = payload.inicio, payload.fim
    db.commit()
    return turno_out(turno, ativos)


# ---------- Operadores ----------


def _vinculos(db: Session, payload: OperadorIn, atual: Operador | None = None) -> None:
    turno = db.get(Turno, payload.turno_id)
    if turno is None:
        raise HTTPException(status_code=400, detail="Turno não encontrado.")
    if not turno.ativo and (atual is None or atual.turno_id != turno.id):
        raise HTTPException(status_code=400, detail=f"O {turno.nome} está inativo.")
    setor = db.get(Setor, payload.setor_id)
    if setor is None:
        raise HTTPException(status_code=400, detail="Centro de trabalho não encontrado.")
    if not setor.ativo and (atual is None or atual.setor_id != setor.id):
        raise HTTPException(status_code=400, detail=f"O centro {setor.nome} está inativo.")


def _matricula_livre(db: Session, matricula: str, ignorar_id: str | None = None) -> None:
    consulta = select(Operador.id).where(Operador.matricula == matricula)
    if ignorar_id:
        consulta = consulta.where(Operador.id != ignorar_id)
    if db.scalar(consulta):
        raise HTTPException(status_code=409, detail=f"Já existe um operador com a matrícula {matricula}.")


@router.get("/operadores", response_model=list[OperadorOut])
def listar_operadores(
    busca: str | None = Query(default=None, max_length=80),
    turno_id: str | None = None,
    setor_id: str | None = None,
    ativos: bool = False,
    _user: Usuario = Depends(ver),
    db: Session = Depends(get_db),
) -> list[OperadorOut]:
    consulta = select(Operador)
    if busca and busca.strip():
        termo = f"%{busca.strip()}%"
        consulta = consulta.where(or_(Operador.matricula.ilike(termo), Operador.nome.ilike(termo)))
    if turno_id:
        consulta = consulta.where(Operador.turno_id == turno_id)
    if setor_id:
        consulta = consulta.where(Operador.setor_id == setor_id)
    if ativos:
        consulta = consulta.where(Operador.ativo.is_(True))
    return [operador_out(o) for o in db.scalars(consulta.order_by(Operador.nome)).all()]


@router.post("/operadores", response_model=OperadorOut, status_code=201)
def criar_operador(payload: OperadorIn, _user: Usuario = Depends(editar), db: Session = Depends(get_db)) -> OperadorOut:
    _matricula_livre(db, payload.matricula)
    _vinculos(db, payload)
    operador = Operador(**payload.model_dump())
    db.add(operador)
    db.commit()
    db.refresh(operador)
    return operador_out(operador)


@router.put("/operadores/{operador_id}", response_model=OperadorOut)
def atualizar_operador(
    operador_id: str, payload: OperadorIn, _user: Usuario = Depends(editar), db: Session = Depends(get_db)
) -> OperadorOut:
    operador = db.get(Operador, operador_id)
    if operador is None:
        raise HTTPException(status_code=404, detail="Operador não encontrado.")
    _matricula_livre(db, payload.matricula, ignorar_id=operador.id)
    _vinculos(db, payload, atual=operador)
    for campo, valor in payload.model_dump().items():
        setattr(operador, campo, valor)
    db.commit()
    db.refresh(operador)
    return operador_out(operador)
