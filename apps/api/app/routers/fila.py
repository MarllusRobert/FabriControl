from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import STATUS_RECEBE_ORDEM
from app.db import get_db
from app.deps import require_acao, require_tela
from app.fila import Par, em_andamento, etapas_atuais, na_fila
from app.models import Maquina, OrdemEvento, Parada, Setor, Usuario
from app.present import etapa_fila_out, maquina_out
from app.schemas import FilaMaquinaOut, FilaOut, FilaSetorIn, FilaSetorOut

router = APIRouter(prefix="/fila", tags=["fila"])
ver = require_tela("fila")
planejar = require_acao("planejar_producao")


def _maquinas_por_setor(db: Session) -> dict[str, list[Maquina]]:
    maquinas = db.scalars(
        select(Maquina).where(Maquina.status.in_(STATUS_RECEBE_ORDEM)).order_by(Maquina.codigo)
    ).all()
    por_setor: dict[str, list[Maquina]] = {}
    for m in maquinas:
        por_setor.setdefault(m.setor_id, []).append(m)
    return por_setor


def _setor_out(setor: Setor, maquinas: list[Maquina], pares: list[Par], paradas: set[str]) -> FilaSetorOut:
    ids = {m.id for m in maquinas}
    filas: dict[str, list[Par]] = {m.id: [] for m in maquinas}
    sobra: list[Par] = []
    for par in na_fila(pares, setor.id):
        etapa = par[1]
        if etapa.maquina_id in ids:
            filas[etapa.maquina_id].append(par)
        elif len(maquinas) == 1:
            filas[maquinas[0].id].append(par)
        else:
            sobra.append(par)

    saida = []
    for m in maquinas:
        rodando = em_andamento(pares, m)
        atual = etapa_fila_out(*rodando, m) if rodando else None
        fila = [etapa_fila_out(o, e, m) for o, e in filas[m.id]]
        carga = (atual.carga_min if atual else 0) + sum(x.carga_min for x in fila)
        saida.append(
            FilaMaquinaOut(
                maquina=maquina_out(m), parada=m.id in paradas, atual=atual, fila=fila, carga_min=round(carga, 1)
            )
        )
    a_distribuir = [etapa_fila_out(o, e, maquinas[0]) for o, e in sobra]
    return FilaSetorOut(
        setor_id=setor.id,
        setor_nome=setor.nome,
        maquinas=saida,
        a_distribuir=a_distribuir,
        carga_a_distribuir_min=round(sum(x.carga_min for x in a_distribuir), 1),
    )


def _fila(db: Session) -> FilaOut:
    por_setor = _maquinas_por_setor(db)
    setores = db.scalars(
        select(Setor).where(Setor.id.in_(list(por_setor)), Setor.ativo.is_(True)).order_by(Setor.ordem, Setor.codigo)
    ).all()
    pares = etapas_atuais(db)
    paradas = set(db.scalars(select(Parada.maquina_id).where(Parada.fim.is_(None))).all())
    return FilaOut(
        setores=[_setor_out(s, por_setor[s.id], pares, paradas) for s in setores],
        atualizado_em=datetime.now(timezone.utc),
    )


@router.get("", response_model=FilaOut)
def ver_fila(_user: Usuario = Depends(ver), db: Session = Depends(get_db)) -> FilaOut:
    return _fila(db)


@router.put("/setores/{setor_id}", response_model=FilaOut)
def sequenciar(
    setor_id: str,
    data: FilaSetorIn,
    user: Usuario = Depends(planejar),
    db: Session = Depends(get_db),
) -> FilaOut:
    """Grava a sequência do centro: a ordem das OPs em cada máquina e as que ficam sem máquina."""
    setor = db.get(Setor, setor_id)
    if setor is None:
        raise HTTPException(status_code=404, detail="Centro de trabalho não encontrado.")
    maquinas = {m.id: m for m in _maquinas_por_setor(db).get(setor_id, [])}
    esperando = {o.id: (o, e) for o, e in na_fila(etapas_atuais(db), setor_id)}

    destino: list[tuple[str, Maquina | None, int]] = []
    for grupo in data.maquinas:
        maquina = maquinas.get(grupo.maquina_id)
        if maquina is None:
            raise HTTPException(status_code=400, detail="Máquina inválida ou parada para este centro.")
        destino += [(ordem_id, maquina, i) for i, ordem_id in enumerate(grupo.ordens)]
    destino += [(ordem_id, None, i) for i, ordem_id in enumerate(data.a_distribuir)]

    vistos: set[str] = set()
    for ordem_id, maquina, posicao in destino:
        if ordem_id in vistos:
            raise HTTPException(status_code=400, detail="A mesma OP aparece duas vezes na fila.")
        vistos.add(ordem_id)
        par = esperando.get(ordem_id)
        if par is None:
            raise HTTPException(status_code=400, detail="Há OP que não está esperando neste centro. Atualize a tela.")
        ordem, etapa = par
        novo = maquina.id if maquina else None
        if etapa.maquina_id != novo:
            descricao = (
                f"Etapa {etapa.sequencia} ({etapa.operacao}) direcionada para {maquina.codigo}"
                if maquina
                else f"Etapa {etapa.sequencia} ({etapa.operacao}) liberada para qualquer máquina de {setor.nome}"
            )
            db.add(OrdemEvento(ordem_id=ordem.id, usuario_id=user.id, tipo="fila", descricao=descricao))
        etapa.maquina_id = novo
        etapa.fila_posicao = posicao
    db.commit()
    return _fila(db)
