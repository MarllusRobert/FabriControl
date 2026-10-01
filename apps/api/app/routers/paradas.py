from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_alguma
from app.models import Parada, Usuario
from app.present import parada_out
from app.schemas import ParadaOut

router = APIRouter(prefix="/paradas", tags=["paradas"])
ver = require_alguma("painel", "operacao", "kanban")


@router.get("", response_model=list[ParadaOut])
def listar(
    abertas: bool = False,
    maquina_id: str | None = None,
    dias: int = Query(default=7, ge=1, le=90),
    _user: Usuario = Depends(ver),
    db: Session = Depends(get_db),
) -> list[ParadaOut]:
    consulta = select(Parada)
    if abertas:
        consulta = consulta.where(Parada.fim.is_(None))
    else:
        consulta = consulta.where(Parada.inicio >= datetime.now(timezone.utc) - timedelta(days=dias))
    if maquina_id:
        consulta = consulta.where(Parada.maquina_id == maquina_id)
    return [parada_out(p) for p in db.scalars(consulta.order_by(Parada.inicio.desc()).limit(200)).all()]
