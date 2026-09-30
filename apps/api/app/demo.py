"""Dados de exemplo de uma metalúrgica que fabrica perfis dobrados.

Uso: docker compose exec api python -m app.demo  (pode rodar mais de uma vez)
"""
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.constants import TZ
from app.db import SessionLocal
from app.models import (
    Maquina,
    Operador,
    OrdemEtapa,
    OrdemEvento,
    OrdemProducao,
    Produto,
    RoteiroEtapa,
    Setor,
    Turno,
    Usuario,
)

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


# (código, nome, início, fim)
TURNOS = [
    ("T1", "1º turno", time(6), time(14)),
    ("T2", "2º turno", time(14), time(22)),
    ("T3", "3º turno", time(22), time(6)),
]

# (matrícula, nome, turno, setor)
OPERADORES = [
    ("1001", "Carlos Henrique Alves", "T1", "DES"),
    ("1002", "Marcos Vinícius Rocha", "T1", "COR"),
    ("1003", "Fernanda Lopes", "T1", "DOB"),
    ("1004", "Rafael Moreira", "T2", "DES"),
    ("1005", "Juliana Martins", "T2", "COR"),
    ("1006", "Diego Carvalho", "T2", "DOB"),
    ("1007", "Anderson Pereira", "T3", "COR"),
    ("1008", "Lucas Ferreira", "T3", "DOB"),
]

# (produto, quantidade, prioridade, dias até o prazo, etapas concluídas, estado da etapa atual, máquinas usadas, motivo da pausa)
ORDENS = [
    ("PU-100-6", 600, "alta", 3, None, None, [], None),
    ("CANT-50-6", 300, "normal", 6, None, None, [], None),
    ("PUE-75-3", 400, "urgente", -1, 0, "em_andamento", ["DES-01"], None),
    ("PU-100-6", 800, "normal", 4, 1, "na_fila", ["DES-01"], None),
    ("CANT-50-6", 250, "alta", 2, 1, "em_andamento", ["DES-01", "COR-01"], None),
    ("PUE-75-3", 500, "normal", 5, 2, "na_fila", ["DES-01", "COR-01"], None),
    ("PU-100-6", 350, "normal", 1, 2, "em_andamento", ["DES-01", "COR-01", "DOB-01"], None),
    ("CANT-50-6", 200, "baixa", 8, 2, "na_fila", ["DES-01", "COR-02"], "Aguardando ajuste do ferramental da dobradeira"),
    ("PU-100-6", 1000, "normal", 0, 3, None, ["DES-01", "COR-01", "DOB-02"], None),
]


def carregar_ordens(db) -> int:
    if db.scalar(select(OrdemProducao.id).limit(1)):
        return 0
    produtos = {p.codigo: p for p in db.scalars(select(Produto)).all()}
    maquinas = {m.codigo: m for m in db.scalars(select(Maquina)).all()}
    autor = db.scalar(select(Usuario).where(Usuario.perfil == "administrador").limit(1))
    agora = datetime.now(timezone.utc)
    hoje = datetime.now(TZ).date()
    for numero, (codigo, qtd, prioridade, dias, feitas, estado, usadas, pausa) in enumerate(ORDENS, start=1):
        produto = produtos[codigo]
        inicio = agora - timedelta(hours=len(ORDENS) - numero + 2)
        ordem = OrdemProducao(
            numero=numero,
            produto_id=produto.id,
            quantidade=qtd,
            prazo=hoje + timedelta(days=dias),
            prioridade=prioridade,
            status="planejada",
            criado_por_id=autor.id if autor else None,
            criado_em=inicio,
            etapas=[
                OrdemEtapa(sequencia=e.sequencia, setor_id=e.setor_id, operacao=e.operacao, tempo_padrao_seg=e.tempo_padrao_seg)
                for e in produto.roteiro
            ],
        )
        eventos = [("criada", f"OP criada: {qtd} PC de {codigo}.")]
        if feitas is not None:
            ordem.status = "em_producao" if feitas or estado == "em_andamento" else "liberada"
            eventos.append(("liberada", f"Liberada para a fábrica: entra na fila de {produto.roteiro[0].setor.nome}."))
            momento = inicio
            for etapa, maq in zip(ordem.etapas, usadas):
                momento += timedelta(minutes=35)
                etapa.maquina_id = maquinas[maq].id
                etapa.iniciada_em = momento
                if etapa.sequencia <= feitas:
                    etapa.status = "concluida"
                    etapa.concluida_em = momento + timedelta(minutes=30)
                    eventos.append(("etapa_concluida", f"Etapa {etapa.sequencia} concluída na {maq}."))
                else:
                    etapa.status = "em_andamento"
                    eventos.append(("etapa_iniciada", f"Etapa {etapa.sequencia} iniciada na {maq}."))
            if feitas < len(ordem.etapas):
                atual = ordem.etapas[feitas]
                if atual.status != "em_andamento":
                    atual.status = "na_fila"
            else:
                ordem.status = "concluida"
                ordem.concluida_em = momento + timedelta(minutes=30)
                eventos.append(("concluida", "OP concluída: produto final pronto."))
            if pausa:
                ordem.status = "pausada"
                ordem.motivo_pausa = pausa
                eventos.append(("pausada", f"Pausada: {pausa}"))
        db.add(ordem)
        db.flush()
        for i, (tipo, descricao) in enumerate(eventos):
            db.add(
                OrdemEvento(
                    ordem_id=ordem.id,
                    usuario_id=autor.id if autor else None,
                    tipo=tipo,
                    descricao=descricao,
                    em=inicio + timedelta(minutes=i * 30),
                )
            )
    return len(ORDENS)


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
        db.flush()

        turnos = {t.codigo: t for t in db.scalars(select(Turno)).all()}
        novos["turnos"] = 0
        for codigo, nome, inicio, fim in TURNOS:
            if codigo not in turnos:
                turnos[codigo] = Turno(codigo=codigo, nome=nome, inicio=inicio, fim=fim)
                db.add(turnos[codigo])
                novos["turnos"] += 1
        db.flush()

        matriculas = set(db.scalars(select(Operador.matricula)).all())
        novos["operadores"] = 0
        for matricula, nome, turno, setor in OPERADORES:
            if matricula not in matriculas:
                db.add(Operador(matricula=matricula, nome=nome, turno_id=turnos[turno].id, setor_id=setores[setor].id))
                novos["operadores"] += 1

        novos["ordens"] = carregar_ordens(db)
        db.commit()
    return novos


if __name__ == "__main__":
    print("Dados de exemplo novos:", carregar())
