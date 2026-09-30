from datetime import date, timedelta


def test_cria_ordem_com_copia_do_roteiro(client, admin, produto):
    resp = client.post(
        "/ordens", headers=admin.headers, json={"produto_id": produto["id"], "quantidade": 500, "prioridade": "alta"}
    )
    assert resp.status_code == 201, resp.text
    o = resp.json()
    assert o["numero"] == 1
    assert o["status"] == "planejada"
    assert o["comprimento_mm"] == 6000
    assert [(e["setor_nome"], e["status"]) for e in o["etapas"]] == [
        ("Desbobinamento", "aguardando"),
        ("Corte", "aguardando"),
        ("Dobra", "aguardando"),
    ]
    assert o["etapa_atual"] is None
    assert o["eventos"][0]["tipo"] == "criada"
    assert o["eventos"][0]["usuario_nome"] == "Admin Fábrica"


def test_numero_sequencial(nova_ordem):
    assert [nova_ordem()["numero"] for _ in range(3)] == [1, 2, 3]


def test_mudar_o_roteiro_nao_altera_ordem_existente(client, admin, fluxo, produto, nova_ordem):
    from conftest import perfil_u

    ordem = nova_ordem()
    novo = perfil_u(fluxo)
    novo["roteiro"] = novo["roteiro"][1:]
    client.put(f"/produtos/{produto['id']}", headers=admin.headers, json=novo)
    detalhe = client.get(f"/ordens/{ordem['id']}", headers=admin.headers).json()
    assert detalhe["total_etapas"] == 3


def test_liberar_coloca_na_fila_da_primeira_etapa(client, admin, nova_ordem):
    ordem = nova_ordem()
    resp = client.post(f"/ordens/{ordem['id']}/liberar", headers=admin.headers)
    assert resp.status_code == 200, resp.text
    o = resp.json()
    assert o["status"] == "liberada"
    assert o["etapa_atual"] == 1
    assert o["etapas"][0]["status"] == "na_fila"
    assert client.post(f"/ordens/{ordem['id']}/liberar", headers=admin.headers).status_code == 400


def test_fluxo_completo_desbobinador_guilhotina_dobradeira(client, admin, fluxo, nova_ordem):
    maq = fluxo["maquinas"]
    ordem = nova_ordem(liberar=True)
    url = f"/ordens/{ordem['id']}"

    # Desbobinador: só há uma máquina no centro, então ela é escolhida sozinha.
    o = client.post(f"{url}/iniciar", headers=admin.headers, json={}).json()
    assert o["status"] == "em_producao"
    assert o["etapas"][0]["status"] == "em_andamento"
    assert o["etapas"][0]["maquina_codigo"] == "DES-01"
    o = client.post(f"{url}/concluir-etapa", headers=admin.headers, json={}).json()
    assert o["etapa_atual"] == 2
    assert o["etapas"][1]["status"] == "na_fila"

    # Corte tem guilhotina e laser: precisa escolher.
    sem_maquina = client.post(f"{url}/concluir-etapa", headers=admin.headers, json={})
    assert sem_maquina.status_code == 400
    assert "Escolha a máquina de Corte" in sem_maquina.json()["detail"]
    o = client.post(f"{url}/concluir-etapa", headers=admin.headers, json={"maquina_id": maq["COR-01"]["id"]}).json()
    assert o["etapas"][1]["maquina_codigo"] == "COR-01"
    assert o["etapas"][1]["iniciada_em"] is not None

    # Dobradeira: última etapa conclui a OP.
    o = client.post(f"{url}/concluir-etapa", headers=admin.headers, json={}).json()
    assert o["status"] == "concluida"
    assert o["concluida_em"] is not None
    assert o["etapa_atual"] is None
    assert [e["tipo"] for e in o["eventos"]] == [
        "concluida", "etapa_concluida", "etapa_concluida", "etapa_iniciada", "liberada", "criada",
    ]


def test_maquina_de_outro_centro_ou_parada(client, admin, fluxo, nova_ordem):
    maq = fluxo["maquinas"]
    ordem = nova_ordem(liberar=True)
    errada = client.post(f"/ordens/{ordem['id']}/iniciar", headers=admin.headers, json={"maquina_id": maq["DOB-01"]["id"]})
    assert errada.status_code == 400
    assert "não é do centro Desbobinamento" in errada.json()["detail"]

    client.patch(f"/maquinas/{maq['DES-01']['id']}", headers=admin.headers, json={"status": "manutencao"})
    parada = client.post(f"/ordens/{ordem['id']}/iniciar", headers=admin.headers, json={"maquina_id": maq["DES-01"]["id"]})
    assert parada.status_code == 400
    assert "não recebe ordens" in parada.json()["detail"]


def test_ordem_planejada_nao_movimenta(client, admin, nova_ordem):
    ordem = nova_ordem()
    assert client.post(f"/ordens/{ordem['id']}/iniciar", headers=admin.headers, json={}).status_code == 400
    assert client.post(f"/ordens/{ordem['id']}/concluir-etapa", headers=admin.headers, json={}).status_code == 400


def test_pausar_e_retomar_com_motivo(client, admin, nova_ordem):
    ordem = nova_ordem(liberar=True)
    url = f"/ordens/{ordem['id']}"
    assert client.post(f"{url}/pausar", headers=admin.headers, json={"motivo": ""}).status_code == 400
    o = client.post(f"{url}/pausar", headers=admin.headers, json={"motivo": "Falta de bobina de 2,00 mm"}).json()
    assert o["status"] == "pausada"
    assert o["motivo_pausa"] == "Falta de bobina de 2,00 mm"
    assert client.post(f"{url}/iniciar", headers=admin.headers, json={}).status_code == 400
    o = client.post(f"{url}/retomar", headers=admin.headers).json()
    assert o["status"] == "liberada"
    assert o["motivo_pausa"] is None


def test_cancelar(client, admin, nova_ordem):
    ordem = nova_ordem()
    o = client.post(f"/ordens/{ordem['id']}/cancelar", headers=admin.headers, json={"motivo": "Pedido do cliente cancelado"}).json()
    assert o["status"] == "cancelada"
    assert client.post(f"/ordens/{ordem['id']}/liberar", headers=admin.headers).status_code == 400


def test_ordem_atrasada(client, admin, nova_ordem):
    ontem = (date.today() - timedelta(days=1)).isoformat()
    amanha = (date.today() + timedelta(days=1)).isoformat()
    assert nova_ordem(prazo=ontem)["atrasada"] is True
    assert nova_ordem(prazo=amanha)["atrasada"] is False


def test_busca_por_numero_ou_produto(client, admin, nova_ordem):
    nova_ordem()
    segunda = nova_ordem()
    assert [o["numero"] for o in client.get("/ordens", headers=admin.headers, params={"busca": "2"}).json()] == [2]
    assert [o["numero"] for o in client.get("/ordens", headers=admin.headers, params={"busca": "op 1"}).json()] == [1]
    assert len(client.get("/ordens", headers=admin.headers, params={"busca": "pu-100"}).json()) == 2
    assert client.get("/ordens", headers=admin.headers, params={"status": "planejada"}).json()[0]["id"] == segunda["id"]


def test_permissoes_das_ordens(client, usuario, produto, nova_ordem):
    ordem = nova_ordem(liberar=True)
    op = usuario("operador")
    assert client.post("/ordens", headers=op.headers, json={"produto_id": produto["id"], "quantidade": 1}).status_code == 403
    assert client.post(f"/ordens/{ordem['id']}/iniciar", headers=op.headers, json={}).status_code == 200
    assert client.post(f"/ordens/{ordem['id']}/cancelar", headers=op.headers, json={"motivo": "teste"}).status_code == 403

    qualidade = usuario("qualidade")
    assert client.get("/ordens", headers=qualidade.headers).status_code == 200
    assert client.post(f"/ordens/{ordem['id']}/concluir-etapa", headers=qualidade.headers, json={}).status_code == 403

    pcp = usuario("pcp")
    assert client.post("/ordens", headers=pcp.headers, json={"produto_id": produto["id"], "quantidade": 10}).status_code == 201
