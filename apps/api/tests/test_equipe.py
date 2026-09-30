import pytest

TURNOS = [("T1", "1º turno", "06:00", "14:00"), ("T2", "2º turno", "14:00", "22:00"), ("T3", "3º turno", "22:00", "06:00")]


@pytest.fixture
def turnos(client, admin) -> dict[str, dict]:
    criados = {}
    for codigo, nome, inicio, fim in TURNOS:
        resp = client.post("/turnos", headers=admin.headers, json={"codigo": codigo, "nome": nome, "inicio": inicio, "fim": fim})
        assert resp.status_code == 201, resp.text
        criados[codigo] = resp.json()
    return criados


def operador(turno: dict, setor: dict, **extra) -> dict:
    return {"matricula": "op-101", "nome": "João  da Silva", "turno_id": turno["id"], "setor_id": setor["id"], **extra}


def test_turno_que_vira_a_meia_noite(turnos):
    noite = turnos["T3"]
    assert (noite["inicio"], noite["fim"]) == ("22:00", "06:00")
    assert noite["vira_meia_noite"] is True
    assert noite["duracao_min"] == 480
    assert turnos["T1"]["vira_meia_noite"] is False
    assert turnos["T1"]["duracao_min"] == 480


def test_lista_turnos_pela_hora_de_inicio(client, admin, turnos):
    lista = client.get("/turnos", headers=admin.headers).json()
    assert [t["codigo"] for t in lista] == ["T1", "T2", "T3"]


@pytest.mark.parametrize(
    ("hora", "codigo"),
    [("06:00", "T1"), ("13:59", "T1"), ("14:00", "T2"), ("22:00", "T3"), ("23:30", "T3"), ("00:00", "T3"), ("05:59", "T3")],
)
def test_turno_do_horario(client, admin, turnos, hora, codigo):
    resp = client.get("/turnos/do-horario", headers=admin.headers, params={"hora": hora})
    assert resp.status_code == 200, resp.text
    assert resp.json()["codigo"] == codigo


def test_horario_sem_turno(client, admin):
    client.post("/turnos", headers=admin.headers, json={"codigo": "ADM", "nome": "Comercial", "inicio": "08:00", "fim": "17:00"})
    assert client.get("/turnos/do-horario", headers=admin.headers, params={"hora": "20:00"}).json() is None


def test_inicio_igual_ao_fim(client, admin):
    resp = client.post("/turnos", headers=admin.headers, json={"codigo": "X", "nome": "Errado", "inicio": "08:00", "fim": "08:00"})
    assert resp.status_code == 400


@pytest.mark.parametrize(("inicio", "fim"), [("13:00", "15:00"), ("05:00", "07:00"), ("23:00", "01:00"), ("02:00", "03:00")])
def test_turnos_ativos_nao_se_sobrepoem(client, admin, turnos, inicio, fim):
    resp = client.post("/turnos", headers=admin.headers, json={"codigo": "EX", "nome": "Extra", "inicio": inicio, "fim": fim})
    assert resp.status_code == 409
    assert "sobrepõe" in resp.json()["detail"]


def test_turno_inativo_nao_conflita(client, admin, turnos):
    extra = {"codigo": "EX", "nome": "Extra", "inicio": "13:00", "fim": "15:00", "ativo": False}
    resp = client.post("/turnos", headers=admin.headers, json=extra)
    assert resp.status_code == 201, resp.text
    reativar = client.put(f"/turnos/{resp.json()['id']}", headers=admin.headers, json={**extra, "ativo": True})
    assert reativar.status_code == 409


def test_codigo_de_turno_duplicado(client, admin, turnos):
    resp = client.post("/turnos", headers=admin.headers, json={"codigo": "t1", "nome": "Outro", "inicio": "08:00", "fim": "09:00"})
    assert resp.status_code == 409


def test_operador_ligado_a_turno_e_setor(client, admin, turnos, setor):
    resp = client.post("/operadores", headers=admin.headers, json=operador(turnos["T3"], setor))
    assert resp.status_code == 201, resp.text
    op = resp.json()
    assert op["matricula"] == "OP-101"
    assert op["nome"] == "João da Silva"
    assert (op["turno_nome"], op["turno_horario"], op["setor_nome"]) == ("3º turno", "22:00 às 06:00", "Corte")
    lista = client.get("/turnos", headers=admin.headers).json()
    assert {t["codigo"]: t["operadores"] for t in lista} == {"T1": 0, "T2": 0, "T3": 1}


def test_filtros_de_operadores(client, admin, turnos, setor):
    client.post("/operadores", headers=admin.headers, json=operador(turnos["T1"], setor, matricula="A1", nome="Ana Souza"))
    client.post("/operadores", headers=admin.headers, json=operador(turnos["T2"], setor, matricula="B2", nome="Bruno Lima"))
    por_turno = client.get("/operadores", headers=admin.headers, params={"turno_id": turnos["T2"]["id"]}).json()
    assert [o["nome"] for o in por_turno] == ["Bruno Lima"]
    por_busca = client.get("/operadores", headers=admin.headers, params={"busca": "a1"}).json()
    assert [o["nome"] for o in por_busca] == ["Ana Souza"]


def test_troca_de_turno(client, admin, turnos, setor):
    op = client.post("/operadores", headers=admin.headers, json=operador(turnos["T1"], setor)).json()
    resp = client.put(f"/operadores/{op['id']}", headers=admin.headers, json=operador(turnos["T2"], setor))
    assert resp.status_code == 200, resp.text
    assert resp.json()["turno_nome"] == "2º turno"


def test_matricula_duplicada(client, admin, turnos, setor):
    assert client.post("/operadores", headers=admin.headers, json=operador(turnos["T1"], setor)).status_code == 201
    assert client.post("/operadores", headers=admin.headers, json=operador(turnos["T2"], setor, nome="Outro")).status_code == 409


def test_turno_ou_setor_inativo_nao_recebe_operador(client, admin, turnos, setor):
    t1 = turnos["T1"]
    client.put(f"/turnos/{t1['id']}", headers=admin.headers, json={**{k: t1[k] for k in ("codigo", "nome", "inicio", "fim")}, "ativo": False})
    assert client.post("/operadores", headers=admin.headers, json=operador(t1, setor)).status_code == 400
    client.put(f"/setores/{setor['id']}", headers=admin.headers, json={"codigo": "COR", "nome": "Corte", "ativo": False})
    assert client.post("/operadores", headers=admin.headers, json=operador(turnos["T2"], setor)).status_code == 400


def test_nao_inativa_turno_com_operadores(client, admin, turnos, setor):
    client.post("/operadores", headers=admin.headers, json=operador(turnos["T1"], setor))
    t1 = turnos["T1"]
    resp = client.put(f"/turnos/{t1['id']}", headers=admin.headers, json={**{k: t1[k] for k in ("codigo", "nome", "inicio", "fim")}, "ativo": False})
    assert resp.status_code == 400
    assert "operador" in resp.json()["detail"]


def test_supervisor_cadastra_a_equipe(client, usuario, setor):
    sup = usuario("supervisor")
    turno = client.post("/turnos", headers=sup.headers, json={"codigo": "T1", "nome": "1º turno", "inicio": "06:00", "fim": "14:00"})
    assert turno.status_code == 201, turno.text
    assert client.post("/operadores", headers=sup.headers, json=operador(turno.json(), setor)).status_code == 201


@pytest.mark.parametrize("perfil", ["operador", "qualidade"])
def test_perfis_sem_acesso_a_equipe(client, usuario, perfil):
    pessoa = usuario(perfil)
    assert client.get("/turnos", headers=pessoa.headers).status_code == 403
    assert client.get("/operadores", headers=pessoa.headers).status_code == 403
    novo = {"codigo": "T9", "nome": "Turno", "inicio": "06:00", "fim": "14:00"}
    assert client.post("/turnos", headers=pessoa.headers, json=novo).status_code == 403
