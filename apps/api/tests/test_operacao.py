from types import SimpleNamespace

import pytest


@pytest.fixture
def equipe(client, admin, fluxo) -> SimpleNamespace:
    turno = client.post("/turnos", headers=admin.headers, json={"codigo": "T1", "nome": "1º turno", "inicio": "06:00", "fim": "14:00"})
    assert turno.status_code == 201, turno.text
    ops = {}
    for matricula, nome, setor in [("1001", "Carlos Alves", "DES"), ("1002", "Marcos Rocha", "COR")]:
        resp = client.post(
            "/operadores",
            headers=admin.headers,
            json={"matricula": matricula, "nome": nome, "turno_id": turno.json()["id"], "setor_id": fluxo[setor]["id"]},
        )
        assert resp.status_code == 201, resp.text
        ops[matricula] = resp.json()
    return SimpleNamespace(**{f"op{k}": v for k, v in ops.items()}, maq=fluxo["maquinas"])


def painel(client, headers, maquina) -> dict:
    resp = client.get(f"/operacao/maquinas/{maquina['id']}", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def iniciar(client, headers, maquina, ordem, operador):
    return client.post(
        f"/operacao/maquinas/{maquina['id']}/iniciar",
        headers=headers,
        json={"ordem_id": ordem["id"], "operador_id": operador["id"]},
    )


def finalizar(client, headers, maquina, operador):
    return client.post(f"/operacao/maquinas/{maquina['id']}/finalizar", headers=headers, json={"operador_id": operador["id"]})


def test_identifica_operador_pela_matricula(client, usuario, equipe):
    op = usuario("operador")
    resp = client.get("/operacao/operador", headers=op.headers, params={"matricula": " 1001 "})
    assert resp.status_code == 200, resp.text
    assert resp.json()["nome"] == "Carlos Alves"
    assert client.get("/operacao/operador", headers=op.headers, params={"matricula": "9999"}).status_code == 404


def test_fila_da_maquina_por_prioridade(client, admin, equipe, nova_ordem):
    normal = nova_ordem(liberar=True)
    urgente = nova_ordem(liberar=True, prioridade="urgente")
    nova_ordem()  # planejada: ainda não entrou na fábrica
    fila = painel(client, admin.headers, equipe.maq["DES-01"])
    assert [f["ordem_numero"] for f in fila["fila"]] == [urgente["numero"], normal["numero"]]
    assert fila["atual"] is None
    assert fila["fila"][0]["proximo_setor"] == "Corte"
    assert fila["fila"][0]["carga_min"] == 333.3  # 500 peças × 40 s
    assert painel(client, admin.headers, equipe.maq["COR-01"])["fila"] == []


def test_iniciar_registra_operador_e_horario(client, usuario, equipe, nova_ordem):
    op = usuario("operador")
    ordem = nova_ordem(liberar=True)
    resp = iniciar(client, op.headers, equipe.maq["DES-01"], ordem, equipe.op1001)
    assert resp.status_code == 200, resp.text
    atual = resp.json()["atual"]
    assert atual["ordem_numero"] == ordem["numero"]
    assert atual["operador_nome"] == "Carlos Alves"
    assert atual["iniciada_em"] is not None
    assert resp.json()["fila"] == []
    detalhe = client.get(f"/ordens/{ordem['id']}", headers=op.headers).json()
    assert detalhe["etapas"][0]["operador_nome"] == "Carlos Alves"
    assert "por Carlos Alves (1001)" in detalhe["eventos"][0]["descricao"]


def test_maquina_ocupada_nao_inicia_outra(client, admin, equipe, nova_ordem):
    primeira, segunda = nova_ordem(liberar=True), nova_ordem(liberar=True)
    assert iniciar(client, admin.headers, equipe.maq["DES-01"], primeira, equipe.op1001).status_code == 200
    resp = iniciar(client, admin.headers, equipe.maq["DES-01"], segunda, equipe.op1001)
    assert resp.status_code == 400
    assert "em andamento" in resp.json()["detail"]


def test_ordem_de_outro_centro_nao_inicia(client, admin, equipe, nova_ordem):
    ordem = nova_ordem(liberar=True)
    resp = iniciar(client, admin.headers, equipe.maq["COR-01"], ordem, equipe.op1002)
    assert resp.status_code == 400


def test_finalizar_manda_para_a_proxima_maquina(client, admin, equipe, nova_ordem):
    ordem = nova_ordem(liberar=True)
    iniciar(client, admin.headers, equipe.maq["DES-01"], ordem, equipe.op1001)
    resp = finalizar(client, admin.headers, equipe.maq["DES-01"], equipe.op1001)
    assert resp.status_code == 200, resp.text
    assert resp.json()["atual"] is None
    detalhe = client.get(f"/ordens/{ordem['id']}", headers=admin.headers).json()
    assert detalhe["etapas"][0]["status"] == "concluida"
    assert detalhe["etapas"][0]["concluida_em"] is not None
    # As duas guilhotinas do Corte enxergam a ordem na fila.
    for codigo in ("COR-01", "COR-02"):
        assert [f["ordem_numero"] for f in painel(client, admin.headers, equipe.maq[codigo])["fila"]] == [ordem["numero"]]


def test_finalizar_sem_operacao(client, admin, equipe):
    resp = finalizar(client, admin.headers, equipe.maq["DES-01"], equipe.op1001)
    assert resp.status_code == 400


def test_ordem_pausada_nao_finaliza(client, admin, equipe, nova_ordem):
    ordem = nova_ordem(liberar=True)
    iniciar(client, admin.headers, equipe.maq["DES-01"], ordem, equipe.op1001)
    client.post(f"/ordens/{ordem['id']}/pausar", headers=admin.headers, json={"motivo": "Troca de bobina"})
    atual = painel(client, admin.headers, equipe.maq["DES-01"])["atual"]
    assert (atual["ordem_status"], atual["motivo_pausa"]) == ("pausada", "Troca de bobina")
    assert finalizar(client, admin.headers, equipe.maq["DES-01"], equipe.op1001).status_code == 400


def test_operador_inativo_nao_aponta(client, admin, equipe, nova_ordem, fluxo):
    op = equipe.op1001
    client.put(
        f"/operadores/{op['id']}",
        headers=admin.headers,
        json={"matricula": "1001", "nome": op["nome"], "turno_id": op["turno_id"], "setor_id": op["setor_id"], "ativo": False},
    )
    ordem = nova_ordem(liberar=True)
    assert iniciar(client, admin.headers, equipe.maq["DES-01"], ordem, op).status_code == 400


@pytest.mark.parametrize("perfil", ["pcp", "qualidade"])
def test_perfis_sem_tela_do_operador(client, usuario, equipe, perfil):
    pessoa = usuario(perfil)
    assert client.get(f"/operacao/maquinas/{equipe.maq['DES-01']['id']}", headers=pessoa.headers).status_code == 403
