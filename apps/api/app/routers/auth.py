from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import login_guard
from app.db import get_db
from app.deps import get_current_user
from app.models import Usuario
from app.present import usuario_out
from app.schemas import LoginIn, SetupIn, TokenOut, TrocaSenhaIn, UsuarioOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(tags=["acesso"])


def _token(user: Usuario) -> TokenOut:
    return TokenOut(access_token=create_access_token(user.id, user.versao_senha), user=usuario_out(user))


@router.get("/setup/status")
def setup_status(db: Session = Depends(get_db)) -> dict:
    return {"needs_setup": db.scalar(select(Usuario.id).limit(1)) is None}


@router.post("/setup", response_model=TokenOut)
def setup(payload: SetupIn, db: Session = Depends(get_db)) -> TokenOut:
    if db.scalar(select(Usuario.id).limit(1)) is not None:
        raise HTTPException(status_code=409, detail="O sistema já foi configurado. Entre com seu usuário.")
    admin = Usuario(
        nome=payload.nome.strip(),
        email=payload.email,
        senha_hash=hash_password(payload.senha),
        perfil="administrador",
        ativo=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return _token(admin)


@router.post("/auth/login", response_model=TokenOut)
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)) -> TokenOut:
    login_guard.verificar(request, payload.email)
    user = db.scalar(select(Usuario).where(Usuario.email == payload.email))
    if user is None or not user.ativo or not verify_password(payload.senha, user.senha_hash):
        login_guard.registrar_falha(request, payload.email)
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos.")
    login_guard.limpar(request, payload.email)
    return _token(user)


@router.get("/auth/me", response_model=UsuarioOut)
def me(user: Usuario = Depends(get_current_user)) -> UsuarioOut:
    return usuario_out(user)


@router.post("/auth/senha", response_model=TokenOut)
def trocar_senha(
    payload: TrocaSenhaIn, user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)
) -> TokenOut:
    if not verify_password(payload.senha_atual, user.senha_hash):
        raise HTTPException(status_code=400, detail="A senha atual não confere.")
    if payload.senha_atual == payload.nova_senha:
        raise HTTPException(status_code=400, detail="A nova senha precisa ser diferente da atual.")
    user.senha_hash = hash_password(payload.nova_senha)
    user.versao_senha += 1
    db.commit()
    db.refresh(user)
    return _token(user)
