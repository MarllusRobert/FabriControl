def _colunas(client, headers) -> dict[str, list[int]]:
    resp = client.get("/kanban", headers=headers)
    assert resp.status_code == 200, resp.text
    return {c["titulo"]: [card["numero"] for card in c["cards"]] for c in resp.json()["colunas"]}


def test_colunas_seguem_o_fluxo_da_fabrica(client, admin, produto):
    colunas = client.get("/kanban", headers=admin.headers).json()["colunas"]
    assert [c["titulo"] for c in colunas] == ["Planejadas", "Desbobinamento", "Corte", "Dobra", "Concluídas"]
    corte = colunas[2]
    assert [m["codigo"] for m in corte["maquinas"]] == ["COR-01", "COR-02"]


def test_card_anda_de_processo_em_processo(client, admin, fluxo, nova_ordem):
    ordem = nova_ordem()
    url = f"/ordens/{ordem['id']}"
    assert _colunas(client, admin.headers)["Planejadas"] == [1]

    client.post(f"{url}/liberar", headers=admin.headers)
    assert _colunas(client, admin.headers)["Desbobinamento"] == [1]

    client.post(f"{url}/concluir-etapa", headers=admin.headers, json={})
    assert _colunas(client, admin.headers)["Corte"] == [1]

    client.post(f"{url}/concluir-etapa", headers=admin.headers, json={"maquina_id": fluxo["maquinas"]["COR-01"]["id"]})
    assert _colunas(client, admin.headers)["Dobra"] == [1]

    client.post(f"{url}/concluir-etapa", headers=admin.headers, json={})
    colunas = _colunas(client, admin.headers)
    assert colunas["Concluídas"] == [1]
    assert colunas["Dobra"] == []


def test_em_andamento_e_urgente_vem_primeiro(client, admin, nova_ordem):
    normal = nova_ordem(liberar=True)
    urgente = nova_ordem(liberar=True, prioridade="urgente")
    rodando = nova_ordem(liberar=True, prioridade="baixa")
    client.post(f"/ordens/{rodando['id']}/iniciar", headers=admin.headers, json={})
    assert _colunas(client, admin.headers)["Desbobinamento"] == [rodando["numero"], urgente["numero"], normal["numero"]]


def test_cancelada_sai_do_quadro(client, admin, nova_ordem):
    ordem = nova_ordem(liberar=True)
    client.post(f"/ordens/{ordem['id']}/cancelar", headers=admin.headers, json={"motivo": "Cliente desistiu"})
    colunas = _colunas(client, admin.headers)
    assert all(ordem["numero"] not in cards for cards in colunas.values())


def test_operador_ve_o_kanban(client, usuario, produto):
    op = usuario("operador")
    assert client.get("/kanban", headers=op.headers).status_code == 200
