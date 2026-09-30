# FabriControl no Jira — backlog, tarefas e sprints

Sistema de controle de produção industrial (metalúrgica) com foco em **controle, organização e visualização das informações**, desenvolvido em Scrum e gerenciado no Jira.

| Item | Valor |
|---|---|
| Projeto | FabriControl |
| Chave | `FC` (as tarefas ficam FC-1, FC-2...) |
| Método | Scrum, sprints de 1 semana |
| Backlog | 9 épicos, 34 histórias/tarefas, 17 subtarefas, 122 pontos |
| Arquivo | `fabricontrol-backlog.csv` (gerado por `gerar_backlog.py`) |

## 1. Criar a conta (grátis até 10 usuários)

1. Acesse **atlassian.com/software/jira/free** e entre com o seu Gmail.
2. Nome do site: por exemplo `zionsistemas` (fica `zionsistemas.atlassian.net`).
3. Quando perguntar o tipo de trabalho, escolha **Desenvolvimento de software**.

## 2. Criar o projeto

1. **Projetos → Criar projeto → Desenvolvimento de software → Scrum**.
2. Tipo: **gerenciado pela empresa** (company-managed). Ele aceita a importação com pontos e subtarefas sem ajuste.
3. Nome **FabriControl**, chave **FC**.
4. Em **Configurações do projeto → Fluxo de trabalho**, deixe os status: `A fazer → Em andamento → Em revisão → Concluído`.

## 3. Importar o backlog (CSV)

1. Engrenagem (canto superior direito) → **Sistema → Importação de sistema externo → CSV**.
2. Envie `fabricontrol-backlog.csv`. Codificação **UTF-8**, separador **vírgula**.
3. Projeto de destino: **FabriControl**.
4. Mapeamento das colunas:

| Coluna do CSV | Campo do Jira |
|---|---|
| Issue Id | Issue Id |
| Parent Id | Parent Id |
| Issue Type | Tipo de item |
| Summary | Resumo |
| Description | Descrição |
| Priority | Prioridade |
| Story Points | Story Points (ou "Estimativa de pontos da história") |
| Labels (as duas colunas) | Rótulos |

5. Marque **"Mapear valores"** para *Issue Type* e ligue: `Epic → Épico`, `Story → História`, `Task → Tarefa`, `Sub-task → Subtarefa`.
6. **Validar** → **Iniciar importação**. No fim devem aparecer **60 itens** criados.

## 4. Montar as sprints

Cada item já vem com um rótulo `sprint-1` … `sprint-6` com a sugestão de planejamento.

| Sprint | Meta da sprint | Pontos |
|---|---|---|
| Sprint 1 | Projeto rodando em Docker com CI, login por perfil e cadastro de máquinas | 14 |
| Sprint 2 | Cadastros completos, ordens de produção com status e histórico e Kanban por etapa do processo | 22 |
| Sprint 3 | Operador apontando produção, refugo e paradas; simulador de dados das máquinas | 19 |
| Sprint 4 | Pipeline de dados (ingestão, limpeza, modelo analítico, qualidade) e cálculo do OEE | 24 |
| Sprint 5 | Painéis da fábrica e por máquina, Pareto e Gantt | 20 |
| Sprint 6 | Qualidade, relatórios, alertas, modo TV e entrega | 23 |

Para cada sprint:
1. No **Backlog**, clique em **Criar sprint**.
2. Pesquise `labels = sprint-1` → selecione tudo → arraste para a sprint (ou **Alteração em massa → Sprint**).
3. **Iniciar sprint**: duração de 1 semana e a meta da tabela acima.

## 5. Quadro (board)

- Colunas: **A fazer · Em andamento · Em revisão · Concluído**.
- Limite de WIP em **Em andamento = 2** (Configurações do quadro → Colunas).
- Raias por **épico**, para ver o avanço de cada frente.
- Ritual de cada dia: mover os cartões, comentar o que foi feito e registrar horas (**Registrar trabalho**).

## 6. Filtros JQL (salvar como filtros)

| Nome do filtro | JQL |
|---|---|
| Minha sprint | `project = FC AND sprint in openSprints() AND assignee = currentUser() ORDER BY rank` |
| Pipeline de dados em aberto | `project = FC AND labels = dados AND statusCategory != Done` |
| Prioridades altas | `project = FC AND priority in (Highest, High) AND statusCategory != Done ORDER BY priority DESC` |
| Bugs da semana | `project = FC AND type = Bug AND created >= -7d` |
| Itens de um épico | `project = FC AND parent = FC-5` |
| Atrasados na sprint | `project = FC AND sprint in openSprints() AND statusCategory = "To Do" AND updated <= -3d` |

## 7. Painel (dashboard) "FabriControl — visão do projeto"

**Painéis → Criar painel** e adicione os gadgets:
- **Burndown da sprint** e **Saúde da sprint**;
- **Gráfico de pizza** por rótulo (frente de trabalho) e por status;
- **Criados x resolvidos** (últimos 30 dias);
- **Estatísticas bidimensionais**: épico x status;
- **Resultados do filtro**: "Minha sprint".

Relatórios do projeto para acompanhar: **Burndown**, **Velocidade**, **Fluxo cumulativo** e **Relatório de épico**.

## 8. Ligar o Jira ao GitHub

1. No Jira: **Aplicativos → Explorar aplicativos → "GitHub for Jira"** (gratuito) → conectar a conta `MarllusRobert` e o repositório `FabriControl`.
2. Padrões que ligam o código às tarefas:
   - branch: `FC-14-tela-do-operador`
   - commit: `FC-14 cria tela do operador para tablet`
   - pull request: `FC-14 Tela do operador`
   - smart commit: `FC-14 #comment layout ajustado para tablet #time 2h`
3. Resultado: cada cartão do Jira mostra as branches, os commits e os pull requests dele.

## 9. Encerramento de cada sprint

1. **Revisão**: mostrar o que ficou pronto (prints ou vídeo curto).
2. **Retrospectiva**: o que foi bem, o que melhorar, uma ação para a próxima sprint (comentário no épico ou página no Confluence).
3. **Concluir sprint**: o que não terminou volta para o backlog ou vai para a próxima.
4. Conferir o gráfico de **Velocidade** para planejar a próxima.

## 10. Como vai aparecer no currículo (depois de rodar as sprints)

> **Jira:** gestão do projeto FabriControl em Scrum: backlog com épicos, histórias com critérios de aceite e estimativa em pontos, sprints semanais com meta, quadro com limite de WIP, filtros JQL, painel com burndown e velocidade, e integração com o GitHub (branches, commits e pull requests vinculados às tarefas).
