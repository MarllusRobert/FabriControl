from alembic import command

from conftest import alembic_config


def test_modelos_e_migracoes_batem():
    # Falha se algum model mudou sem migração correspondente.
    command.check(alembic_config())
