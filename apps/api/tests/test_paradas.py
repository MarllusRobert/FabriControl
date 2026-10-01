import pytest

from conftest import iniciar, painel


@pytest.fixture
def motivos(client, admin) -> dict[str, dict]:
    criados = {}
    for codigo, descricao, tipo in [("SET", "Setup", "planejada"), ("QUE", "Quebra de máquina", "nao_planejada")]:
        resp = client.post("/motivos/parada", headers=admin.headers, json={"codigo": codigo, "descricao": descricao, "tipo": tipo})
        assert resp.status_code == 201, resp.text
        criados[codigo] = resp.json()
    return criados


def parar(client, headers, maquina, operador, motivo, **extra):
    return client.post(
        f"/operacao/maquinas/{maquina['id']}/parar",
        headers=headers,
        json={"operador_id": operador["id"], "motivo_parada_id": motivo["id"] if motivo else "", **extra},
    )


def voltar(client, headers, maquina, operador):
    return client.post(f"/operacao/maquinas/{maquina['id']}/voltar", headers=headers, json={"operador_id": operador["id"]})


def test_parada_sem_ordem_rodando(client, usuario, equipe, motivos):
    op = usuario("operador")
    resp = parar(client, op.headers, equipe.maq["DES-01"], equipe.op1001, motivos["SET"], observacao="Troca de bobina")
    assert resp.status_code == 200, resp.text
    parada = resp.json()["parada"]
    assert (parada["motivo_descricao"], parada["planejada"], parada["fim"]) == ("Setup", True, None)
    assert parada["operador_nome"] == "Carlos Alves"
    assert parada["observacao"] == "Troca de bobina"


def test_parada_em_aberto_aparece_para_o_supervisor(client, admin, usuario, equipe, motivos):
    parar(client, admin.headers, equipe.maq["DES-01"], equipe.op1001, motivos["QUE"])
    sup = usuario("supervisor")
    abertas = client.get("/paradas", headers=sup.headers, params={"abertas": True}).json()
    assert [(p["maquina_codigo"], p["tipo_label"]) for p in abertas] == [("DES-01", "Não planejada")]


def test_parada_pausa_e_retoma_a_ordem(client, admin, equipe, motivos, nova_ordem):
    ordem = nova_ordem(liberar=True)
    iniciar(client, admin.headers, equipe.maq["DES-01"], ordem, equipe.op1001)
    resp = parar(client, admin.headers, equipe.maq["DES-01"], equipe.op1001, motivos["QUE"])
    atual = resp.json()["atual"]
    assert (atual["ordem_status"], atual["motivo_pausa"]) == ("pausada", "Máquina parada: Quebra de máquina")
    assert resp.json()["parada"]["ordem_numero"] == ordem["numero"]

    resp = voltar(client, admin.headers, equipe.maq["DES-01"], equipe.op1001)
    assert resp.status_code == 200, resp.text
    assert resp.json()["parada"] is None
    assert resp.json()["atual"]["ordem_status"] == "em_producao"
    assert client.get("/paradas", headers=admin.headers, params={"abertas": True}).json() == []
    historico = client.get("/paradas", headers=admin.headers).json()
    assert historico[0]["fim"] is not None and historico[0]["duracao_min"] >= 0
    eventos = client.get(f"/ordens/{ordem['id']}", headers=admin.headers).json()["eventos"]
    assert eventos[0]["tipo"] == "retomada"


def test_motivo_obrigatorio(client, admin, equipe):
    assert parar(client, admin.headers, equipe.maq["DES-01"], equipe.op1001, None).status_code == 400


def test_uma_parada_aberta_por_maquina(client, admin, equipe, motivos):
    parar(client, admin.headers, equipe.maq["DES-01"], equipe.op1001, motivos["SET"])
    resp = parar(client, admin.headers, equipe.maq["DES-01"], equipe.op1001, motivos["QUE"])
    assert resp.status_code == 400
    assert "já está parada" in resp.json()["detail"]
    # Outra máquina pode parar ao mesmo tempo.
    assert parar(client, admin.headers, equipe.maq["COR-01"], equipe.op1002, motivos["QUE"]).status_code == 200


def test_voltar_sem_parada(client, admin, equipe):
    assert voltar(client, admin.headers, equipe.maq["DES-01"], equipe.op1001).status_code == 400


def test_maquina_parada_nao_inicia_ordem(client, admin, equipe, motivos, nova_ordem):
    parar(client, admin.headers, equipe.maq["DES-01"], equipe.op1001, motivos["SET"])
    resp = iniciar(client, admin.headers, equipe.maq["DES-01"], nova_ordem(liberar=True), equipe.op1001)
    assert resp.status_code == 400
    assert "parada" in resp.json()["detail"]


def test_painel_mostra_a_parada(client, admin, equipe, motivos):
    parar(client, admin.headers, equipe.maq["DES-01"], equipe.op1001, motivos["SET"])
    assert painel(client, admin.headers, equipe.maq["DES-01"])["parada"]["motivo_codigo"] == "SET"
    assert painel(client, admin.headers, equipe.maq["COR-01"])["parada"] is None


def test_qualidade_ve_mas_nao_para(client, usuario, equipe, motivos):
    qual = usuario("qualidade")
    assert client.get("/paradas", headers=qual.headers).status_code == 200
    assert parar(client, qual.headers, equipe.maq["DES-01"], equipe.op1001, motivos["SET"]).status_code == 403


def test_operador_ve_motivos_de_parada(client, usuario, motivos):
    op = usuario("operador")
    resp = client.get("/operacao/motivos-parada", headers=op.headers)
    assert [m["codigo"] for m in resp.json()] == ["SET", "QUE"]
