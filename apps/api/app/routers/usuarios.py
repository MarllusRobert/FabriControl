from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants import ACOES_LABEL, PERFIS, TELAS_LABEL
from app.db import get_db
from app.deps import require_acao
from app.models import Usuario
from app.present import usuario_out
from app.schemas import UsuarioCreate, UsuarioOut, UsuarioUpdate
from app.security import hash_password

router = APIRouter(prefix="/usuarios", tags=["usuarios"])
gerenciar = require_acao("gerenciar_usuarios")


@router.get("/perfis")
def perfis(_user: Usuario = Depends(gerenciar)) -> list[dict]:
    return [
        {
            "perfil": chave,
            "label": dados["label"],
            "telas": [TELAS_LABEL[t] for t in dados["telas"]],
            "acoes": [ACOES_LABEL[a] for a in dados["acoes"]],
        }
        for chave, dados in PERFIS.items()
    ]


@router.get("", response_model=list[UsuarioOut])
def listar(_user: Usuario = Depends(gerenciar), db: Session = Depends(get_db)) -> list[UsuarioOut]:
    usuarios = db.scalars(select(Usuario).order_by(Usuario.ativo.desc(), Usuario.nome)).all()
    return [usuario_out(u) for u in usuarios]


@router.post("", response_model=UsuarioOut, status_code=201)
def criar(payload: UsuarioCreate, _user: Usuario = Depends(gerenciar), db: Session = Depends(get_db)) -> UsuarioOut:
    if db.scalar(select(Usuario.id).where(Usuario.email == payload.email)):
        raise HTTPException(status_code=409, detail="Já existe um usuário com este e-mail.")
    novo = Usuario(
        nome=payload.nome.strip(),
        email=payload.email,
        senha_hash=hash_password(payload.senha),
        perfil=payload.perfil,
        ativo=True,
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return usuario_out(novo)


def _outros_admins_ativos(db: Session, user_id: str) -> int:
    return db.scalar(
        select(func.count())
        .select_from(Usuario)
        .where(Usuario.perfil == "administrador", Usuario.ativo.is_(True), Usuario.id != user_id)
    ) or 0


@router.patch("/{user_id}", response_model=UsuarioOut)
def atualizar(
    user_id: str, payload: UsuarioUpdate, _user: Usuario = Depends(gerenciar), db: Session = Depends(get_db)
) -> UsuarioOut:
    alvo = db.get(Usuario, user_id)
    if alvo is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    deixa_de_ser_admin = alvo.perfil == "administrador" and (
        (payload.perfil is not None and payload.perfil != "administrador") or payload.ativo is False
    )
    if deixa_de_ser_admin and _outros_admins_ativos(db, alvo.id) == 0:
        raise HTTPException(status_code=400, detail="O sistema precisa de pelo menos um administrador ativo.")
    if payload.nome is not None:
        alvo.nome = payload.nome.strip()
    if payload.perfil is not None:
        alvo.perfil = payload.perfil
    if payload.ativo is not None:
        alvo.ativo = payload.ativo
    if payload.senha is not None:
        alvo.senha_hash = hash_password(payload.senha)
        alvo.versao_senha += 1
    db.commit()
    db.refresh(alvo)
    return usuario_out(alvo)
