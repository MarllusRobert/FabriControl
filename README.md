# FabriControl

Sistema de controle de produção industrial (metalúrgica): cadastros da fábrica, ordens de produção, apontamento no chão de fábrica, pipeline de dados das máquinas e indicadores como o OEE.

O projeto é conduzido em **Scrum no Jira** (projeto `FC`, sprints de 1 semana). O backlog completo e o guia de uso do Jira estão em [`jira/`](jira/GUIA-JIRA.md).

## Stack

| Camada | Tecnologia |
|---|---|
| API | Python 3.12, FastAPI, SQLAlchemy 2, Alembic |
| Banco | PostgreSQL 16 |
| Web | Next.js 15, React 19, TypeScript |
| Infra | Docker Compose, GitHub Actions |

## Como rodar

Pré-requisito: Docker Desktop.

```bash
cp .env.example .env        # ajuste as senhas se quiser
docker compose up -d --build
```

| Serviço | Endereço |
|---|---|
| Web | http://localhost:3040 |
| API (Swagger) | http://localhost:8040/docs |
| PostgreSQL | localhost:5435 |

No primeiro acesso a tela pede para criar o administrador. Para carregar centros de trabalho e máquinas de exemplo:

```bash
docker compose exec api python -m app.demo
```

## Simulador de CLP

Gera dados de máquina minuto a minuto (estado, alarme, ciclos, peças boas e refugo, contador do CLP), um CSV por máquina e por dia, para testar o pipeline de dados sem fábrica real. Parte das linhas sai suja de propósito (lacunas, duplicatas, linhas fora de ordem, estados fora do padrão, valores negativos e picos, nulos, timestamps em outro formato, vírgula decimal, cabeçalho repetido).

```bash
docker compose exec api python -m app.simulador_clp --maquinas 5 --dias 7 --sujeira 0.01 --semente 42
docker compose exec api python -m app.simulador_clp --do-banco --dias 30   # máquinas cadastradas
```

A saída fica em `apps/api/dados/clp/` (fora do git): `<MAQUINA>/<AAAA-MM-DD>.csv`, `gabarito.csv` (totais verdadeiros por máquina e dia, antes da sujeira), `anomalias.csv` (cada sujeira injetada) e `parametros.json`. Mesma semente, mesmos dados.

## Perfis de acesso

| Perfil | Acessa |
|---|---|
| Administrador | Tudo, inclusive usuários |
| PCP | Painel, Kanban, Fila por máquina (sequencia), cadastros, equipe e motivos |
| Supervisor | Painel, tela do operador, Kanban, Fila (consulta), equipe e motivos |
| Operador | Tela do operador (inicia, aponta, registra paradas), Kanban e máquinas |
| Qualidade | Painel, Kanban, máquinas, produtos e motivos (consulta) |

Senhas com bcrypt, token JWT com validade, bloqueio após 5 tentativas erradas e troca de senha que encerra as sessões antigas.

## Testes

```bash
docker compose exec api pip install -r requirements-dev.txt
docker compose exec api python -m pytest
docker compose exec web npx tsc --noEmit
```

Os testes da API usam um banco próprio (`fabricontrol_test`), recriado a cada execução. O CI roda testes, checagem de migrações (`alembic check`), tipos e build do frontend a cada push e pull request.

## Fluxo de trabalho

- Cada item do Jira vira uma branch: `FC-12-login-perfis`.
- Commits citam a chave (`FC-12 Endpoints de login`) para aparecerem na tarefa do Jira.
- Pull request só entra na `main` com o CI verde.
