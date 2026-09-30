from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.constants import STATUS_MAQUINA, STATUS_RECEBE_ORDEM
from app.db import get_db
from app.deps import require_acao, require_alguma, require_tela
from app.models import Maquina, Setor, Usuario
from app.present import maquina_out
from app.schemas import MaquinaIn, MaquinaOut, MaquinaUpdate, SetorIn, SetorOut

router = APIRouter(tags=["cadastros"])
ver = require_tela("maquinas")
# Setores também alimentam o roteiro dos produtos.
ver_setores = require_alguma("maquinas", "produtos")
editar = require_acao("editar_cadastros")


# ---------- Setores (centros de trabalho) ----------


def _setor_out(s: Setor, maquinas: int = 0) -> SetorOut:
    return SetorOut(id=s.id, codigo=s.codigo, nome=s.nome, ordem=s.ordem, ativo=s.ativo, maquinas=maquinas)


@router.get("/setores", response_model=list[SetorOut])
def listar_setores(_user: Usuario = Depends(ver_setores), db: Session = Depends(get_db)) -> list[SetorOut]:
    contagem = dict(db.execute(select(Maquina.setor_id, func.count()).group_by(Maquina.setor_id)).all())
    setores = db.scalars(select(Setor).order_by(Setor.ordem, Setor.codigo)).all()
    return [_setor_out(s, contagem.get(s.id, 0)) for s in setores]


def _setor_duplicado(db: Session, payload: SetorIn, ignorar_id: str | None = None) -> None:
    filtro = or_(Setor.codigo == payload.codigo, func.lower(Setor.nome) == payload.nome.lower())
    consulta = select(Setor.id).where(filtro)
    if ignorar_id:
        consulta = consulta.where(Setor.id != ignorar_id)
    if db.scalar(consulta):
        raise HTTPException(status_code=409, detail="Já existe um centro de trabalho com este código ou nome.")


@router.post("/setores", response_model=SetorOut, status_code=201)
def criar_setor(payload: SetorIn, _user: Usuario = Depends(editar), db: Session = Depends(get_db)) -> SetorOut:
    _setor_duplicado(db, payload)
    setor = Setor(codigo=payload.codigo, nome=payload.nome, ordem=payload.ordem, ativo=payload.ativo)
    db.add(setor)
    db.commit()
    return _setor_out(setor)


@router.put("/setores/{setor_id}", response_model=SetorOut)
def atualizar_setor(
    setor_id: str, payload: SetorIn, _user: Usuario = Depends(editar), db: Session = Depends(get_db)
) -> SetorOut:
    setor = db.get(Setor, setor_id)
    if setor is None:
        raise HTTPException(status_code=404, detail="Centro de trabalho não encontrado.")
    _setor_duplicado(db, payload, ignorar_id=setor.id)
    setor.codigo, setor.nome, setor.ordem, setor.ativo = payload.codigo, payload.nome, payload.ordem, payload.ativo
    db.commit()
    total = db.scalar(select(func.count()).select_from(Maquina).where(Maquina.setor_id == setor.id)) or 0
    return _setor_out(setor, total)


# ---------- Máquinas ----------


def _setor_ativo(db: Session, setor_id: str) -> Setor:
    setor = db.get(Setor, setor_id)
    if setor is None:
        raise HTTPException(status_code=400, detail="Centro de trabalho não encontrado.")
    if not setor.ativo:
        raise HTTPException(status_code=400, detail="Este centro de trabalho está inativo.")
    return setor


def _codigo_livre(db: Session, codigo: str, ignorar_id: str | None = None) -> None:
    consulta = select(Maquina.id).where(Maquina.codigo == codigo)
    if ignorar_id:
        consulta = consulta.where(Maquina.id != ignorar_id)
    if db.scalar(consulta):
        raise HTTPException(status_code=409, detail=f"Já existe uma máquina com o código {codigo}.")


@router.get("/maquinas", response_model=list[MaquinaOut])
def listar_maquinas(
    busca: str | None = Query(default=None, max_length=80),
    setor_id: str | None = None,
    status: str | None = None,
    recebe_ordem: bool = Query(default=False, description="Só as máquinas que podem receber ordem de produção."),
    _user: Usuario = Depends(ver),
    db: Session = Depends(get_db),
) -> list[MaquinaOut]:
    consulta = select(Maquina).join(Maquina.setor)
    if busca and busca.strip():
        termo = f"%{busca.strip()}%"
        consulta = consulta.where(or_(Maquina.codigo.ilike(termo), Maquina.nome.ilike(termo)))
    if setor_id:
        consulta = consulta.where(Maquina.setor_id == setor_id)
    if status:
        if status not in STATUS_MAQUINA:
            raise HTTPException(status_code=400, detail="Status de máquina inválido.")
        consulta = consulta.where(Maquina.status == status)
    if recebe_ordem:
        consulta = consulta.where(Maquina.status.in_(STATUS_RECEBE_ORDEM), Setor.ativo.is_(True))
    maquinas = db.scalars(consulta.order_by(Setor.ordem, Setor.codigo, Maquina.codigo)).all()
    return [maquina_out(m) for m in maquinas]


@router.get("/maquinas/resumo")
def resumo_maquinas(_user: Usuario = Depends(ver), db: Session = Depends(get_db)) -> dict:
    por_status = dict(db.execute(select(Maquina.status, func.count()).group_by(Maquina.status)).all())
    por_setor = db.execute(
        select(Setor.nome, func.count(Maquina.id))
        .outerjoin(Maquina, Maquina.setor_id == Setor.id)
        .where(Setor.ativo.is_(True))
        .group_by(Setor.ordem, Setor.codigo, Setor.nome)
        .order_by(Setor.ordem, Setor.codigo)
    ).all()
    return {
        "total": sum(por_status.values()),
        "por_status": [
            {"status": chave, "label": label, "total": por_status.get(chave, 0)}
            for chave, label in STATUS_MAQUINA.items()
        ],
        "por_setor": [{"setor": nome, "total": total} for nome, total in por_setor],
    }


@router.get("/maquinas/{maquina_id}", response_model=MaquinaOut)
def obter_maquina(maquina_id: str, _user: Usuario = Depends(ver), db: Session = Depends(get_db)) -> MaquinaOut:
    maquina = db.get(Maquina, maquina_id)
    if maquina is None:
        raise HTTPException(status_code=404, detail="Máquina não encontrada.")
    return maquina_out(maquina)


@router.post("/maquinas", response_model=MaquinaOut, status_code=201)
def criar_maquina(payload: MaquinaIn, _user: Usuario = Depends(editar), db: Session = Depends(get_db)) -> MaquinaOut:
    _codigo_livre(db, payload.codigo)
    _setor_ativo(db, payload.setor_id)
    maquina = Maquina(
        codigo=payload.codigo,
        nome=payload.nome,
        setor_id=payload.setor_id,
        ciclo_padrao_seg=Decimal(str(payload.ciclo_padrao_seg)),
        status=payload.status,
        observacao=(payload.observacao or "").strip() or None,
    )
    db.add(maquina)
    db.commit()
    db.refresh(maquina)
    return maquina_out(maquina)


@router.patch("/maquinas/{maquina_id}", response_model=MaquinaOut)
def atualizar_maquina(
    maquina_id: str, payload: MaquinaUpdate, _user: Usuario = Depends(editar), db: Session = Depends(get_db)
) -> MaquinaOut:
    maquina = db.get(Maquina, maquina_id)
    if maquina is None:
        raise HTTPException(status_code=404, detail="Máquina não encontrada.")
    dados = payload.model_dump(exclude_unset=True)
    if "codigo" in dados and dados["codigo"] is not None:
        _codigo_livre(db, dados["codigo"], ignorar_id=maquina.id)
        maquina.codigo = dados["codigo"]
    if dados.get("setor_id") and dados["setor_id"] != maquina.setor_id:
        _setor_ativo(db, dados["setor_id"])
        maquina.setor_id = dados["setor_id"]
    if dados.get("nome") is not None:
        maquina.nome = dados["nome"]
    if dados.get("ciclo_padrao_seg") is not None:
        maquina.ciclo_padrao_seg = Decimal(str(dados["ciclo_padrao_seg"]))
    if dados.get("status") is not None:
        maquina.status = dados["status"]
    if "observacao" in dados:
        maquina.observacao = (dados["observacao"] or "").strip() or None
    db.commit()
    db.refresh(maquina)
    return maquina_out(maquina)


def maquina_pode_receber_ordem(db: Session, maquina_id: str) -> Maquina:
    """Usado pelas ordens de produção: barra máquina inativa ou em manutenção."""
    maquina = db.get(Maquina, maquina_id)
    if maquina is None:
        raise HTTPException(status_code=404, detail="Máquina não encontrada.")
    if maquina.status not in STATUS_RECEBE_ORDEM:
        raise HTTPException(
            status_code=400,
            detail=f"A máquina {maquina.codigo} está {STATUS_MAQUINA[maquina.status].lower()} e não recebe ordens.",
        )
    if not maquina.setor.ativo:
        raise HTTPException(status_code=400, detail=f"O centro de trabalho de {maquina.codigo} está inativo.")
    return maquina
