import pytest

PARADAS = [
    ("set", "Setup / troca de ferramenta", "planejada"),
    ("mpv", "Manutenção preventiva", "planejada"),
    ("que", "Quebra de máquina", "nao_planejada"),
    ("fmt", "Falta de material", "nao_planejada"),
]


@pytest.fixture
def paradas(client, admin) -> dict[str, dict]:
    criados = {}
    for codigo, descricao, tipo in PARADAS:
        resp = client.post("/motivos/parada", headers=admin.headers, json={"codigo": codigo, "descricao": descricao, "tipo": tipo})
        assert resp.status_code == 201, resp.text
        criados[codigo.upper()] = resp.json()
    return criados


def test_parada_planejada_e_nao_planejada(paradas):
    assert paradas["SET"]["planejada"] is True
    assert paradas["SET"]["tipo_label"] == "Planejada"
    assert paradas["QUE"]["planejada"] is False
    assert paradas["QUE"]["tipo_label"] == "Não planejada"


def test_lista_paradas_por_tipo(client, admin, paradas):
    todas = client.get("/motivos/parada", headers=admin.headers).json()
    assert [m["codigo"] for m in todas] == ["MPV", "SET", "FMT", "QUE"]
    nao = client.get("/motivos/parada", headers=admin.headers, params={"tipo": "nao_planejada"}).json()
    assert [m["codigo"] for m in nao] == ["FMT", "QUE"]


def test_tipo_de_parada_invalido(client, admin):
    resp = client.post("/motivos/parada", headers=admin.headers, json={"codigo": "X", "descricao": "Outro", "tipo": "talvez"})
    assert resp.status_code == 400


def test_parada_duplicada(client, admin, paradas):
    mesmo_codigo = {"codigo": "SET", "descricao": "Outra coisa", "tipo": "planejada"}
    assert client.post("/motivos/parada", headers=admin.headers, json=mesmo_codigo).status_code == 409
    mesma_descricao = {"codigo": "QB2", "descricao": "quebra de máquina", "tipo": "nao_planejada"}
    assert client.post("/motivos/parada", headers=admin.headers, json=mesma_descricao).status_code == 409


def test_inativa_motivo_e_filtra_ativos(client, admin, paradas):
    fmt = paradas["FMT"]
    resp = client.put(
        f"/motivos/parada/{fmt['id']}",
        headers=admin.headers,
        json={"codigo": "FMT", "descricao": fmt["descricao"], "tipo": "nao_planejada", "ativo": False},
    )
    assert resp.status_code == 200, resp.text
    ativos = client.get("/motivos/parada", headers=admin.headers, params={"ativos": True}).json()
    assert "FMT" not in [m["codigo"] for m in ativos]


def test_refugo_por_categoria(client, admin):
    for codigo, descricao, categoria in [
        ("dim", "Medida fora da tolerância", "dimensional"),
        ("ang", "Ângulo de dobra fora", "dimensional"),
        ("reb", "Rebarba no corte", "acabamento"),
    ]:
        resp = client.post("/motivos/refugo", headers=admin.headers, json={"codigo": codigo, "descricao": descricao, "categoria": categoria})
        assert resp.status_code == 201, resp.text
    dim = client.get("/motivos/refugo", headers=admin.headers, params={"categoria": "dimensional"}).json()
    assert [m["codigo"] for m in dim] == ["ANG", "DIM"]
    assert dim[0]["categoria_label"] == "Dimensional"


def test_categoria_de_refugo_invalida(client, admin):
    resp = client.post("/motivos/refugo", headers=admin.headers, json={"codigo": "X", "descricao": "Outro", "categoria": "cor"})
    assert resp.status_code == 400


def test_opcoes_de_tipos_e_categorias(client, admin):
    opcoes = client.get("/motivos/opcoes", headers=admin.headers).json()
    assert [o["valor"] for o in opcoes["tipos_parada"]] == ["planejada", "nao_planejada"]
    assert "dimensional" in [o["valor"] for o in opcoes["categorias_refugo"]]


def test_qualidade_ve_mas_nao_edita(client, usuario, paradas):
    qual = usuario("qualidade")
    assert client.get("/motivos/parada", headers=qual.headers).status_code == 200
    assert client.get("/motivos/refugo", headers=qual.headers).status_code == 200
    novo = {"codigo": "RIS", "descricao": "Riscos", "categoria": "manuseio"}
    assert client.post("/motivos/refugo", headers=qual.headers, json=novo).status_code == 403


def test_supervisor_cadastra_motivos(client, usuario):
    sup = usuario("supervisor")
    novo = {"codigo": "AJU", "descricao": "Ajuste de processo", "tipo": "nao_planejada"}
    assert client.post("/motivos/parada", headers=sup.headers, json=novo).status_code == 201


def test_operador_nao_acessa_motivos(client, usuario):
    op = usuario("operador")
    assert client.get("/motivos/parada", headers=op.headers).status_code == 403
