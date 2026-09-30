"""Dados de exemplo de uma metalúrgica que fabrica perfis dobrados.

Uso: docker compose exec api python -m app.demo  (pode rodar mais de uma vez)
"""
from decimal import Decimal

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Maquina, Produto, RoteiroEtapa, Setor

# (código, nome, posição no fluxo)
SETORES = [
    ("DES", "Desbobinamento", 1),
    ("COR", "Corte", 2),
    ("DOB", "Dobra", 3),
    ("USI", "Usinagem", 4),
    ("SOL", "Solda", 5),
    ("PIN", "Pintura", 6),
    ("MON", "Montagem", 7),
]

# (código, nome, setor, ciclo padrão em segundos, status)
MAQUINAS = [
    ("DES-01", "Desbobinador com linha de corte (chapa 3 m e 6 m)", "DES", "40", "ativa"),
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

# (código, descrição, comprimento da chapa em mm, [(setor, operação, segundos por peça)])
PRODUTOS = [
    (
        "PU-100-6",
        "Perfil U 100x40x2,00 mm - 6 m",
        6000,
        [
            ("DES", "Desbobinar a bobina e cortar chapa de 6 m", "40"),
            ("COR", "Guilhotina: cortar tiras de 180 mm (desenvolvimento do perfil)", "12"),
            ("DOB", "Dobradeira: dobrar o perfil U 100x40", "25"),
        ],
    ),
    (
        "PUE-75-3",
        "Perfil U enrijecido 75x40x15x2,00 mm - 3 m",
        3000,
        [
            ("DES", "Desbobinar a bobina e cortar chapa de 3 m", "30"),
            ("COR", "Guilhotina: cortar tiras de 185 mm", "10"),
            ("DOB", "Dobradeira: 4 dobras do U enrijecido", "35"),
        ],
    ),
    (
        "CANT-50-6",
        "Cantoneira dobrada 50x50x3,00 mm - 6 m",
        6000,
        [
            ("DES", "Desbobinar a bobina e cortar chapa de 6 m", "40"),
            ("COR", "Guilhotina: cortar tiras de 100 mm", "12"),
            ("DOB", "Dobradeira: dobra a 90°", "15"),
        ],
    ),
]


def carregar() -> dict[str, int]:
    novos = {"setores": 0, "maquinas": 0, "produtos": 0}
    with SessionLocal() as db:
        setores = {s.codigo: s for s in db.scalars(select(Setor)).all()}
        for codigo, nome, ordem in SETORES:
            if codigo not in setores:
                setores[codigo] = Setor(codigo=codigo, nome=nome, ordem=ordem)
                db.add(setores[codigo])
                novos["setores"] += 1
            elif setores[codigo].ordem == 0:
                setores[codigo].ordem = ordem
        db.flush()

        existentes = set(db.scalars(select(Maquina.codigo)).all())
        for codigo, nome, setor, ciclo, status in MAQUINAS:
            if codigo not in existentes:
                db.add(Maquina(codigo=codigo, nome=nome, setor_id=setores[setor].id, ciclo_padrao_seg=Decimal(ciclo), status=status))
                novos["maquinas"] += 1

        produtos = set(db.scalars(select(Produto.codigo)).all())
        for codigo, descricao, comprimento, roteiro in PRODUTOS:
            if codigo in produtos:
                continue
            db.add(
                Produto(
                    codigo=codigo,
                    descricao=descricao,
                    unidade="PC",
                    comprimento_mm=comprimento,
                    roteiro=[
                        RoteiroEtapa(sequencia=seq, setor_id=setores[setor].id, operacao=op, tempo_padrao_seg=Decimal(t))
                        for seq, (setor, op, t) in enumerate(roteiro, start=1)
                    ],
                )
            )
            novos["produtos"] += 1
        db.commit()
    return novos


if __name__ == "__main__":
    print("Dados de exemplo novos:", carregar())
