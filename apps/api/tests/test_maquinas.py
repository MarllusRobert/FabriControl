import pytest
from fastapi import HTTPException


def test_cadastra_maquina(client, admin, setor):
    resp = client.post(
        "/maquinas",
        headers=admin.headers,
        json={"codigo": " cor-01 ", "nome": "Guilhotina  hidráulica", "setor_id": setor["id"], "ciclo_padrao_seg": 12},
    )
    assert resp.status_code == 201, resp.text
    m = resp.json()
    assert m["codigo"] == "COR-01"
    assert m["nome"] == "Guilhotina hidráulica"
    assert m["setor_nome"] == "Corte"
    assert m["status"] == "ativa"
    assert m["pecas_por_hora"] == 300.0
    assert m["recebe_ordem"] is True


def test_codigo_unico(client, admin, setor, nova_maquina):
    nova_maquina(codigo="COR-01")
    dup = {"codigo": "cor-01", "nome": "Outra", "setor_id": setor["id"], "ciclo_padrao_seg": 10}
    resp = client.post("/maquinas", headers=admin.headers, json=dup)
    assert resp.status_code == 409


@pytest.mark.parametrize("ciclo", [0, -5])
def test_ciclo_precisa_ser_positivo(client, admin, setor, ciclo):
    payload = {"codigo": "X-1", "nome": "Máquina", "setor_id": setor["id"], "ciclo_padrao_seg": ciclo}
    assert client.post("/maquinas", headers=admin.headers, json=payload).status_code == 400


def test_setor_inexistente_ou_inativo(client, admin, setor):
    payload = {"codigo": "X-1", "nome": "Máquina", "setor_id": "nao-existe", "ciclo_padrao_seg": 10}
    assert client.post("/maquinas", headers=admin.headers, json=payload).status_code == 400
    client.put(f"/setores/{setor['id']}", headers=admin.headers, json={"codigo": "COR", "nome": "Corte", "ativo": False})
    payload["setor_id"] = setor["id"]
    resp = client.post("/maquinas", headers=admin.headers, json=payload)
    assert resp.status_code == 400
    assert "inativo" in resp.json()["detail"]


def test_busca_e_filtro_por_setor(client, admin, nova_maquina):
    nova_maquina(nome="Guilhotina hidráulica")
    nova_maquina(nome="Corte a laser")
    dobra = client.post("/setores", headers=admin.headers, json={"codigo": "DOB", "nome": "Dobra"}).json()
    nova_maquina(codigo="DOB-01", nome="Dobradeira CNC", setor_id=dobra["id"])

    busca = client.get("/maquinas", headers=admin.headers, params={"busca": "laser"}).json()
    assert [m["nome"] for m in busca] == ["Corte a laser"]
    por_codigo = client.get("/maquinas", headers=admin.headers, params={"busca": "dob-01"}).json()
    assert [m["codigo"] for m in por_codigo] == ["DOB-01"]
    do_setor = client.get("/maquinas", headers=admin.headers, params={"setor_id": dobra["id"]}).json()
    assert [m["codigo"] for m in do_setor] == ["DOB-01"]
    todas = client.get("/maquinas", headers=admin.headers).json()
    assert len(todas) == 3


def test_maquina_inativa_nao_recebe_ordem(client, admin, db, nova_maquina):
    from app.routers.cadastros import maquina_pode_receber_ordem

    ativa = nova_maquina()
    parada = nova_maquina(status="manutencao")
    inativa = nova_maquina()
    resp = client.patch(f"/maquinas/{inativa['id']}", headers=admin.headers, json={"status": "inativa"})
    assert resp.json()["recebe_ordem"] is False

    disponiveis = client.get("/maquinas", headers=admin.headers, params={"recebe_ordem": True}).json()
    assert [m["id"] for m in disponiveis] == [ativa["id"]]

    assert maquina_pode_receber_ordem(db, ativa["id"]).codigo == ativa["codigo"]
    for m in (parada, inativa):
        with pytest.raises(HTTPException) as erro:
            maquina_pode_receber_ordem(db, m["id"])
        assert "não recebe ordens" in erro.value.detail


def test_edita_maquina(client, admin, nova_maquina):
    m = nova_maquina()
    resp = client.patch(
        f"/maquinas/{m['id']}",
        headers=admin.headers,
        json={"nome": "Guilhotina nova", "ciclo_padrao_seg": 10.5, "observacao": "Troca de faca a cada 20 mil cortes"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["ciclo_padrao_seg"] == 10.5
    assert resp.json()["observacao"] == "Troca de faca a cada 20 mil cortes"
    assert client.patch("/maquinas/nao-existe", headers=admin.headers, json={"nome": "Outro nome"}).status_code == 404


def test_resumo_por_status_e_setor(client, admin, nova_maquina):
    nova_maquina()
    nova_maquina(status="manutencao")
    resumo = client.get("/maquinas/resumo", headers=admin.headers).json()
    assert resumo["total"] == 2
    assert {s["status"]: s["total"] for s in resumo["por_status"]} == {"ativa": 1, "manutencao": 1, "inativa": 0}
    assert resumo["por_setor"] == [{"setor": "Corte", "total": 2}]


def test_setor_duplicado(client, admin, setor):
    assert client.post("/setores", headers=admin.headers, json={"codigo": "COR", "nome": "Outro"}).status_code == 409
    assert client.post("/setores", headers=admin.headers, json={"codigo": "X", "nome": "corte"}).status_code == 409


@pytest.mark.parametrize("perfil", ["supervisor", "operador", "qualidade"])
def test_perfis_de_consulta_nao_editam(client, usuario, setor, nova_maquina, perfil):
    m = nova_maquina()
    pessoa = usuario(perfil)
    assert client.get("/maquinas", headers=pessoa.headers).status_code == 200
    novo = {"codigo": "Z-1", "nome": "Máquina", "setor_id": setor["id"], "ciclo_padrao_seg": 10}
    assert client.post("/maquinas", headers=pessoa.headers, json=novo).status_code == 403
    assert client.patch(f"/maquinas/{m['id']}", headers=pessoa.headers, json={"nome": "Outro nome"}).status_code == 403
    assert client.post("/setores", headers=pessoa.headers, json={"codigo": "S", "nome": "Setor"}).status_code == 403


def test_pcp_cadastra(client, usuario, setor):
    pcp = usuario("pcp")
    novo = {"codigo": "COR-09", "nome": "Serra fita", "setor_id": setor["id"], "ciclo_padrao_seg": 60}
    assert client.post("/maquinas", headers=pcp.headers, json=novo).status_code == 201


def test_operador_nao_ve_painel(client, usuario):
    op = usuario("operador")
    me = client.get("/auth/me", headers=op.headers).json()
    assert "painel" not in me["telas"]
    assert me["inicio"] == "/kanban"
