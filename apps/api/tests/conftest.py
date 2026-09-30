"""Fixtures da suíte.

Os testes rodam num banco próprio (nome terminando em _test), recriado a cada execução.
Cada teste roda dentro de uma transação desfeita no final.
"""
import os
from types import SimpleNamespace

from sqlalchemy.engine import make_url

_base = make_url(os.environ.get("DATABASE_URL", "postgresql+psycopg://fabri:fabri@localhost:5435/fabricontrol"))
_url = make_url(os.environ.get("TEST_DATABASE_URL") or _base.set(database=f"{_base.database}_test"))
if not (_url.database or "").endswith("_test"):
    raise RuntimeError("Os testes apagam o banco: use um banco cujo nome termine em _test.")

# Precisa vir antes de qualquer import de app.*, que lê a configuração uma vez só.
os.environ.update(
    {
        "DATABASE_URL": _url.render_as_string(hide_password=False),
        "ENVIRONMENT": "test",
        "JWT_SECRET": "segredo-usado-somente-nos-testes-automatizados",
    }
)

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app import login_guard  # noqa: E402
from app.db import API_DIR, engine, get_db  # noqa: E402
from app.main import app  # noqa: E402

SETUP = {"nome": "Admin Fábrica", "email": "admin@fabrica.com", "senha": "senha-admin-123"}
SENHA_PADRAO = "senha-usuario-123"


def alembic_config() -> Config:
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.attributes["configure_logger"] = False
    return cfg


@pytest.fixture(scope="session", autouse=True)
def banco_de_teste():
    manutencao = create_engine(_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with manutencao.connect() as conn:
        existe = conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :nome"), {"nome": _url.database})
        if not existe:
            conn.execute(text(f'CREATE DATABASE "{_url.database}"'))
    manutencao.dispose()
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    command.upgrade(alembic_config(), "head")
    yield
    engine.dispose()


@pytest.fixture
def db():
    conn = engine.connect()
    trans = conn.begin()
    session = Session(bind=conn, join_transaction_mode="create_savepoint")
    app.dependency_overrides[get_db] = lambda: session
    login_guard._falhas.clear()
    try:
        yield session
    finally:
        app.dependency_overrides.pop(get_db, None)
        session.close()
        trans.rollback()
        conn.close()


@pytest.fixture
def client(db):
    # Sem "with": o lifespan (migrações) não roda nos testes.
    return TestClient(app)


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin(client) -> SimpleNamespace:
    resp = client.post("/setup", json=SETUP)
    assert resp.status_code == 200, resp.text
    return SimpleNamespace(id=resp.json()["user"]["id"], headers=auth(resp.json()["access_token"]))


@pytest.fixture
def usuario(client, admin):
    """Cria um usuário com o perfil pedido e devolve já logado."""
    criados = 0

    def criar(perfil: str) -> SimpleNamespace:
        nonlocal criados
        criados += 1
        email = f"{perfil}{criados}@fabrica.com"
        resp = client.post(
            "/usuarios",
            headers=admin.headers,
            json={"nome": f"Usuário {perfil}", "email": email, "senha": SENHA_PADRAO, "perfil": perfil},
        )
        assert resp.status_code == 201, resp.text
        login = client.post("/auth/login", json={"email": email, "senha": SENHA_PADRAO})
        assert login.status_code == 200, login.text
        return SimpleNamespace(id=resp.json()["id"], email=email, headers=auth(login.json()["access_token"]))

    return criar


@pytest.fixture
def setor(client, admin) -> dict:
    resp = client.post("/setores", headers=admin.headers, json={"codigo": "cor", "nome": "Corte"})
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture
def nova_maquina(client, admin, setor):
    seq = 0

    def criar(**extra) -> dict:
        nonlocal seq
        seq += 1
        payload = {"codigo": f"COR-{seq:02d}", "nome": f"Guilhotina {seq}", "setor_id": setor["id"], "ciclo_padrao_seg": 12}
        resp = client.post("/maquinas", headers=admin.headers, json={**payload, **extra})
        assert resp.status_code == 201, resp.text
        return resp.json()

    return criar
