"""Gera o CSV de importação do backlog do FabriControl para o Jira Cloud.

Hierarquia pelas colunas "Issue Id" / "Parent Id": épico → história/tarefa → subtarefa.
"""
import csv
from pathlib import Path

OUT = Path(__file__).with_name("fabricontrol-backlog.csv")

EPICOS = [
    ("E1", "Fundação e infraestrutura",
     "Repositório, ambiente em Docker, integração contínua e controle de acesso por perfil."),
    ("E2", "Cadastros da fábrica",
     "Máquinas, produtos com roteiro de fabricação, operadores, turnos e motivos de parada e refugo."),
    ("E3", "Ordens de produção",
     "Planejamento (PCP), liberação, fila por máquina e acompanhamento do status das ordens."),
    ("E4", "Apontamento de produção",
     "Registro no chão de fábrica: início e fim das operações, peças boas, refugo e paradas."),
    ("E5", "Pipeline de dados",
     "Ingestão dos dados das máquinas, limpeza, carga no modelo analítico e monitoramento das execuções."),
    ("E6", "Indicadores e visualização",
     "OEE, painéis da fábrica e por máquina, Pareto, Gantt, modo TV (Andon) e alertas."),
    ("E7", "Qualidade",
     "Inspeção por amostragem, não conformidades e ações corretivas."),
    ("E8", "Relatórios",
     "Relatórios gerenciais por período, máquina, turno e operador, com exportação."),
    ("E9", "Entrega e documentação",
     "Dados de demonstração, documentação técnica, publicação e vídeo de apresentação."),
]

# (id, épico, tipo, resumo, história, critérios, prioridade, pontos, rótulo, sprint)
ITENS = [
    ("S1", "E1", "Story", "Configurar repositório e ambiente Docker (API, web e PostgreSQL)",
     "Como desenvolvedor, quero subir o sistema inteiro com um comando, para que qualquer pessoa rode o projeto igual.",
     ["docker compose up sobe API, web e banco", "Variáveis sensíveis só no .env (fora do Git)",
      "README com o passo a passo"], "High", 3, "infra", "sprint-1"),
    ("S2", "E1", "Story", "Integração contínua no GitHub Actions",
     "Como time, queremos que cada push rode testes e build, para não quebrar a versão principal.",
     ["Testes da API com PostgreSQL de serviço", "Checagem de migrações", "Checagem de tipos e build do frontend",
      "Pull request só entra com CI verde"], "High", 3, "infra", "sprint-1"),
    ("S3", "E1", "Story", "Login e perfis de acesso (Administrador, PCP, Supervisor, Operador, Qualidade)",
     "Como administrador, quero que cada pessoa veja só o que é da função dela, para proteger os dados e simplificar as telas.",
     ["Login com senha criptografada e token com validade", "Permissão por tela e por ação",
      "Bloqueio após tentativas erradas"], "High", 5, "backend", "sprint-1"),
    ("S4", "E2", "Story", "Cadastro de máquinas e centros de trabalho",
     "Como PCP, quero cadastrar as máquinas com setor e tempo de ciclo padrão, para planejar e medir a performance.",
     ["Código, nome, setor, tempo de ciclo padrão e status", "Máquina inativa não recebe ordem",
      "Busca e filtro por setor"], "High", 3, "cadastros", "sprint-1"),
    ("S5", "E2", "Story", "Cadastro de produtos e roteiro de fabricação",
     "Como PCP, quero definir por quais operações e máquinas cada produto passa, com o tempo padrão por peça.",
     ["Produto com código, descrição e unidade", "Roteiro com sequência de operações, máquina e tempo padrão",
      "Validação de sequência sem repetição"], "High", 5, "cadastros", "sprint-2"),
    ("S6", "E2", "Story", "Cadastro de operadores e turnos",
     "Como supervisor, quero cadastrar operadores e turnos, para saber quem produziu o quê e quando.",
     ["Turnos com horário de início e fim (inclusive virando a meia-noite)", "Operador vinculado a turno e setor"],
     "Medium", 2, "cadastros", "sprint-2"),
    ("S7", "E2", "Story", "Motivos de parada e de refugo",
     "Como supervisor, quero uma lista padronizada de motivos, para que os indicadores sejam comparáveis.",
     ["Parada planejada (setup, manutenção preventiva) ou não planejada (quebra, falta de material)",
      "Motivos de refugo por categoria"], "Medium", 2, "cadastros", "sprint-2"),
    ("S8", "E3", "Story", "Criar e liberar ordem de produção",
     "Como PCP, quero criar ordens com produto, quantidade, prazo e prioridade e liberá-las para a fábrica.",
     ["Número sequencial da ordem", "Operações geradas a partir do roteiro do produto",
      "Só ordens liberadas aparecem para o operador"], "High", 5, "ordens", "sprint-2"),
    ("S9", "E3", "Story", "Status da ordem com histórico",
     "Como gestor, quero acompanhar em que etapa cada ordem está e quem mudou, para ter rastreabilidade.",
     ["Planejada → Liberada → Em produção → Pausada → Concluída / Cancelada",
      "Histórico com data, usuário e motivo", "Ordem atrasada destacada"], "High", 3, "ordens", "sprint-2"),
    ("S31", "E3", "Story", "Kanban da produção por etapa do processo (Desbobinador → Guilhotina → Dobradeira)",
     "Como supervisor, quero ver cada ordem andando de processo em processo, para saber onde está cada lote e o que vem a seguir.",
     ["Uma coluna por setor, na ordem do fluxo da fábrica, mais Planejadas e Concluídas",
      "Cartão só avança para a próxima etapa do roteiro (arrastar ou botão)",
      "Iniciar pede a máquina quando o setor tem mais de uma",
      "Pausa exige motivo e fica destacada", "Atualiza sozinho"], "High", 5, "ordens", "sprint-2"),
    ("S10", "E3", "Story", "Fila de produção por máquina (sequenciamento)",
     "Como PCP, quero ordenar a fila de cada máquina arrastando as ordens, para priorizar o que é urgente.",
     ["Arrastar e soltar muda a sequência", "Fila mostra carga em horas por máquina"],
     "Medium", 5, "ordens", "sprint-3"),
    ("S11", "E4", "Story", "Tela do operador: iniciar, pausar e finalizar operação",
     "Como operador, quero uma tela simples no tablet para apontar minha produção sem papel.",
     ["Botões grandes, próprio para tablet", "Mostra a próxima ordem da fila da máquina",
      "Registra horário real de início e fim"], "Highest", 5, "apontamento", "sprint-3"),
    ("S12", "E4", "Story", "Apontar peças boas e refugo com motivo",
     "Como operador, quero informar quantas peças boas e quantas refugadas, para calcular qualidade e saldo.",
     ["Refugo exige motivo", "Não permite apontar acima do saldo da ordem",
      "Saldo da ordem atualizado na hora"], "Highest", 3, "apontamento", "sprint-3"),
    ("S13", "E4", "Story", "Registrar parada de máquina",
     "Como operador, quero registrar quando a máquina para e o motivo, para medir disponibilidade.",
     ["Início e fim da parada, com motivo obrigatório", "Parada em aberto aparece em destaque para o supervisor"],
     "Highest", 3, "apontamento", "sprint-3"),
    ("S14", "E5", "Story", "Simulador de dados das máquinas (CLP)",
     "Como time de dados, queremos gerar dados realistas de ciclos e estados das máquinas, para testar o pipeline sem fábrica real.",
     ["Gera CSV por máquina a cada minuto: estado, ciclos e peças", "Inclui falhas e dados sujos de propósito",
      "Parâmetros de quantidade de máquinas e dias"], "High", 3, "dados", "sprint-3"),
    ("S15", "E5", "Story", "Ingestão dos arquivos das máquinas com validação de esquema",
     "Como time de dados, queremos ler os arquivos, validar e separar as linhas inválidas, para confiar na base.",
     ["Valida colunas, tipos e faixas", "Linhas rejeitadas vão para uma tabela com o motivo",
      "Arquivo já processado não é lido duas vezes"], "High", 5, "dados", "sprint-4"),
    ("S16", "E5", "Story", "Limpeza e padronização dos dados",
     "Como analista, quero dados sem duplicados e no mesmo padrão, para os indicadores baterem.",
     ["Remove duplicados", "Converte fuso horário e unidades", "Preenche turno pelo horário"],
     "High", 3, "dados", "sprint-4"),
    ("S17", "E5", "Story", "Modelo analítico (fatos e dimensões)",
     "Como analista, quero um modelo em estrela, para consultar produção e paradas de forma rápida.",
     ["fato_producao e fato_parada", "dim_maquina, dim_produto, dim_turno, dim_operador e dim_tempo",
      "Carga incremental"], "High", 5, "dados", "sprint-4"),
    ("S18", "E5", "Story", "Agendamento e monitoramento do pipeline",
     "Como responsável pelos dados, quero ver cada execução do pipeline, para agir rápido quando falhar.",
     ["Execução agendada", "Registro de início, fim, linhas lidas, carregadas e rejeitadas",
      "Tela de execuções com status"], "Medium", 3, "dados", "sprint-4"),
    ("S19", "E5", "Story", "Testes de qualidade de dados",
     "Como time de dados, queremos checagens automáticas, para perceber dado errado antes do painel.",
     ["Checa nulos, faixas e contagens entre origem e destino", "Falha de qualidade marca a execução com alerta"],
     "Medium", 3, "dados", "sprint-4"),
    ("S20", "E6", "Story", "Cálculo do OEE por máquina, turno e dia",
     "Como gestor, quero o OEE (disponibilidade × performance × qualidade), para medir a eficiência real da fábrica.",
     ["Disponibilidade = tempo produzindo / tempo planejado", "Performance = (peças × ciclo padrão) / tempo produzindo",
      "Qualidade = peças boas / peças totais", "Resultados conferidos com casos de teste calculados à mão"],
     "Highest", 5, "indicadores", "sprint-4"),
    ("S21", "E6", "Story", "Painel geral da fábrica",
     "Como diretor, quero ver num só lugar OEE, produção x meta, refugo e paradas, para decidir rápido.",
     ["Filtros por período, setor e turno", "Comparação com o período anterior",
      "Atualiza sozinho"], "High", 5, "indicadores", "sprint-5"),
    ("S22", "E6", "Story", "Painel por máquina em tempo real",
     "Como supervisor, quero ver o estado de cada máquina (produzindo, parada, setup), para agir na hora.",
     ["Cartão por máquina com cor do estado", "Ordem atual, peças e tempo parado"],
     "High", 5, "indicadores", "sprint-5"),
    ("S23", "E6", "Story", "Pareto de paradas e de refugo",
     "Como engenheiro de processo, quero saber os motivos que mais causam perda, para atacar o que mais pesa.",
     ["Gráfico de Pareto com percentual acumulado", "Filtro por máquina e período"],
     "Medium", 3, "indicadores", "sprint-5"),
    ("S24", "E6", "Story", "Gantt das ordens por máquina",
     "Como PCP, quero ver a linha do tempo das ordens em cada máquina, planejado x realizado.",
     ["Barras planejadas e realizadas", "Ordem atrasada em destaque"], "Medium", 5, "indicadores", "sprint-5"),
    ("S25", "E6", "Story", "Modo TV (Andon) para o chão de fábrica",
     "Como supervisor, quero uma tela grande na fábrica com o status das máquinas, para todos verem o andamento.",
     ["Tela cheia, fonte grande, atualização automática", "Sem necessidade de interação"],
     "Low", 3, "indicadores", "sprint-6"),
    ("S26", "E6", "Story", "Alertas de produção",
     "Como supervisor, quero ser avisado quando algo sai do normal, para não descobrir só no fim do turno.",
     ["Máquina parada acima do limite", "OEE abaixo da meta", "Ordem com risco de atraso"],
     "Medium", 3, "indicadores", "sprint-6"),
    ("S27", "E7", "Story", "Inspeção por amostragem",
     "Como inspetor, quero registrar medições das peças por amostragem, para garantir a especificação.",
     ["Plano de inspeção por produto com limites", "Medida fora do limite reprova a amostra"],
     "Medium", 3, "qualidade", "sprint-6"),
    ("S28", "E7", "Story", "Não conformidade e ação corretiva",
     "Como qualidade, quero registrar não conformidades e acompanhar a ação corretiva até fechar.",
     ["Abertura, responsável, prazo e status", "Vínculo com ordem e máquina"],
     "Medium", 3, "qualidade", "sprint-6"),
    ("S29", "E8", "Story", "Relatório de produção por período com exportação",
     "Como gestor, quero exportar a produção por período, máquina e produto, para análises e reuniões.",
     ["Filtros por período, máquina e produto", "Exporta CSV e Excel"], "Medium", 3, "relatorios", "sprint-6"),
    ("S30", "E8", "Story", "Relatório de eficiência por turno e operador",
     "Como supervisor, quero comparar turnos e operadores, para orientar treinamento.",
     ["OEE, peças e refugo por turno e operador", "Ranking e evolução no período"],
     "Low", 3, "relatorios", "sprint-6"),
    ("T1", "E9", "Task", "Dados de demonstração de 90 dias",
     "Gerar base de demonstração com máquinas, ordens, apontamentos e paradas para apresentar o sistema.",
     ["Script idempotente", "Dados coerentes com os indicadores"], "Medium", 2, "entrega", "sprint-5"),
    ("T2", "E9", "Task", "Documentação técnica e dicionário de dados",
     "README, diagrama de arquitetura, fluxo do pipeline e dicionário das tabelas analíticas.",
     ["Arquitetura e decisões registradas", "Dicionário de dados de fatos e dimensões"],
     "Medium", 2, "entrega", "sprint-6"),
    ("T3", "E9", "Task", "Publicação da demonstração e vídeo de apresentação",
     "Publicar a vitrine no GitHub com telas e vídeo narrado.",
     ["Vitrine pública com telas e vídeo", "Link no currículo e no LinkedIn"], "Low", 3, "entrega", "sprint-6"),
]

SUBTAREFAS = {
    "S3": ["Modelo de usuários, grupos e permissões", "Endpoints de login e troca de senha",
           "Tela de login e guarda de rotas no frontend", "Testes de permissão"],
    "S11": ["API de início, pausa e fim da operação", "Tela do operador para tablet", "Testes do fluxo de apontamento"],
    "S15": ["Leitor de arquivos com controle de processados", "Validação de esquema e tabela de rejeitados",
            "Testes com arquivos sujos"],
    "S17": ["Migrações das tabelas de fatos e dimensões", "Carga incremental", "Consultas de conferência"],
    "S20": ["Função de cálculo do OEE", "Casos de teste calculados à mão", "Endpoint de OEE com filtros",
            "Gráfico de OEE no painel"],
}


def descricao(historia, criterios):
    linhas = [historia, "", "Critérios de aceite:"] + [f"- {c}" for c in criterios]
    return "\n".join(linhas)


def main():
    cabecalho = ["Issue Id", "Parent Id", "Issue Type", "Summary", "Description",
                 "Priority", "Story Points", "Labels", "Labels"]
    linhas = []
    for eid, nome, desc in EPICOS:
        linhas.append([eid, "", "Epic", nome, desc, "Medium", "", "fabricontrol", ""])
    for iid, epico, tipo, resumo, historia, criterios, prio, pontos, rotulo, sprint in ITENS:
        linhas.append([iid, epico, tipo, resumo, descricao(historia, criterios), prio, pontos, rotulo, sprint])
        for n, sub in enumerate(SUBTAREFAS.get(iid, []), start=1):
            linhas.append([f"{iid}-{n}", iid, "Sub-task", sub, "", prio, "", rotulo, sprint])

    with OUT.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f, quoting=csv.QUOTE_ALL).writerows([cabecalho] + linhas)
    total_pontos = sum(i[7] for i in ITENS)
    print(f"{OUT.name}: {len(EPICOS)} épicos, {len(ITENS)} histórias/tarefas, "
          f"{sum(len(v) for v in SUBTAREFAS.values())} subtarefas, {total_pontos} pontos")


if __name__ == "__main__":
    main()
