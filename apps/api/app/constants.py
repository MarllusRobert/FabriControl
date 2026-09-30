from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Sao_Paulo")

TELAS_LABEL = {
    "painel": "Painel da fábrica",
    "kanban": "Kanban da produção",
    "maquinas": "Máquinas e centros de trabalho",
    "produtos": "Produtos e roteiros de fabricação",
    "usuarios": "Usuários",
}

ACOES_LABEL = {
    "editar_cadastros": "Cadastrar e editar máquinas, centros de trabalho e produtos",
    "planejar_producao": "Criar, liberar e cancelar ordens de produção",
    "movimentar_producao": "Iniciar, concluir e pausar etapas no Kanban",
    "gerenciar_usuarios": "Cadastrar usuários e definir perfis",
}

# Perfis fixos da fábrica: cada função vê só o que é dela.
PERFIS = {
    "administrador": {
        "label": "Administrador",
        "telas": list(TELAS_LABEL),
        "acoes": list(ACOES_LABEL),
    },
    "pcp": {
        "label": "PCP (planejamento)",
        "telas": ["painel", "kanban", "maquinas", "produtos"],
        "acoes": ["editar_cadastros", "planejar_producao", "movimentar_producao"],
    },
    "supervisor": {
        "label": "Supervisor de produção",
        "telas": ["painel", "kanban", "maquinas", "produtos"],
        "acoes": ["movimentar_producao"],
    },
    "operador": {
        "label": "Operador",
        "telas": ["kanban", "maquinas"],
        "acoes": ["movimentar_producao"],
    },
    "qualidade": {
        "label": "Qualidade",
        "telas": ["painel", "kanban", "maquinas", "produtos"],
        "acoes": [],
    },
}

MENU = [
    ("painel", "Painel", "/painel"),
    ("kanban", "Kanban", "/kanban"),
    ("maquinas", "Máquinas", "/maquinas"),
    ("produtos", "Produtos", "/produtos"),
    ("usuarios", "Usuários", "/usuarios"),
]

STATUS_MAQUINA = {
    "ativa": "Ativa",
    "manutencao": "Em manutenção",
    "inativa": "Inativa",
}
# Só máquina ativa pode receber ordem de produção.
STATUS_RECEBE_ORDEM = ("ativa",)

STATUS_ORDEM = {
    "planejada": "Planejada",
    "liberada": "Liberada",
    "em_producao": "Em produção",
    "pausada": "Pausada",
    "concluida": "Concluída",
    "cancelada": "Cancelada",
}
ORDEM_ABERTA = ("liberada", "em_producao", "pausada")

STATUS_ETAPA = {
    "aguardando": "Aguardando",
    "na_fila": "Na fila",
    "em_andamento": "Em andamento",
    "concluida": "Concluída",
}

PRIORIDADES = {"baixa": "Baixa", "normal": "Normal", "alta": "Alta", "urgente": "Urgente"}


def menu_for(telas: list[str]) -> list[dict[str, str]]:
    permitidas = set(telas)
    return [{"tela": tela, "label": label, "href": href} for tela, label, href in MENU if tela in permitidas]


def inicio_for(telas: list[str]) -> str:
    return next((href for tela, _, href in MENU if tela in telas), "/conta")
