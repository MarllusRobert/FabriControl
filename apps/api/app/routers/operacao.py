from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import ORDEM_ABERTA
from app.db import get_db
from app.deps import require_acao, require_tela
from app.models import (
    Apontamento,
    Maquina,
    MotivoParada,
    MotivoRefugo,
    Operador,
    OrdemEtapa,
    OrdemEvento,
    OrdemProducao,
    Parada,
    Usuario,
)
from app.present import etapa_fila_out, maquina_out, operador_out, parada_out
from app.routers.kanban import PESO_PRIORIDADE
from app.routers.motivos import parada_out as parada_motivo_out
from app.routers.motivos import refugo_out
from app.routers.ordens import executar_conclusao, executar_inicio
from app.schemas import (
    ApontamentoIn,
    MotivoParadaOut,
    MotivoRefugoOut,
    OperacaoIn,
    OperadorOut,
    PainelMaquinaOut,
    PararIn,
)

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


def _parada_aberta(db: Session, maquina: Maquina) -> Parada | None:
    return db.scalar(select(Parada).where(Parada.maquina_id == maquina.id, Parada.fim.is_(None)))


def _painel(db: Session, maquina: Maquina) -> PainelMaquinaOut:
    atual, fila = _estado(db, maquina)
    parada = _parada_aberta(db, maquina)
    return PainelMaquinaOut(
        maquina=maquina_out(maquina),
        atual=etapa_fila_out(*atual, maquina) if atual else None,
        fila=[etapa_fila_out(o, e, maquina) for o, e in fila],
        parada=parada_out(parada) if parada else None,
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
    if _parada_aberta(db, maquina) is not None:
        raise HTTPException(status_code=400, detail=f"A {maquina.codigo} está parada; registre a volta antes de iniciar.")
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


@router.get("/motivos-refugo", response_model=list[MotivoRefugoOut])
def motivos_refugo(_user: Usuario = Depends(ver), db: Session = Depends(get_db)) -> list[MotivoRefugoOut]:
    motivos = db.scalars(
        select(MotivoRefugo).where(MotivoRefugo.ativo.is_(True)).order_by(MotivoRefugo.categoria, MotivoRefugo.descricao)
    ).all()
    return [refugo_out(m) for m in motivos]


@router.post("/maquinas/{maquina_id}/apontar", response_model=PainelMaquinaOut)
def apontar(
    maquina_id: str, payload: ApontamentoIn, user: Usuario = Depends(movimentar), db: Session = Depends(get_db)
) -> PainelMaquinaOut:
    maquina = _maquina(db, maquina_id)
    operador = _operador(db, payload.operador_id)
    atual, _fila = _estado(db, maquina)
    if atual is None:
        raise HTTPException(status_code=400, detail=f"Nenhuma operação em andamento na {maquina.codigo}.")
    ordem, etapa = atual
    if payload.boas + payload.refugo == 0:
        raise HTTPException(status_code=400, detail="Informe as peças boas ou o refugo.")
    motivo = None
    if payload.refugo:
        motivo = db.get(MotivoRefugo, payload.motivo_refugo_id) if payload.motivo_refugo_id else None
        if motivo is None or not motivo.ativo:
            raise HTTPException(status_code=400, detail="Refugo exige o motivo.")
    saldo = ordem.saldo(etapa)
    if payload.boas + payload.refugo > saldo:
        raise HTTPException(
            status_code=400,
            detail=f"Só restam {saldo} {ordem.produto.unidade} nesta etapa; confira a contagem.",
        )
    etapa.apontamentos.append(
        Apontamento(
            maquina_id=maquina.id,
            operador_id=operador.id,
            usuario_id=user.id,
            boas=payload.boas,
            refugo=payload.refugo,
            motivo_refugo_id=motivo.id if motivo else None,
        )
    )
    partes = [f"{payload.boas} boas"] if payload.boas else []
    if motivo:
        partes.append(f"{payload.refugo} refugo ({motivo.descricao})")
    db.add(
        OrdemEvento(
            ordem_id=ordem.id,
            usuario_id=user.id,
            tipo="apontamento",
            descricao=f"Etapa {etapa.sequencia}: apontadas {' e '.join(partes)} na {maquina.codigo} por {operador.nome}.",
        )
    )
    db.commit()
    return _painel(db, maquina)


@router.get("/motivos-parada", response_model=list[MotivoParadaOut])
def motivos_parada(_user: Usuario = Depends(ver), db: Session = Depends(get_db)) -> list[MotivoParadaOut]:
    motivos = db.scalars(
        select(MotivoParada).where(MotivoParada.ativo.is_(True)).order_by(MotivoParada.tipo.desc(), MotivoParada.descricao)
    ).all()
    return [parada_motivo_out(m) for m in motivos]


@router.post("/maquinas/{maquina_id}/parar", response_model=PainelMaquinaOut)
def parar(
    maquina_id: str, payload: PararIn, user: Usuario = Depends(movimentar), db: Session = Depends(get_db)
) -> PainelMaquinaOut:
    maquina = _maquina(db, maquina_id)
    operador = _operador(db, payload.operador_id)
    aberta = _parada_aberta(db, maquina)
    if aberta is not None:
        raise HTTPException(
            status_code=400,
            detail=f"A {maquina.codigo} já está parada ({aberta.motivo.descricao}); registre a volta antes.",
        )
    motivo = db.get(MotivoParada, payload.motivo_parada_id)
    if motivo is None or not motivo.ativo:
        raise HTTPException(status_code=400, detail="Escolha o motivo da parada.")
    atual, _fila = _estado(db, maquina)
    ordem = atual[0] if atual and atual[0].status in ("liberada", "em_producao") else None
    if ordem is not None:
        ordem.status = "pausada"
        ordem.motivo_pausa = f"Máquina parada: {motivo.descricao}"
        db.add(
            OrdemEvento(
                ordem_id=ordem.id,
                usuario_id=user.id,
                tipo="pausada",
                descricao=f"Pausada: a {maquina.codigo} parou por {motivo.descricao.lower()} ({operador.nome}).",
            )
        )
    db.add(
        Parada(
            maquina_id=maquina.id,
            motivo_parada_id=motivo.id,
            operador_id=operador.id,
            ordem_id=ordem.id if ordem else None,
            usuario_id=user.id,
            observacao=(payload.observacao or "").strip() or None,
        )
    )
    db.commit()
    return _painel(db, maquina)


@router.post("/maquinas/{maquina_id}/voltar", response_model=PainelMaquinaOut)
def voltar(
    maquina_id: str, payload: OperacaoIn, user: Usuario = Depends(movimentar), db: Session = Depends(get_db)
) -> PainelMaquinaOut:
    maquina = _maquina(db, maquina_id)
    operador = _operador(db, payload.operador_id)
    parada = _parada_aberta(db, maquina)
    if parada is None:
        raise HTTPException(status_code=400, detail=f"A {maquina.codigo} não está parada.")
    parada.fim = datetime.now(timezone.utc)
    ordem = parada.ordem
    if ordem is not None and ordem.status == "pausada":
        iniciou = any(e.status in ("em_andamento", "concluida") for e in ordem.etapas)
        ordem.status = "em_producao" if iniciou else "liberada"
        ordem.motivo_pausa = None
        minutos = round((parada.fim - parada.inicio).total_seconds() / 60)
        db.add(
            OrdemEvento(
                ordem_id=ordem.id,
                usuario_id=user.id,
                tipo="retomada",
                descricao=f"Produção retomada: a {maquina.codigo} voltou após {minutos} min ({operador.nome}).",
            )
        )
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
