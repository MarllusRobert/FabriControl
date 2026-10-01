"""Simulador de CLP: o que cada máquina mandaria ao sistema, minuto a minuto.

Gera um CSV por máquina e por dia (<saida>/<MAQUINA>/<AAAA-MM-DD>.csv) com estado, ciclos e peças.
Parte das linhas sai suja de propósito (lacunas, duplicatas, códigos fora do padrão, valores
impossíveis...), como acontece com dados de chão de fábrica. Ao lado ficam:

- gabarito.csv: totais verdadeiros por máquina e dia, calculados antes da sujeira;
- anomalias.csv: cada sujeira injetada e cada evento de contador (zerado ou estourado);
- parametros.json: o que foi usado para gerar, para repetir a mesma massa de dados.

Uso: python -m app.simulador_clp --maquinas 5 --dias 7 --saida dados/clp --semente 42
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from app.constants import TZ

COLUNAS = ["timestamp", "maquina", "estado", "alarme", "ciclos", "pecas_boas", "pecas_refugo", "contador"]
ESTADOS = ("RUN", "SETUP", "STOP", "IDLE", "OFF")
ALARMES = {
    "E101": "Queda de energia",
    "H210": "Pressão hidráulica baixa",
    "M305": "Atolamento de chapa",
    "S410": "Cortina de segurança acionada",
    "T520": "Ferramenta quebrada",
}
PESO_ALARME = [1, 3, 4, 3, 2]  # mesma ordem de ALARMES: queda de energia é a mais rara
CONTADOR_MAX = 65535  # contador de 16 bits: volta a zero depois disso

INICIO_TURNO = {6 * 60, 14 * 60, 22 * 60}
REFEICAO = [(10 * 60 + 30, 11 * 60), (18 * 60 + 30, 19 * 60), (2 * 60, 2 * 60 + 30)]

# Probabilidade, a cada minuto produzindo, de começar cada tipo de evento.
P_FALHA = 1 / 180
P_SETUP = 1 / 240
P_ESPERA = 1 / 400
P_QUEBRA_NO_DIA = 0.05

TIPOS_SUJEIRA = (
    "lacuna",
    "duplicada",
    "fora_de_ordem",
    "estado_fora_do_padrao",
    "valor_negativo",
    "pico",
    "nulo",
    "timestamp_formato",
    "decimal_virgula",
    "inconsistente",
)

# Fábrica de perfis: código, ciclo ideal (s), peças por ciclo, turnos.
FABRICA = [
    ("DES-01", 40, 1, 2),
    ("COR-01", 12, 1, 3),
    ("COR-02", 20, 2, 3),
    ("DOB-01", 25, 1, 2),
    ("DOB-02", 30, 1, 2),
    ("SOL-01", 90, 1, 2),
    ("PIN-01", 15, 4, 1),
    ("USI-01", 75, 1, 2),
]


@dataclass
class MaquinaSim:
    codigo: str
    ciclo_seg: float
    pecas_por_ciclo: int = 1
    turnos: int = 2  # 1: só 1º turno; 2: 06h às 22h; 3: 24 horas


@dataclass
class Resumo:
    arquivos: int = 0
    linhas: int = 0
    anomalias: Counter = field(default_factory=Counter)


def maquinas_padrao(n: int) -> list[MaquinaSim]:
    maquinas = [MaquinaSim(*m) for m in FABRICA[:n]]
    maquinas += [MaquinaSim(f"MAQ-{i:02d}", 30) for i in range(len(maquinas) + 1, n + 1)]
    return maquinas


def maquinas_do_banco(n: int) -> list[MaquinaSim]:
    from sqlalchemy import select

    from app.constants import STATUS_RECEBE_ORDEM
    from app.db import SessionLocal
    from app.models import Maquina

    with SessionLocal() as db:
        cadastradas = db.scalars(
            select(Maquina).where(Maquina.status.in_(STATUS_RECEBE_ORDEM)).order_by(Maquina.codigo).limit(n)
        ).all()
        return [MaquinaSim(m.codigo, float(m.ciclo_padrao_seg), turnos=3 if m.codigo.startswith("COR") else 2) for m in cadastradas]


def turno(momento: datetime, maquina: MaquinaSim) -> str | None:
    """Turno em que a máquina trabalha neste minuto (None = desligada). Sábado só o 1º turno; domingo parado."""
    hora, dia = momento.hour, momento.weekday()
    if 6 <= hora < 14:
        return "T1" if dia <= 5 else None
    if 14 <= hora < 22:
        return "T2" if maquina.turnos >= 2 and dia <= 4 else None
    if hora >= 22:
        return "T3" if maquina.turnos == 3 and dia <= 4 else None
    return "T3" if maquina.turnos == 3 and 1 <= dia <= 5 else None


def _na_refeicao(minuto_do_dia: int) -> bool:
    return any(a <= minuto_do_dia < b for a, b in REFEICAO)


class _Maquina:
    """Estado interno do CLP de uma máquina; atravessa a meia-noite."""

    def __init__(self, maquina: MaquinaSim, rng: random.Random):
        self.m = maquina
        self.rng = rng
        self.desempenho = rng.uniform(0.82, 0.96)
        self.taxa_refugo = rng.uniform(0.005, 0.03)
        self.estado = "OFF"
        self.restante = 0
        self.alarme = ""
        self.desde_setup = 999
        self.contador = rng.randrange(CONTADOR_MAX)

    def _evento(self, estado: str, minutos: int, alarme: str = "") -> None:
        self.estado, self.restante, self.alarme = estado, max(1, minutos), alarme

    def minuto(self, momento: datetime, quebra: tuple[int, int] | None, anomalias: list[dict]) -> tuple[dict, str]:
        """Linha limpa deste minuto e a categoria dele para o gabarito."""
        rng = self.rng
        mdd = momento.hour * 60 + momento.minute
        ciclos = boas = refugo = 0

        if turno(momento, self.m) is None:
            self._evento("OFF", 0)
            estado, categoria = "OFF", "off"
        elif _na_refeicao(mdd):
            estado, categoria = "IDLE", "pausa_planejada"
        else:
            if self.estado == "OFF" or (mdd in INICIO_TURNO and self.estado != "STOP"):
                self._evento("SETUP", rng.randint(5, 15))
            elif quebra and mdd == quebra[0]:
                self._evento("STOP", quebra[1], rng.choice(["T520", "E101"]))
            elif self.estado != "RUN" and self.restante <= 0:
                if self.estado == "STOP" and self.alarme == "E101":
                    self.contador = 0
                    anomalias.append(_anomalia(self.m, momento, "contador_zerado", "CLP religado após queda de energia"))
                if self.estado == "SETUP":
                    self.desde_setup = 0
                self._evento("RUN", 0)
            elif self.estado == "RUN":
                r = rng.random()
                if r < P_FALHA:
                    duracao = min(120, round(rng.lognormvariate(math.log(8), 0.8)))
                    self._evento("STOP", duracao, rng.choices(list(ALARMES), weights=PESO_ALARME)[0])
                elif r < P_FALHA + P_SETUP:
                    self._evento("SETUP", rng.randint(10, 40))
                elif r < P_FALHA + P_SETUP + P_ESPERA:
                    self._evento("IDLE", rng.randint(5, 30))

            estado = self.estado
            categoria = {"RUN": "run", "SETUP": "setup", "STOP": "stop", "IDLE": "idle"}[estado]
            if estado == "RUN":
                maximo = 60 / self.m.ciclo_seg
                esperado = min(maximo, maximo * self.desempenho * rng.uniform(0.9, 1.04))
                ciclos = int(esperado) + (rng.random() < esperado - int(esperado))
                chance = self.taxa_refugo * (4 if self.desde_setup < 15 else 1)
                pecas = ciclos * self.m.pecas_por_ciclo
                refugo = sum(rng.random() < chance for _ in range(pecas))
                boas = pecas - refugo
                self.desde_setup += 1
                novo = self.contador + ciclos
                if novo > CONTADOR_MAX:
                    anomalias.append(_anomalia(self.m, momento, "contador_estouro", f"passou de {CONTADOR_MAX} e voltou a zero"))
                self.contador = novo % (CONTADOR_MAX + 1)
            else:
                self.restante -= 1

        linha = {
            "timestamp": momento.isoformat(),
            "maquina": self.m.codigo,
            "estado": estado,
            "alarme": self.alarme if estado == "STOP" else "",
            "ciclos": ciclos,
            "pecas_boas": boas,
            "pecas_refugo": refugo,
            "contador": self.contador,
        }
        return linha, categoria


def _anomalia(maquina: MaquinaSim, momento: datetime, tipo: str, detalhe: str = "") -> dict:
    return {
        "maquina": maquina.codigo,
        "data": momento.date().isoformat(),
        "timestamp": momento.isoformat(),
        "tipo": tipo,
        "detalhe": detalhe,
    }


def _sujar(linhas: list[dict], taxa: float, rng: random.Random, maquina: MaquinaSim, anomalias: list[dict]) -> list[dict]:
    saida: list[dict] = []
    i = 0
    while i < len(linhas):
        linha = dict(linhas[i])
        if not taxa or rng.random() >= taxa:
            saida.append(linha)
            i += 1
            continue
        momento = datetime.fromisoformat(linha["timestamp"])
        tipo = rng.choice(TIPOS_SUJEIRA)
        detalhe = ""
        if tipo == "lacuna":
            n = rng.randint(1, 20)
            anomalias.append(_anomalia(maquina, momento, tipo, f"{n} min sem registro"))
            i += n
            continue
        if tipo == "duplicada":
            saida.append(dict(linha))
        elif tipo == "fora_de_ordem" and saida:
            saida.insert(len(saida) - 1, linha)
            anomalias.append(_anomalia(maquina, momento, tipo, "chegou antes do minuto anterior"))
            i += 1
            continue
        elif tipo == "estado_fora_do_padrao":
            linha["estado"] = rng.choice(["run", " RUN", "Run ", "STOPPED", "?", ""])
            detalhe = f"estado {linha['estado']!r}"
        elif tipo == "valor_negativo":
            campo = rng.choice(["ciclos", "pecas_boas", "pecas_refugo"])
            linha[campo] = -rng.randint(1, 5)
            detalhe = campo
        elif tipo == "pico":
            linha["ciclos"] = rng.choice([999, 9999, 32767])
            detalhe = f"ciclos {linha['ciclos']}"
        elif tipo == "nulo":
            campo = rng.choice(["estado", "ciclos", "pecas_boas", "pecas_refugo", "contador"])
            linha[campo] = rng.choice(["", "NULL", "NaN"])
            detalhe = campo
        elif tipo == "timestamp_formato":
            formatos = [
                momento.strftime("%d/%m/%Y %H:%M:%S"),
                momento.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                (momento + timedelta(seconds=rng.randint(1, 59))).isoformat(),
            ]
            linha["timestamp"] = rng.choice(formatos)
            detalhe = linha["timestamp"]
        elif tipo == "decimal_virgula":
            linha["ciclos"] = f"{linha['ciclos']},0"
        elif tipo == "inconsistente":
            linha["estado"], linha["alarme"] = "STOP", ""
            linha["ciclos"] = max(1, int(linha["ciclos"]))
            detalhe = "STOP sem alarme e com ciclos"
        else:
            tipo = "duplicada"
            saida.append(dict(linha))
        anomalias.append(_anomalia(maquina, momento, tipo, detalhe))
        saida.append(linha)
        i += 1

    if taxa and saida and rng.random() < min(1.0, taxa * 5):
        pos = rng.randrange(len(saida))
        momento = datetime.fromisoformat(linhas[0]["timestamp"])
        anomalias.append(_anomalia(maquina, momento, "cabecalho_repetido", f"linha {pos + 2} do arquivo"))
        saida.insert(pos, {c: c for c in COLUNAS})
    return saida


def _gravar_csv(caminho: Path, colunas: list[str], linhas: list[dict]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=colunas)
        escritor.writeheader()
        escritor.writerows(linhas)


CATEGORIAS = ["run", "setup", "stop", "idle", "pausa_planejada", "off"]
COLUNAS_GABARITO = [
    "maquina",
    "data",
    "ciclo_ideal_seg",
    "pecas_por_ciclo",
    "minutos_planejados",
    *[f"minutos_{c}" for c in CATEGORIAS],
    "ciclos",
    "pecas_boas",
    "pecas_refugo",
]


def gerar(
    saida: Path,
    maquinas: list[MaquinaSim],
    inicio: date,
    dias: int,
    sujeira: float = 0.01,
    semente: int = 42,
) -> Resumo:
    if not maquinas or dias < 1 or not 0 <= sujeira <= 0.3:
        raise ValueError("Informe ao menos uma máquina, um dia e sujeira entre 0 e 0,3.")
    saida = Path(saida)
    resumo = Resumo()
    gabarito: list[dict] = []
    anomalias: list[dict] = []

    for maquina in maquinas:
        rng = random.Random(f"{semente}-{maquina.codigo}")
        rng_sujeira = random.Random(f"{semente}-{maquina.codigo}-sujeira")
        clp = _Maquina(maquina, rng)
        for d in range(dias):
            dia = inicio + timedelta(days=d)
            quebra = None
            if rng.random() < P_QUEBRA_NO_DIA:
                comeco = rng.randrange(6 * 60, 20 * 60)
                quebra = (comeco, rng.randint(120, 360))
            meia_noite = datetime(dia.year, dia.month, dia.day, tzinfo=TZ)
            linhas: list[dict] = []
            minutos: Counter = Counter()
            for m in range(24 * 60):
                linha, categoria = clp.minuto(meia_noite + timedelta(minutes=m), quebra, anomalias)
                linhas.append(linha)
                minutos[categoria] += 1
            gabarito.append(
                {
                    "maquina": maquina.codigo,
                    "data": dia.isoformat(),
                    "ciclo_ideal_seg": maquina.ciclo_seg,
                    "pecas_por_ciclo": maquina.pecas_por_ciclo,
                    "minutos_planejados": sum(minutos[c] for c in ("run", "setup", "stop", "idle")),
                    **{f"minutos_{c}": minutos[c] for c in CATEGORIAS},
                    "ciclos": sum(x["ciclos"] for x in linhas),
                    "pecas_boas": sum(x["pecas_boas"] for x in linhas),
                    "pecas_refugo": sum(x["pecas_refugo"] for x in linhas),
                }
            )
            sujas = _sujar(linhas, sujeira, rng_sujeira, maquina, anomalias)
            _gravar_csv(saida / maquina.codigo / f"{dia.isoformat()}.csv", COLUNAS, sujas)
            resumo.arquivos += 1
            resumo.linhas += len(sujas)

    _gravar_csv(saida / "gabarito.csv", COLUNAS_GABARITO, gabarito)
    _gravar_csv(saida / "anomalias.csv", ["maquina", "data", "timestamp", "tipo", "detalhe"], anomalias)
    parametros = {
        "maquinas": [asdict(m) for m in maquinas],
        "inicio": inicio.isoformat(),
        "dias": dias,
        "sujeira": sujeira,
        "semente": semente,
        "colunas": COLUNAS,
        "estados": list(ESTADOS),
        "alarmes": ALARMES,
    }
    (saida / "parametros.json").write_text(json.dumps(parametros, ensure_ascii=False, indent=2), encoding="utf-8")
    resumo.anomalias = Counter(a["tipo"] for a in anomalias)
    return resumo


def main(argv: list[str] | None = None) -> Resumo:
    p = argparse.ArgumentParser(prog="python -m app.simulador_clp", description="Gera dados de CLP das máquinas em CSV.")
    p.add_argument("--maquinas", type=int, default=5, help="quantidade de máquinas (padrão 5)")
    p.add_argument("--dias", type=int, default=7, help="quantidade de dias (padrão 7)")
    p.add_argument("--inicio", type=date.fromisoformat, help="primeiro dia, AAAA-MM-DD (padrão: termina ontem)")
    p.add_argument("--saida", type=Path, default=Path("dados/clp"), help="pasta de saída (padrão dados/clp)")
    p.add_argument("--semente", type=int, default=42, help="mesma semente, mesmos dados")
    p.add_argument("--sujeira", type=float, default=0.01, help="fração de linhas sujas, de 0 a 0,3 (padrão 0,01)")
    p.add_argument("--do-banco", action="store_true", help="usa as máquinas ativas cadastradas no FabriControl")
    args = p.parse_args(argv)
    if not 1 <= args.maquinas <= 200:
        p.error("--maquinas deve ficar entre 1 e 200")
    if not 1 <= args.dias <= 366:
        p.error("--dias deve ficar entre 1 e 366")
    if not 0 <= args.sujeira <= 0.3:
        p.error("--sujeira deve ficar entre 0 e 0,3")

    maquinas = maquinas_do_banco(args.maquinas) if args.do_banco else maquinas_padrao(args.maquinas)
    if not maquinas:
        p.error("nenhuma máquina ativa cadastrada")
    inicio = args.inicio or datetime.now(TZ).date() - timedelta(days=args.dias)
    resumo = gerar(args.saida, maquinas, inicio, args.dias, args.sujeira, args.semente)
    sujeiras = ", ".join(f"{tipo} {n}" for tipo, n in sorted(resumo.anomalias.items())) or "nenhuma"
    print(f"{resumo.arquivos} arquivos e {resumo.linhas} linhas em {args.saida} ({len(maquinas)} máquinas, {args.dias} dias).")
    print(f"Anomalias: {sujeiras}.")
    return resumo


if __name__ == "__main__":
    main(sys.argv[1:])
