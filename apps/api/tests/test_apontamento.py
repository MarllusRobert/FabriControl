import pytest

from conftest import finalizar, iniciar, painel


@pytest.fixture
def motivo(client, admin) -> dict:
    resp = client.post("/motivos/refugo", headers=admin.headers, json={"codigo": "REB", "descricao": "Rebarba no corte", "categoria": "acabamento"})
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture
def rodando(client, admin, equipe, nova_ordem) -> dict:
    """OP de 500 peças rodando no desbobinador."""
    ordem = nova_ordem(liberar=True)
    assert iniciar(client, admin.headers, equipe.maq["DES-01"], ordem, equipe.op1001).status_code == 200
    return ordem


def apontar(client, headers, maquina, operador, **corpo):
    return client.post(f"/operacao/maquinas/{maquina['id']}/apontar", headers=headers, json={"operador_id": operador["id"], **corpo})


def test_aponta_boas_e_refugo_e_atualiza_saldo(client, usuario, equipe, rodando, motivo):
    op = usuario("operador")
    resp = apontar(client, op.headers, equipe.maq["DES-01"], equipe.op1001, boas=100, refugo=5, motivo_refugo_id=motivo["id"])
    assert resp.status_code == 200, resp.text
    atual = resp.json()["atual"]
    assert (atual["entrada"], atual["boas"], atual["refugo"], atual["saldo"]) == (500, 100, 5, 395)
    resp = apontar(client, op.headers, equipe.maq["DES-01"], equipe.op1001, boas=200)
    assert resp.json()["atual"]["saldo"] == 195
    detalhe = client.get(f"/ordens/{rodando['id']}", headers=op.headers).json()
    assert (detalhe["etapas"][0]["boas"], detalhe["etapas"][0]["refugo"]) == (300, 5)
    assert "apontadas 100 boas e 5 refugo (Rebarba no corte)" in detalhe["eventos"][1]["descricao"]


def test_refugo_exige_motivo(client, admin, equipe, rodando):
    resp = apontar(client, admin.headers, equipe.maq["DES-01"], equipe.op1001, boas=10, refugo=2)
    assert resp.status_code == 400
    assert "motivo" in resp.json()["detail"]


def test_motivo_inativo_nao_vale(client, admin, equipe, rodando, motivo):
    client.put(f"/motivos/refugo/{motivo['id']}", headers=admin.headers, json={**{k: motivo[k] for k in ("codigo", "descricao", "categoria")}, "ativo": False})
    resp = apontar(client, admin.headers, equipe.maq["DES-01"], equipe.op1001, refugo=2, motivo_refugo_id=motivo["id"])
    assert resp.status_code == 400


def test_nao_aponta_acima_do_saldo(client, admin, equipe, rodando, motivo):
    assert apontar(client, admin.headers, equipe.maq["DES-01"], equipe.op1001, boas=490).status_code == 200
    resp = apontar(client, admin.headers, equipe.maq["DES-01"], equipe.op1001, boas=8, refugo=3, motivo_refugo_id=motivo["id"])
    assert resp.status_code == 400
    assert "restam 10" in resp.json()["detail"]


def test_apontamento_vazio(client, admin, equipe, rodando):
    assert apontar(client, admin.headers, equipe.maq["DES-01"], equipe.op1001, boas=0, refugo=0).status_code == 400


def test_sem_operacao_nao_aponta(client, admin, equipe):
    assert apontar(client, admin.headers, equipe.maq["COR-01"], equipe.op1002, boas=10).status_code == 400


def test_proxima_etapa_recebe_so_as_boas(client, admin, equipe, rodando, motivo):
    apontar(client, admin.headers, equipe.maq["DES-01"], equipe.op1001, boas=480, refugo=20, motivo_refugo_id=motivo["id"])
    finalizar(client, admin.headers, equipe.maq["DES-01"], equipe.op1001)
    fila = painel(client, admin.headers, equipe.maq["COR-01"])["fila"]
    assert (fila[0]["entrada"], fila[0]["saldo"]) == (480, 480)
    iniciar(client, admin.headers, equipe.maq["COR-01"], rodando, equipe.op1002)
    resp = apontar(client, admin.headers, equipe.maq["COR-01"], equipe.op1002, boas=481)
    assert resp.status_code == 400


def test_operador_ve_motivos_de_refugo_ativos(client, usuario, motivo):
    op = usuario("operador")
    resp = client.get("/operacao/motivos-refugo", headers=op.headers)
    assert resp.status_code == 200
    assert [m["codigo"] for m in resp.json()] == ["REB"]


def test_qualidade_nao_aponta(client, usuario, equipe, rodando):
    qual = usuario("qualidade")
    assert apontar(client, qual.headers, equipe.maq["DES-01"], equipe.op1001, boas=10).status_code == 403
