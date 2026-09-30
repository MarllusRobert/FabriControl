from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import ORDEM_ABERTA, STATUS_RECEBE_ORDEM
from app.db import get_db
from app.deps import require_tela
from app.models import Maquina, OrdemEtapa, OrdemProducao, Produto, RoteiroEtapa, Setor, Usuario
from app.present import ordem_out
from app.schemas import OrdemOut

router = APIRouter(tags=["kanban"])
ver = require_tela("kanban")

DIAS_CONCLUIDAS = 7
LIMITE_CONCLUIDAS = 30
PESO_PRIORIDADE = {"urgente": 0, "alta": 1, "normal": 2, "baixa": 3}


class MaquinaResumo(BaseModel):
    id: str
    codigo: str
    nome: str


class ColunaOut(BaseModel):
    id: str
    tipo: str  # planejadas | setor | concluidas
    titulo: str
    setor_id: str | None = None
    maquinas: list[MaquinaResumo] = []
    cards: list[OrdemOut]


class KanbanOut(BaseModel):
    colunas: list[ColunaOut]
    atualizado_em: datetime


def _ordenar(cards: list[OrdemOut]) -> list[OrdemOut]:
    def chave(o: OrdemOut):
        etapa = o.etapas[o.etapa_atual - 1] if o.etapa_atual else None
        rodando = 0 if etapa is not None and etapa.status == "em_andamento" and o.status != "pausada" else 1
        return (rodando, PESO_PRIORIDADE.get(o.prioridade, 9), o.prazo or datetime.max.date(), o.numero)

    return sorted(cards, key=chave)


@router.get("/kanban", response_model=KanbanOut)
def kanban(_user: Usuario = Depends(ver), db: Session = Depends(get_db)) -> KanbanOut:
    limite = datetime.now(timezone.utc) - timedelta(days=DIAS_CONCLUIDAS)
    abertas = db.scalars(
        select(OrdemProducao).where(OrdemProducao.status.in_(("planejada", *ORDEM_ABERTA)))
    ).all()
    concluidas = db.scalars(
        select(OrdemProducao)
        .where(OrdemProducao.status == "concluida", OrdemProducao.concluida_em >= limite)
        .order_by(OrdemProducao.concluida_em.desc())
        .limit(LIMITE_CONCLUIDAS)
    ).all()

    # Colunas: centros usados nos roteiros ativos ou nas ordens em aberto, na ordem do fluxo.
    ids_roteiro = select(RoteiroEtapa.setor_id).join(Produto).where(Produto.ativo.is_(True))
    ids_ordens = select(OrdemEtapa.setor_id).where(OrdemEtapa.ordem_id.in_([o.id for o in abertas]))
    setores = db.scalars(
        select(Setor).where(Setor.id.in_(ids_roteiro.union(ids_ordens))).order_by(Setor.ordem, Setor.codigo)
    ).all()
    maquinas = db.scalars(
        select(Maquina).where(Maquina.status.in_(STATUS_RECEBE_ORDEM)).order_by(Maquina.codigo)
    ).all()

    planejadas: list[OrdemOut] = []
    por_setor: dict[str, list[OrdemOut]] = {s.id: [] for s in setores}
    for o in abertas:
        card = ordem_out(o)
        atual = o.etapa_atual
        if o.status == "planejada" or atual is None:
            planejadas.append(card)
        else:
            por_setor.setdefault(atual.setor_id, []).append(card)

    colunas = [ColunaOut(id="planejadas", tipo="planejadas", titulo="Planejadas", cards=_ordenar(planejadas))]
    for s in setores:
        colunas.append(
            ColunaOut(
                id=s.id,
                tipo="setor",
                titulo=s.nome,
                setor_id=s.id,
                maquinas=[MaquinaResumo(id=m.id, codigo=m.codigo, nome=m.nome) for m in maquinas if m.setor_id == s.id],
                cards=_ordenar(por_setor.get(s.id, [])),
            )
        )
    colunas.append(
        ColunaOut(id="concluidas", tipo="concluidas", titulo="Concluídas", cards=[ordem_out(o) for o in concluidas])
    )
    return KanbanOut(colunas=colunas, atualizado_em=datetime.now(timezone.utc))
