from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_acao, require_tela
from app.models import Produto, RoteiroEtapa, Setor, Usuario
from app.present import produto_out
from app.schemas import ProdutoIn, ProdutoOut

router = APIRouter(prefix="/produtos", tags=["produtos"])
ver = require_tela("produtos")
editar = require_acao("editar_cadastros")


def _montar_roteiro(db: Session, payload: ProdutoIn) -> list[RoteiroEtapa]:
    ids = {e.setor_id for e in payload.roteiro}
    setores = {s.id: s for s in db.scalars(select(Setor).where(Setor.id.in_(ids))).all()}
    etapas: list[RoteiroEtapa] = []
    for seq, etapa in enumerate(payload.roteiro, start=1):
        setor = setores.get(etapa.setor_id)
        if setor is None:
            raise HTTPException(status_code=400, detail=f"Etapa {seq}: centro de trabalho não encontrado.")
        if not setor.ativo:
            raise HTTPException(status_code=400, detail=f"Etapa {seq}: o centro {setor.nome} está inativo.")
        if etapas and etapas[-1].setor_id == setor.id:
            raise HTTPException(
                status_code=400,
                detail=f"Etapas {seq - 1} e {seq} estão no mesmo centro ({setor.nome}); junte numa operação só.",
            )
        tempo = Decimal(str(etapa.tempo_padrao_seg)) if etapa.tempo_padrao_seg is not None else None
        etapas.append(RoteiroEtapa(sequencia=seq, setor_id=setor.id, operacao=etapa.operacao, tempo_padrao_seg=tempo))
    return etapas


def _codigo_livre(db: Session, codigo: str, ignorar_id: str | None = None) -> None:
    consulta = select(Produto.id).where(Produto.codigo == codigo)
    if ignorar_id:
        consulta = consulta.where(Produto.id != ignorar_id)
    if db.scalar(consulta):
        raise HTTPException(status_code=409, detail=f"Já existe um produto com o código {codigo}.")


@router.get("", response_model=list[ProdutoOut])
def listar(
    busca: str | None = Query(default=None, max_length=80),
    ativos: bool = False,
    _user: Usuario = Depends(ver),
    db: Session = Depends(get_db),
) -> list[ProdutoOut]:
    consulta = select(Produto)
    if busca and busca.strip():
        termo = f"%{busca.strip()}%"
        consulta = consulta.where(or_(Produto.codigo.ilike(termo), Produto.descricao.ilike(termo)))
    if ativos:
        consulta = consulta.where(Produto.ativo.is_(True))
    return [produto_out(p) for p in db.scalars(consulta.order_by(Produto.codigo)).all()]


@router.get("/{produto_id}", response_model=ProdutoOut)
def obter(produto_id: str, _user: Usuario = Depends(ver), db: Session = Depends(get_db)) -> ProdutoOut:
    produto = db.get(Produto, produto_id)
    if produto is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    return produto_out(produto)


@router.post("", response_model=ProdutoOut, status_code=201)
def criar(payload: ProdutoIn, _user: Usuario = Depends(editar), db: Session = Depends(get_db)) -> ProdutoOut:
    _codigo_livre(db, payload.codigo)
    produto = Produto(
        codigo=payload.codigo,
        descricao=payload.descricao,
        unidade=payload.unidade,
        comprimento_mm=payload.comprimento_mm,
        ativo=payload.ativo,
        roteiro=_montar_roteiro(db, payload),
    )
    db.add(produto)
    db.commit()
    db.refresh(produto)
    return produto_out(produto)


@router.put("/{produto_id}", response_model=ProdutoOut)
def atualizar(
    produto_id: str, payload: ProdutoIn, _user: Usuario = Depends(editar), db: Session = Depends(get_db)
) -> ProdutoOut:
    produto = db.get(Produto, produto_id)
    if produto is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    _codigo_livre(db, payload.codigo, ignorar_id=produto.id)
    novo_roteiro = _montar_roteiro(db, payload)
    produto.codigo = payload.codigo
    produto.descricao = payload.descricao
    produto.unidade = payload.unidade
    produto.comprimento_mm = payload.comprimento_mm
    produto.ativo = payload.ativo
    # Apaga o roteiro antigo antes de inserir o novo, senão a sequência repetida viola a chave única.
    produto.roteiro.clear()
    db.flush()
    produto.roteiro.extend(novo_roteiro)
    db.commit()
    db.refresh(produto)
    return produto_out(produto)
