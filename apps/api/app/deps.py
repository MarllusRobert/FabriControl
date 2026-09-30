from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Usuario
from app.security import decode_access_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Faça login para continuar.")
    try:
        payload = decode_access_token(credentials.credentials)
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão inválida. Entre novamente.")
    user = db.get(Usuario, payload.get("sub"))
    if user is None or not user.ativo or payload.get("sv") != user.versao_senha:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão inválida. Entre novamente.")
    return user


def _negar() -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para esta ação.")


def require_tela(tela: str):
    def dependency(user: Usuario = Depends(get_current_user)) -> Usuario:
        if tela not in user.telas:
            raise _negar()
        return user

    return dependency


def require_acao(acao: str):
    def dependency(user: Usuario = Depends(get_current_user)) -> Usuario:
        if acao not in user.acoes:
            raise _negar()
        return user

    return dependency
