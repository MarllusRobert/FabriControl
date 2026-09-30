"""Bloqueio de login por excesso de tentativas erradas.

Fica em memória: vale para um processo só (a API roda com 1 worker).
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.config import get_settings

_falhas: dict[str, deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def _limites(request: Request, email: str) -> list[tuple[str, int]]:
    s = get_settings()
    ip = request.client.host if request.client else "desconhecido"
    # Por IP+e-mail barra força bruta numa conta; por IP barra quem testa vários e-mails.
    return [(f"{ip}|{email}", s.login_max_tentativas), (ip, s.login_max_tentativas * 4)]


def _janela() -> float:
    return get_settings().login_bloqueio_minutos * 60


def _limpar(fila: deque[float], agora: float) -> None:
    while fila and agora - fila[0] > _janela():
        fila.popleft()


def verificar(request: Request, email: str) -> None:
    agora = time.monotonic()
    with _lock:
        for chave, maximo in _limites(request, email):
            fila = _falhas[chave]
            _limpar(fila, agora)
            if len(fila) >= maximo:
                minutos = max(1, round((_janela() - (agora - fila[0])) / 60))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Muitas tentativas de login. Tente novamente em {minutos} min.",
                )


def registrar_falha(request: Request, email: str) -> None:
    agora = time.monotonic()
    with _lock:
        for chave, _ in _limites(request, email):
            _falhas[chave].append(agora)


def limpar(request: Request, email: str) -> None:
    # Só zera a conta; o contador por IP continua para quem testa vários e-mails.
    chave_conta, _ = _limites(request, email)[0]
    with _lock:
        _falhas.pop(chave_conta, None)
