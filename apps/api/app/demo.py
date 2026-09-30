"""Centros de trabalho e máquinas de exemplo de uma metalúrgica.

Uso: docker compose exec api python -m app.demo  (pode rodar mais de uma vez)
"""
from decimal import Decimal

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Maquina, Setor

SETORES = [
    ("COR", "Corte"),
    ("DOB", "Dobra"),
    ("USI", "Usinagem"),
    ("SOL", "Solda"),
    ("PIN", "Pintura"),
    ("MON", "Montagem"),
]

# (código, nome, setor, ciclo padrão em segundos, status)
MAQUINAS = [
    ("COR-01", "Guilhotina hidráulica 3 m", "COR", "12", "ativa"),
    ("COR-02", "Corte a laser fibra 3 kW", "COR", "45", "ativa"),
    ("COR-03", "Serra fita automática", "COR", "60", "manutencao"),
    ("DOB-01", "Dobradeira CNC 110 t", "DOB", "25", "ativa"),
    ("DOB-02", "Dobradeira CNC 60 t", "DOB", "20", "ativa"),
    ("USI-01", "Torno CNC", "USI", "90", "ativa"),
    ("USI-02", "Centro de usinagem vertical", "USI", "180", "ativa"),
    ("SOL-01", "Robô de solda MIG", "SOL", "75", "ativa"),
    ("SOL-02", "Solda MIG manual - box 2", "SOL", "140", "inativa"),
    ("PIN-01", "Cabine de pintura a pó", "PIN", "30", "ativa"),
    ("MON-01", "Linha de montagem final", "MON", "240", "ativa"),
]


def carregar() -> tuple[int, int]:
    novos_setores = novas_maquinas = 0
    with SessionLocal() as db:
        setores = {s.codigo: s for s in db.scalars(select(Setor)).all()}
        for codigo, nome in SETORES:
            if codigo not in setores:
                setores[codigo] = Setor(codigo=codigo, nome=nome)
                db.add(setores[codigo])
                novos_setores += 1
        db.flush()
        existentes = set(db.scalars(select(Maquina.codigo)).all())
        for codigo, nome, setor, ciclo, status in MAQUINAS:
            if codigo in existentes:
                continue
            db.add(
                Maquina(codigo=codigo, nome=nome, setor_id=setores[setor].id, ciclo_padrao_seg=Decimal(ciclo), status=status)
            )
            novas_maquinas += 1
        db.commit()
    return novos_setores, novas_maquinas


if __name__ == "__main__":
    s, m = carregar()
    print(f"Dados de exemplo: {s} centros de trabalho e {m} máquinas novos.")
