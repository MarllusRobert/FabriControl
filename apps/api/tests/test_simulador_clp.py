import csv
import math
from datetime import date, datetime, timedelta

import pytest

from app.simulador_clp import COLUNAS, ESTADOS, TIPOS_SUJEIRA, MaquinaSim, gerar, main, maquinas_padrao

SEGUNDA = date(2026, 9, 21)


def _ler(caminho):
    with caminho.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_csv_por_maquina_a_cada_minuto(tmp_path):
    maquinas = maquinas_padrao(3)
    resumo = gerar(tmp_path, maquinas, SEGUNDA, dias=2, sujeira=0)
    assert resumo.arquivos == 6
    for m in maquinas:
        for d in range(2):
            dia = SEGUNDA + timedelta(days=d)
            caminho = tmp_path / m.codigo / f"{dia}.csv"
            with caminho.open(encoding="utf-8") as f:
                assert f.readline().strip() == ",".join(COLUNAS)
            linhas = _ler(caminho)
            assert len(linhas) == 24 * 60
            momentos = [datetime.fromisoformat(x["timestamp"]) for x in linhas]
            assert all(b - a == timedelta(minutes=1) for a, b in zip(momentos, momentos[1:]))
            assert momentos[0].isoformat() == f"{dia}T00:00:00-03:00"
            for x in linhas:
                assert x["maquina"] == m.codigo and x["estado"] in ESTADOS
                ciclos, boas, refugo = int(x["ciclos"]), int(x["pecas_boas"]), int(x["pecas_refugo"])
                assert 0 <= ciclos <= math.ceil(60 / m.ciclo_seg)
                assert boas + refugo == ciclos * m.pecas_por_ciclo
                assert ciclos == 0 or x["estado"] == "RUN"
                assert (x["alarme"] != "") == (x["estado"] == "STOP")


def test_turnos_e_fim_de_semana(tmp_path):
    so_primeiro = MaquinaSim("PIN-01", 15, 4, turnos=1)
    gerar(tmp_path, [so_primeiro], SEGUNDA, dias=7, sujeira=0)
    segunda = _ler(tmp_path / "PIN-01" / "2026-09-21.csv")
    assert {x["estado"] for x in segunda[: 6 * 60]} == {"OFF"}
    assert {x["estado"] for x in segunda[14 * 60 :]} == {"OFF"}
    assert segunda[6 * 60]["estado"] == "SETUP"
    assert {x["estado"] for x in segunda[10 * 60 + 30 : 11 * 60]} == {"IDLE"}  # refeição
    assert "RUN" in {x["estado"] for x in segunda}
    domingo = _ler(tmp_path / "PIN-01" / "2026-09-27.csv")
    assert {x["estado"] for x in domingo} == {"OFF"}


def test_gabarito_bate_com_os_dados_limpos(tmp_path):
    maquinas = maquinas_padrao(2)
    gerar(tmp_path, maquinas, SEGUNDA, dias=3, sujeira=0)
    gabarito = _ler(tmp_path / "gabarito.csv")
    assert len(gabarito) == 6
    for g in gabarito:
        linhas = _ler(tmp_path / g["maquina"] / f"{g['data']}.csv")
        assert int(g["ciclos"]) == sum(int(x["ciclos"]) for x in linhas)
        assert int(g["pecas_boas"]) == sum(int(x["pecas_boas"]) for x in linhas)
        assert int(g["minutos_run"]) == sum(x["estado"] == "RUN" for x in linhas)
        assert int(g["minutos_off"]) == sum(x["estado"] == "OFF" for x in linhas)
        minutos = sum(int(g[f"minutos_{c}"]) for c in ("run", "setup", "stop", "idle", "pausa_planejada", "off"))
        assert minutos == 24 * 60
        assert int(g["minutos_planejados"]) == minutos - int(g["minutos_pausa_planejada"]) - int(g["minutos_off"])


def test_mesma_semente_mesmos_dados(tmp_path):
    maquinas = maquinas_padrao(2)
    gerar(tmp_path / "a", maquinas, SEGUNDA, dias=1, sujeira=0.05, semente=7)
    gerar(tmp_path / "b", maquinas, SEGUNDA, dias=1, sujeira=0.05, semente=7)
    gerar(tmp_path / "c", maquinas, SEGUNDA, dias=1, sujeira=0.05, semente=8)
    arquivo = "COR-01/2026-09-21.csv"
    assert (tmp_path / "a" / arquivo).read_bytes() == (tmp_path / "b" / arquivo).read_bytes()
    assert (tmp_path / "a" / arquivo).read_bytes() != (tmp_path / "c" / arquivo).read_bytes()


def test_sujeira_proposital_fica_registrada(tmp_path):
    maquinas = maquinas_padrao(3)
    gerar(tmp_path / "limpo", maquinas, SEGUNDA, dias=3, sujeira=0)
    resumo = gerar(tmp_path / "sujo", maquinas, SEGUNDA, dias=3, sujeira=0.05)
    assert set(TIPOS_SUJEIRA) <= set(resumo.anomalias)
    anomalias = _ler(tmp_path / "sujo" / "anomalias.csv")
    assert len(anomalias) == sum(resumo.anomalias.values())

    # A sujeira não muda a verdade: o gabarito é o mesmo dos dados limpos.
    assert _ler(tmp_path / "sujo" / "gabarito.csv") == _ler(tmp_path / "limpo" / "gabarito.csv")

    sujas = [x for m in maquinas for p in (tmp_path / "sujo" / m.codigo).glob("*.csv") for x in _ler(p)]
    estados = {x["estado"] for x in sujas}
    assert estados - set(ESTADOS) - {"estado"}  # códigos fora do padrão
    assert any(x["ciclos"].startswith("-") for x in sujas if x["ciclos"])
    assert any(x["ciclos"] in ("", "NULL", "NaN") or "," in x["ciclos"] for x in sujas)
    assert any(x["timestamp"].endswith("Z") or "/" in x["timestamp"] for x in sujas)


def test_parametros_de_maquinas_e_dias(tmp_path, capsys):
    resumo = main(["--maquinas", "10", "--dias", "1", "--inicio", "2026-09-21", "--saida", str(tmp_path), "--sujeira", "0"])
    assert resumo.arquivos == 10
    pastas = sorted(p.name for p in tmp_path.iterdir() if p.is_dir())
    assert len(pastas) == 10 and "MAQ-10" in pastas
    assert (tmp_path / "parametros.json").exists()
    assert "10 arquivos" in capsys.readouterr().out
    for errado in (["--maquinas", "0"], ["--dias", "0"], ["--sujeira", "0.9"]):
        with pytest.raises(SystemExit):
            main([*errado, "--saida", str(tmp_path)])
    with pytest.raises(ValueError):
        gerar(tmp_path, [], SEGUNDA, dias=1)
