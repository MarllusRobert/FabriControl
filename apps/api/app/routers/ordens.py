import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.constants import ORDEM_ABERTA, PRIORIDADES, STATUS_ORDEM, STATUS_RECEBE_ORDEM
from app.db import get_db
from app.deps import require_acao, require_tela
from app.models import Maquina, OrdemEtapa, OrdemEvento, OrdemProducao, Produto, Usuario
from app.present import ordem_detalhe_out, ordem_out
from app.routers.cadastros import maquina_pode_receber_ordem
from app.schemas import MaquinaEscolhaIn, MotivoIn, OrdemDetalheOut, OrdemIn, OrdemOut

router = APIRouter(prefix="/ordens", tags=["ordens"])
ver = require_tela("kanban")
planejar = require_acao("planejar_producao")
movimentar = require_acao("movimentar_producao")


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _registrar(db: Session, ordem: OrdemProducao, user: Usuario, tipo: str, descricao: str) -> None:
    db.add(OrdemEvento(ordem_id=ordem.id, usuario_id=user.id, tipo=tipo, descricao=descricao))


def _obter(db: Session, ordem_id: str) -> OrdemProducao:
    ordem = db.get(OrdemProducao, ordem_id)
    if ordem is None:
        raise HTTPException(status_code=404, detail="Ordem de produção não encontrada.")
    return ordem


def _exigir_status(ordem: OrdemProducao, *permitidos: str, acao: str) -> None:
    if ordem.status not in permitidos:
        raise HTTPException(
            status_code=400,
            detail=f"A OP {ordem.numero} está {STATUS_ORDEM[ordem.status].lower()}; não é possível {acao}.",
        )


def _maquina_da_etapa(db: Session, etapa: OrdemEtapa, maquina_id: str | None) -> Maquina:
    """Máquina onde a etapa roda: a informada, a já escolhida ou a única disponível no centro."""
    if maquina_id is None and etapa.maquina_id is not None:
        maquina_id = etapa.maquina_id
    if maquina_id is None:
        disponiveis = db.scalars(
            select(Maquina).where(Maquina.setor_id == etapa.setor_id, Maquina.status.in_(STATUS_RECEBE_ORDEM))
        ).all()
        if len(disponiveis) != 1:
            raise HTTPException(status_code=400, detail=f"Escolha a máquina de {etapa.setor.nome} para esta etapa.")
        maquina_id = disponiveis[0].id
    maquina = maquina_pode_receber_ordem(db, maquina_id)
    if maquina.setor_id != etapa.setor_id:
        raise HTTPException(
            status_code=400, detail=f"A máquina {maquina.codigo} não é do centro {etapa.setor.nome}."
        )
    return maquina


def _resposta(db: Session, ordem: OrdemProducao) -> OrdemDetalheOut:
    db.commit()
    db.refresh(ordem)
    return ordem_detalhe_out(ordem)


@router.get("", response_model=list[OrdemOut])
def listar(
    status: str | None = None,
    busca: str | None = Query(default=None, max_length=80),
    _user: Usuario = Depends(ver),
    db: Session = Depends(get_db),
) -> list[OrdemOut]:
    consulta = select(OrdemProducao).join(OrdemProducao.produto)
    if status:
        if status not in STATUS_ORDEM:
            raise HTTPException(status_code=400, detail="Status de ordem inválido.")
        consulta = consulta.where(OrdemProducao.status == status)
    if busca and busca.strip():
        termo = busca.strip()
        # Só número (ou "OP 12") é o número da OP; senão "2" acharia todo perfil de "2,00 mm".
        numero = re.fullmatch(r"(?:OP\s*)?(\d+)", termo, re.IGNORECASE)
        if numero:
            consulta = consulta.where(OrdemProducao.numero == int(numero.group(1)))
        else:
            consulta = consulta.where(or_(Produto.codigo.ilike(f"%{termo}%"), Produto.descricao.ilike(f"%{termo}%")))
    ordens = db.scalars(consulta.order_by(OrdemProducao.numero.desc())).all()
    return [ordem_out(o) for o in ordens]


@router.get("/{ordem_id}", response_model=OrdemDetalheOut)
def obter(ordem_id: str, _user: Usuario = Depends(ver), db: Session = Depends(get_db)) -> OrdemDetalheOut:
    return ordem_detalhe_out(_obter(db, ordem_id))


@router.post("", response_model=OrdemDetalheOut, status_code=201)
def criar(payload: OrdemIn, user: Usuario = Depends(planejar), db: Session = Depends(get_db)) -> OrdemDetalheOut:
    produto = db.get(Produto, payload.produto_id)
    if produto is None or not produto.ativo:
        raise HTTPException(status_code=400, detail="Produto não encontrado ou inativo.")
    if not produto.roteiro:
        raise HTTPException(status_code=400, detail="O produto não tem roteiro de fabricação.")
    numero = (db.scalar(select(func.max(OrdemProducao.numero))) or 0) + 1
    ordem = OrdemProducao(
        numero=numero,
        produto_id=produto.id,
        quantidade=payload.quantidade,
        prazo=payload.prazo,
        prioridade=payload.prioridade,
        status="planejada",
        observacao=(payload.observacao or "").strip() or None,
        criado_por_id=user.id,
        etapas=[
            OrdemEtapa(sequencia=e.sequencia, setor_id=e.setor_id, operacao=e.operacao, tempo_padrao_seg=e.tempo_padrao_seg)
            for e in produto.roteiro
        ],
    )
    db.add(ordem)
    db.flush()
    _registrar(
        db, ordem, user, "criada",
        f"OP criada: {payload.quantidade} {produto.unidade} de {produto.codigo}, prioridade {PRIORIDADES[payload.prioridade].lower()}.",
    )
    return _resposta(db, ordem)


@router.post("/{ordem_id}/liberar", response_model=OrdemDetalheOut)
def liberar(ordem_id: str, user: Usuario = Depends(planejar), db: Session = Depends(get_db)) -> OrdemDetalheOut:
    ordem = _obter(db, ordem_id)
    _exigir_status(ordem, "planejada", acao="liberar")
    primeira = ordem.etapas[0]
    primeira.status = "na_fila"
    ordem.status = "liberada"
    _registrar(db, ordem, user, "liberada", f"Liberada para a fábrica: entra na fila de {primeira.setor.nome}.")
    return _resposta(db, ordem)


@router.post("/{ordem_id}/iniciar", response_model=OrdemDetalheOut)
def iniciar(
    ordem_id: str, payload: MaquinaEscolhaIn, user: Usuario = Depends(movimentar), db: Session = Depends(get_db)
) -> OrdemDetalheOut:
    ordem = _obter(db, ordem_id)
    _exigir_status(ordem, "liberada", "em_producao", acao="iniciar a etapa")
    etapa = ordem.etapa_atual
    if etapa is None or etapa.status != "na_fila":
        raise HTTPException(status_code=400, detail="A etapa atual já foi iniciada.")
    maquina = _maquina_da_etapa(db, etapa, payload.maquina_id)
    etapa.maquina_id = maquina.id
    etapa.status = "em_andamento"
    etapa.iniciada_em = _agora()
    ordem.status = "em_producao"
    _registrar(db, ordem, user, "etapa_iniciada", f"Etapa {etapa.sequencia} ({etapa.setor.nome}) iniciada na {maquina.codigo}.")
    return _resposta(db, ordem)


@router.post("/{ordem_id}/concluir-etapa", response_model=OrdemDetalheOut)
def concluir_etapa(
    ordem_id: str, payload: MaquinaEscolhaIn, user: Usuario = Depends(movimentar), db: Session = Depends(get_db)
) -> OrdemDetalheOut:
    ordem = _obter(db, ordem_id)
    _exigir_status(ordem, "liberada", "em_producao", acao="concluir a etapa")
    etapa = ordem.etapa_atual
    if etapa is None:
        raise HTTPException(status_code=400, detail="Todas as etapas já foram concluídas.")
    maquina = _maquina_da_etapa(db, etapa, payload.maquina_id)
    agora = _agora()
    etapa.maquina_id = maquina.id
    etapa.iniciada_em = etapa.iniciada_em or agora
    etapa.concluida_em = agora
    etapa.status = "concluida"
    proxima = next((e for e in ordem.etapas if e.sequencia > etapa.sequencia), None)
    if proxima is None:
        ordem.status = "concluida"
        ordem.concluida_em = agora
        _registrar(
            db, ordem, user, "concluida",
            f"Etapa {etapa.sequencia} ({etapa.setor.nome}) concluída na {maquina.codigo}. OP concluída: produto final pronto.",
        )
    else:
        proxima.status = "na_fila"
        ordem.status = "em_producao"
        _registrar(
            db, ordem, user, "etapa_concluida",
            f"Etapa {etapa.sequencia} ({etapa.setor.nome}) concluída na {maquina.codigo}; segue para {proxima.setor.nome}.",
        )
    return _resposta(db, ordem)


@router.post("/{ordem_id}/pausar", response_model=OrdemDetalheOut)
def pausar(
    ordem_id: str, payload: MotivoIn, user: Usuario = Depends(movimentar), db: Session = Depends(get_db)
) -> OrdemDetalheOut:
    ordem = _obter(db, ordem_id)
    _exigir_status(ordem, "liberada", "em_producao", acao="pausar")
    ordem.status = "pausada"
    ordem.motivo_pausa = payload.motivo
    _registrar(db, ordem, user, "pausada", f"Pausada: {payload.motivo}")
    return _resposta(db, ordem)


@router.post("/{ordem_id}/retomar", response_model=OrdemDetalheOut)
def retomar(ordem_id: str, user: Usuario = Depends(movimentar), db: Session = Depends(get_db)) -> OrdemDetalheOut:
    ordem = _obter(db, ordem_id)
    _exigir_status(ordem, "pausada", acao="retomar")
    iniciou = any(e.status in ("em_andamento", "concluida") for e in ordem.etapas)
    ordem.status = "em_producao" if iniciou else "liberada"
    ordem.motivo_pausa = None
    _registrar(db, ordem, user, "retomada", "Produção retomada.")
    return _resposta(db, ordem)


@router.post("/{ordem_id}/cancelar", response_model=OrdemDetalheOut)
def cancelar(
    ordem_id: str, payload: MotivoIn, user: Usuario = Depends(planejar), db: Session = Depends(get_db)
) -> OrdemDetalheOut:
    ordem = _obter(db, ordem_id)
    _exigir_status(ordem, "planejada", *ORDEM_ABERTA, acao="cancelar")
    ordem.status = "cancelada"
    _registrar(db, ordem, user, "cancelada", f"Cancelada: {payload.motivo}")
    return _resposta(db, ordem)
