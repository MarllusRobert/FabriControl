import pytest

from conftest import SENHA_PADRAO, SETUP, auth


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["database"] is True


def test_setup_cria_administrador_uma_vez_so(client):
    assert client.get("/setup/status").json() == {"needs_setup": True}
    resp = client.post("/setup", json=SETUP)
    assert resp.status_code == 200, resp.text
    user = resp.json()["user"]
    assert user["perfil"] == "administrador"
    assert [m["tela"] for m in user["menu"]] == ["painel", "maquinas", "usuarios"]
    assert client.get("/setup/status").json() == {"needs_setup": False}
    assert client.post("/setup", json=SETUP).status_code == 409


def test_senha_fica_criptografada(client, db, admin):
    from app.models import Usuario

    user = db.get(Usuario, admin.id)
    assert user.senha_hash != SETUP["senha"]
    assert user.senha_hash.startswith("$2")


def test_login_e_me(client, admin):
    resp = client.post("/auth/login", json={"email": "  ADMIN@fabrica.com ", "senha": SETUP["senha"]})
    assert resp.status_code == 200, resp.text
    me = client.get("/auth/me", headers=auth(resp.json()["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == "admin@fabrica.com"


def test_rotas_exigem_login(client, admin):
    assert client.get("/maquinas").status_code == 401
    assert client.get("/auth/me", headers=auth("token-falso")).status_code == 401


def test_token_expirado_e_recusado(client, admin, monkeypatch):
    from app import security

    monkeypatch.setattr(security.get_settings(), "jwt_expire_minutes", -1)
    login = client.post("/auth/login", json={"email": SETUP["email"], "senha": SETUP["senha"]})
    assert client.get("/auth/me", headers=auth(login.json()["access_token"])).status_code == 401


def test_bloqueio_apos_tentativas_erradas(client, admin):
    errado = {"email": SETUP["email"], "senha": "senha-errada"}
    for _ in range(5):
        assert client.post("/auth/login", json=errado).status_code == 401
    bloqueado = client.post("/auth/login", json={"email": SETUP["email"], "senha": SETUP["senha"]})
    assert bloqueado.status_code == 429
    assert "Muitas tentativas" in bloqueado.json()["detail"]


def test_usuario_inativo_nao_entra(client, admin, usuario):
    op = usuario("operador")
    assert client.patch(f"/usuarios/{op.id}", headers=admin.headers, json={"ativo": False}).status_code == 200
    assert client.post("/auth/login", json={"email": op.email, "senha": SENHA_PADRAO}).status_code == 401
    assert client.get("/auth/me", headers=op.headers).status_code == 401


def test_troca_de_senha_derruba_sessoes_antigas(client, usuario):
    pcp = usuario("pcp")
    errada = client.post("/auth/senha", headers=pcp.headers, json={"senha_atual": "nao-e-essa", "nova_senha": "nova-senha-123"})
    assert errada.status_code == 400
    resp = client.post("/auth/senha", headers=pcp.headers, json={"senha_atual": SENHA_PADRAO, "nova_senha": "nova-senha-123"})
    assert resp.status_code == 200, resp.text
    assert client.get("/auth/me", headers=pcp.headers).status_code == 401
    assert client.get("/auth/me", headers=auth(resp.json()["access_token"])).status_code == 200
    assert client.post("/auth/login", json={"email": pcp.email, "senha": "nova-senha-123"}).status_code == 200


@pytest.mark.parametrize(
    ("perfil", "menu"),
    [
        ("pcp", ["painel", "maquinas"]),
        ("supervisor", ["painel", "maquinas"]),
        ("operador", ["maquinas"]),
        ("qualidade", ["painel", "maquinas"]),
    ],
)
def test_menu_por_perfil(client, usuario, perfil, menu):
    pessoa = usuario(perfil)
    me = client.get("/auth/me", headers=pessoa.headers).json()
    assert [m["tela"] for m in me["menu"]] == menu
    assert "usuarios" not in me["telas"]


def test_so_administrador_gerencia_usuarios(client, usuario):
    for perfil in ("pcp", "supervisor", "operador", "qualidade"):
        pessoa = usuario(perfil)
        assert client.get("/usuarios", headers=pessoa.headers).status_code == 403
        novo = {"nome": "Intruso", "email": "x@fabrica.com", "senha": "senha-123456", "perfil": "administrador"}
        assert client.post("/usuarios", headers=pessoa.headers, json=novo).status_code == 403


def test_email_duplicado(client, admin):
    novo = {"nome": "Outro", "email": SETUP["email"], "senha": "senha-123456", "perfil": "pcp"}
    assert client.post("/usuarios", headers=admin.headers, json=novo).status_code == 409


def test_perfil_invalido(client, admin):
    novo = {"nome": "Outro", "email": "o@fabrica.com", "senha": "senha-123456", "perfil": "gerente"}
    assert client.post("/usuarios", headers=admin.headers, json=novo).status_code == 400


def test_nao_remove_o_ultimo_administrador(client, admin, usuario):
    resp = client.patch(f"/usuarios/{admin.id}", headers=admin.headers, json={"perfil": "pcp"})
    assert resp.status_code == 400
    assert client.patch(f"/usuarios/{admin.id}", headers=admin.headers, json={"ativo": False}).status_code == 400
    outro = usuario("administrador")
    assert client.patch(f"/usuarios/{admin.id}", headers=outro.headers, json={"perfil": "pcp"}).status_code == 200


def test_lista_de_perfis(client, admin):
    perfis = client.get("/usuarios/perfis", headers=admin.headers).json()
    assert [p["perfil"] for p in perfis] == ["administrador", "pcp", "supervisor", "operador", "qualidade"]
