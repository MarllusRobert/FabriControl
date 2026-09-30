from conftest import perfil_u


def test_setores_saem_na_ordem_do_fluxo(client, admin, fluxo):
    setores = client.get("/setores", headers=admin.headers).json()
    assert [s["codigo"] for s in setores] == ["DES", "COR", "DOB"]


def test_cadastra_produto_com_roteiro(client, admin, fluxo):
    resp = client.post("/produtos", headers=admin.headers, json=perfil_u(fluxo))
    assert resp.status_code == 201, resp.text
    p = resp.json()
    assert p["codigo"] == "PU-100-6"
    assert p["comprimento_mm"] == 6000
    assert [(e["sequencia"], e["setor_nome"]) for e in p["roteiro"]] == [(1, "Desbobinamento"), (2, "Corte"), (3, "Dobra")]


def test_roteiro_obrigatorio_e_setor_valido(client, admin, fluxo):
    assert client.post("/produtos", headers=admin.headers, json=perfil_u(fluxo, roteiro=[])).status_code == 400
    ruim = perfil_u(fluxo)
    ruim["roteiro"][1]["setor_id"] = "nao-existe"
    resp = client.post("/produtos", headers=admin.headers, json=ruim)
    assert resp.status_code == 400
    assert "Etapa 2" in resp.json()["detail"]


def test_mesmo_centro_em_etapas_seguidas(client, admin, fluxo):
    repetido = perfil_u(fluxo)
    repetido["roteiro"][1]["setor_id"] = fluxo["DES"]["id"]
    resp = client.post("/produtos", headers=admin.headers, json=repetido)
    assert resp.status_code == 400
    assert "mesmo centro" in resp.json()["detail"]


def test_codigo_de_produto_unico(client, admin, fluxo):
    client.post("/produtos", headers=admin.headers, json=perfil_u(fluxo))
    assert client.post("/produtos", headers=admin.headers, json=perfil_u(fluxo)).status_code == 409


def test_edita_roteiro(client, admin, fluxo):
    p = client.post("/produtos", headers=admin.headers, json=perfil_u(fluxo)).json()
    novo = perfil_u(fluxo, comprimento_mm=3000)
    novo["roteiro"] = novo["roteiro"][1:]
    resp = client.put(f"/produtos/{p['id']}", headers=admin.headers, json=novo)
    assert resp.status_code == 200, resp.text
    assert resp.json()["comprimento_mm"] == 3000
    assert [(e["sequencia"], e["setor_nome"]) for e in resp.json()["roteiro"]] == [(1, "Corte"), (2, "Dobra")]


def test_busca_de_produto(client, admin, fluxo):
    client.post("/produtos", headers=admin.headers, json=perfil_u(fluxo))
    assert len(client.get("/produtos", headers=admin.headers, params={"busca": "perfil u"}).json()) == 1
    assert client.get("/produtos", headers=admin.headers, params={"busca": "cantoneira"}).json() == []


def test_so_quem_edita_cadastros_cria_produto(client, usuario, fluxo):
    sup = usuario("supervisor")
    assert client.get("/produtos", headers=sup.headers).status_code == 200
    assert client.post("/produtos", headers=sup.headers, json=perfil_u(fluxo)).status_code == 403
    pcp = usuario("pcp")
    assert client.post("/produtos", headers=pcp.headers, json=perfil_u(fluxo)).status_code == 201
    op = usuario("operador")
    assert client.get("/produtos", headers=op.headers).status_code == 403
