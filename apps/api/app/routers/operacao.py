from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import ORDEM_ABERTA
from app.db import get_db
from app.deps import require_acao, require_tela
from app.models import Maquina, Operador, OrdemEtapa, OrdemProducao, Usuario
from app.present import etapa_fila_out, maquina_out, operador_out
from app.routers.kanban import PESO_PRIORIDADE
from app.routers.ordens import executar_conclusao, executar_inicio
from app.schemas import OperacaoIn, OperadorOut, PainelMaquinaOut

router = APIRouter(prefix="/operacao", tags=["operacao"])
ver = require_tela("operacao")
movimentar = require_acao("movimentar_producao")

Par = tuple[OrdemProducao, OrdemEtapa]
_NUNCA = datetime.max.replace(tzinfo=timezone.utc)


def _maquina(db: Session, maquina_id: str) -> Maquina:
    maquina = db.get(Maquina, maquina_id)
    if maquina is None:
        raise HTTPException(status_code=404, detail="Máquina não encontrada.")
    return maquina


def _operador(db: Session, operador_id: str) -> Operador:
    operador = db.get(Operador, operador_id)
    if operador is None or not operador.ativo:
        raise HTTPException(status_code=400, detail="Operador não encontrado ou inativo; entre de novo com a matrícula.")
    return operador


def _estado(db: Session, maquina: Maquina) -> tuple[Par | None, list[Par]]:
    """Etapa rodando na máquina e fila de etapas do centro dela que podem começar ali."""
    abertas = db.scalars(select(OrdemProducao).where(OrdemProducao.status.in_(ORDEM_ABERTA))).all()
    atual: Par | None = None
    fila: list[Par] = []
    for ordem in abertas:
        etapa = ordem.etapa_atual
        if etapa is None or etapa.setor_id != maquina.setor_id:
            continue
        if etapa.status == "em_andamento" and etapa.maquina_id == maquina.id:
            if atual is None or (etapa.iniciada_em or _NUNCA) < (atual[1].iniciada_em or _NUNCA):
                atual = (ordem, etapa)
        elif etapa.status == "na_fila" and ordem.status != "pausada" and etapa.maquina_id in (None, maquina.id):
            fila.append((ordem, etapa))
    fila.sort(key=lambda p: (PESO_PRIORIDADE.get(p[0].prioridade, 9), p[0].prazo or date.max, p[0].numero))
    return atual, fila


def _painel(db: Session, maquina: Maquina) -> PainelMaquinaOut:
    atual, fila = _estado(db, maquina)
    return PainelMaquinaOut(
        maquina=maquina_out(maquina),
        atual=etapa_fila_out(*atual, maquina) if atual else None,
        fila=[etapa_fila_out(o, e, maquina) for o, e in fila],
        atualizado_em=datetime.now(timezone.utc),
    )


@router.get("/operador", response_model=OperadorOut)
def identificar(
    matricula: str = Query(min_length=1, max_length=20), _user: Usuario = Depends(ver), db: Session = Depends(get_db)
) -> OperadorOut:
    operador = db.scalar(select(Operador).where(Operador.matricula == matricula.strip().upper()))
    if operador is None or not operador.ativo:
        raise HTTPException(status_code=404, detail="Matrícula não encontrada ou operador inativo.")
    return operador_out(operador)


@router.get("/maquinas/{maquina_id}", response_model=PainelMaquinaOut)
def painel(maquina_id: str, _user: Usuario = Depends(ver), db: Session = Depends(get_db)) -> PainelMaquinaOut:
    return _painel(db, _maquina(db, maquina_id))


@router.post("/maquinas/{maquina_id}/iniciar", response_model=PainelMaquinaOut)
def iniciar(
    maquina_id: str, payload: OperacaoIn, user: Usuario = Depends(movimentar), db: Session = Depends(get_db)
) -> PainelMaquinaOut:
    maquina = _maquina(db, maquina_id)
    operador = _operador(db, payload.operador_id)
    if not payload.ordem_id:
        raise HTTPException(status_code=400, detail="Escolha a ordem da fila.")
    atual, fila = _estado(db, maquina)
    if atual is not None:
        raise HTTPException(
            status_code=400,
            detail=f"A {maquina.codigo} já está com a OP {atual[0].numero} em andamento; finalize antes de iniciar outra.",
        )
    par = next((p for p in fila if p[0].id == payload.ordem_id), None)
    if par is None:
        raise HTTPException(status_code=400, detail=f"Esta OP não está na fila da {maquina.codigo}.")
    executar_inicio(db, par[0], user, maquina.id, operador)
    db.commit()
    return _painel(db, maquina)


@router.post("/maquinas/{maquina_id}/finalizar", response_model=PainelMaquinaOut)
def finalizar(
    maquina_id: str, payload: OperacaoIn, user: Usuario = Depends(movimentar), db: Session = Depends(get_db)
) -> PainelMaquinaOut:
    maquina = _maquina(db, maquina_id)
    operador = _operador(db, payload.operador_id)
    atual, _fila = _estado(db, maquina)
    if atual is None:
        raise HTTPException(status_code=400, detail=f"Nenhuma operação em andamento na {maquina.codigo}.")
    executar_conclusao(db, atual[0], user, maquina.id, operador)
    db.commit()
    return _painel(db, maquina)
