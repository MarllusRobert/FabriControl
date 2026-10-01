"""Fila de produção: quais etapas esperam em cada máquina e em que ordem."""
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import ORDEM_ABERTA
from app.models import Maquina, OrdemEtapa, OrdemProducao

PESO_PRIORIDADE = {"urgente": 0, "alta": 1, "normal": 2, "baixa": 3}
_NUNCA = datetime.max.replace(tzinfo=timezone.utc)

Par = tuple[OrdemProducao, OrdemEtapa]


def chave(par: Par):
    """Posição definida pelo PCP primeiro; sem posição, vale prioridade, prazo e número da OP."""
    ordem, etapa = par
    return (
        etapa.fila_posicao is None,
        etapa.fila_posicao or 0,
        PESO_PRIORIDADE.get(ordem.prioridade, 9),
        ordem.prazo or date.max,
        ordem.numero,
    )


def etapas_atuais(db: Session) -> list[Par]:
    abertas = db.scalars(select(OrdemProducao).where(OrdemProducao.status.in_(ORDEM_ABERTA))).all()
    return [(o, o.etapa_atual) for o in abertas if o.etapa_atual is not None]


def em_andamento(pares: list[Par], maquina: Maquina) -> Par | None:
    rodando = [p for p in pares if p[1].status == "em_andamento" and p[1].maquina_id == maquina.id]
    return min(rodando, key=lambda p: p[1].iniciada_em or _NUNCA, default=None)


def na_fila(pares: list[Par], setor_id: str) -> list[Par]:
    """Etapas do centro esperando para começar (OP pausada não entra)."""
    fila = [p for p in pares if p[1].setor_id == setor_id and p[1].status == "na_fila" and p[0].status != "pausada"]
    return sorted(fila, key=chave)


def fila_da_maquina(pares: list[Par], maquina: Maquina) -> list[Par]:
    """O que esta máquina pode começar: as etapas atribuídas a ela e as ainda sem máquina."""
    return [p for p in na_fila(pares, maquina.setor_id) if p[1].maquina_id in (None, maquina.id)]
