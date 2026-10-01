from conftest import finalizar, iniciar, painel


def _setor(fila: dict, nome: str) -> dict:
    return next(s for s in fila["setores"] if s["setor_nome"] == nome)


def _no_corte(client, headers, equipe, *ordens):
    """Passa as ordens pelo Desbobinamento para que esperem no Corte."""
    for ordem in ordens:
        assert iniciar(client, headers, equipe.maq["DES-01"], ordem, equipe.op1001).status_code == 200
        assert finalizar(client, headers, equipe.maq["DES-01"], equipe.op1001).status_code == 200


def test_fila_mostra_carga_por_maquina(client, admin, equipe, nova_ordem):
    normal = nova_ordem(liberar=True)
    urgente = nova_ordem(liberar=True, prioridade="urgente")
    resp = client.get("/fila", headers=admin.headers)
    assert resp.status_code == 200, resp.text
    assert [s["setor_nome"] for s in resp.json()["setores"]] == ["Desbobinamento", "Corte", "Dobra"]
    des = _setor(resp.json(), "Desbobinamento")
    maquina = des["maquinas"][0]
    assert [f["ordem_numero"] for f in maquina["fila"]] == [urgente["numero"], normal["numero"]]
    assert maquina["carga_min"] == 666.6  # 2 × 500 peças × 40 s
    assert des["a_distribuir"] == []

    iniciar(client, admin.headers, equipe.maq["DES-01"], urgente, equipe.op1001)
    maquina = _setor(client.get("/fila", headers=admin.headers).json(), "Desbobinamento")["maquinas"][0]
    assert maquina["atual"]["ordem_numero"] == urgente["numero"]
    assert maquina["carga_min"] == 666.6


def test_centro_com_varias_maquinas_tem_a_distribuir(client, admin, equipe, nova_ordem):
    ordem = nova_ordem(liberar=True)
    _no_corte(client, admin.headers, equipe, ordem)
    corte = _setor(client.get("/fila", headers=admin.headers).json(), "Corte")
    assert [m["maquina"]["codigo"] for m in corte["maquinas"]] == ["COR-01", "COR-02"]
    assert all(m["fila"] == [] for m in corte["maquinas"])
    assert [f["ordem_numero"] for f in corte["a_distribuir"]] == [ordem["numero"]]
    assert corte["carga_a_distribuir_min"] == 100.0  # 500 peças × 12 s


def test_direcionar_para_maquina(client, admin, equipe, nova_ordem, fluxo):
    ordem = nova_ordem(liberar=True)
    _no_corte(client, admin.headers, equipe, ordem)
    resp = client.put(
        f"/fila/setores/{fluxo['COR']['id']}",
        headers=admin.headers,
        json={"maquinas": [{"maquina_id": equipe.maq["COR-02"]["id"], "ordens": [ordem["id"]]}], "a_distribuir": []},
    )
    assert resp.status_code == 200, resp.text
    corte = _setor(resp.json(), "Corte")
    assert corte["a_distribuir"] == []
    assert corte["maquinas"][1]["carga_min"] == 100.0
    assert painel(client, admin.headers, equipe.maq["COR-01"])["fila"] == []
    assert [f["ordem_numero"] for f in painel(client, admin.headers, equipe.maq["COR-02"])["fila"]] == [ordem["numero"]]
    eventos = client.get(f"/ordens/{ordem['id']}", headers=admin.headers).json()["eventos"]
    assert "direcionada para COR-02" in eventos[0]["descricao"]


def test_arrastar_muda_a_sequencia(client, admin, equipe, nova_ordem, fluxo):
    urgente = nova_ordem(liberar=True, prioridade="urgente")
    normal = nova_ordem(liberar=True)
    des = equipe.maq["DES-01"]
    resp = client.put(
        f"/fila/setores/{fluxo['DES']['id']}",
        headers=admin.headers,
        json={"maquinas": [{"maquina_id": des["id"], "ordens": [normal["id"], urgente["id"]]}]},
    )
    assert resp.status_code == 200, resp.text
    esperado = [normal["numero"], urgente["numero"]]
    assert [f["ordem_numero"] for f in _setor(resp.json(), "Desbobinamento")["maquinas"][0]["fila"]] == esperado
    assert [f["ordem_numero"] for f in painel(client, admin.headers, des)["fila"]] == esperado

    # OP nova sem posição entra depois das já sequenciadas, mesmo sendo urgente.
    outra = nova_ordem(liberar=True, prioridade="urgente")
    assert [f["ordem_numero"] for f in painel(client, admin.headers, des)["fila"]] == [*esperado, outra["numero"]]


def test_sequencia_invalida(client, admin, equipe, nova_ordem, fluxo):
    ordem = nova_ordem(liberar=True)
    planejada = nova_ordem()
    url = f"/fila/setores/{fluxo['DES']['id']}"
    des = equipe.maq["DES-01"]["id"]
    outro_centro = {"maquinas": [{"maquina_id": equipe.maq["COR-01"]["id"], "ordens": [ordem["id"]]}]}
    assert client.put(url, headers=admin.headers, json=outro_centro).status_code == 400
    nao_esta = {"maquinas": [{"maquina_id": des, "ordens": [planejada["id"]]}]}
    assert client.put(url, headers=admin.headers, json=nao_esta).status_code == 400
    repetida = {"maquinas": [{"maquina_id": des, "ordens": [ordem["id"]]}], "a_distribuir": [ordem["id"]]}
    assert client.put(url, headers=admin.headers, json=repetida).status_code == 400
    assert client.put("/fila/setores/nao-existe", headers=admin.headers, json={"maquinas": []}).status_code == 404


def test_permissoes_da_fila(client, usuario, equipe, fluxo):
    payload = {"maquinas": [], "a_distribuir": []}
    url = f"/fila/setores/{fluxo['DES']['id']}"
    pcp = usuario("pcp")
    assert client.get("/fila", headers=pcp.headers).status_code == 200
    assert client.put(url, headers=pcp.headers, json=payload).status_code == 200
    supervisor = usuario("supervisor")
    assert client.get("/fila", headers=supervisor.headers).status_code == 200
    assert client.put(url, headers=supervisor.headers, json=payload).status_code == 403
    operador = usuario("operador")
    assert client.get("/fila", headers=operador.headers).status_code == 403
    assert client.get("/fila").status_code == 401
