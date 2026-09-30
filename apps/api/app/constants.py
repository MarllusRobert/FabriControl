from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Sao_Paulo")

TELAS_LABEL = {
    "painel": "Painel da fábrica",
    "maquinas": "Máquinas e centros de trabalho",
    "usuarios": "Usuários",
}

ACOES_LABEL = {
    "editar_cadastros": "Cadastrar e editar máquinas e centros de trabalho",
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
        "telas": ["painel", "maquinas"],
        "acoes": ["editar_cadastros"],
    },
    "supervisor": {
        "label": "Supervisor de produção",
        "telas": ["painel", "maquinas"],
        "acoes": [],
    },
    "operador": {
        "label": "Operador",
        "telas": ["maquinas"],
        "acoes": [],
    },
    "qualidade": {
        "label": "Qualidade",
        "telas": ["painel", "maquinas"],
        "acoes": [],
    },
}

MENU = [
    ("painel", "Painel", "/painel"),
    ("maquinas", "Máquinas", "/maquinas"),
    ("usuarios", "Usuários", "/usuarios"),
]

STATUS_MAQUINA = {
    "ativa": "Ativa",
    "manutencao": "Em manutenção",
    "inativa": "Inativa",
}
# Só máquina ativa pode receber ordem de produção.
STATUS_RECEBE_ORDEM = ("ativa",)


def menu_for(telas: list[str]) -> list[dict[str, str]]:
    permitidas = set(telas)
    return [{"tela": tela, "label": label, "href": href} for tela, label, href in MENU if tela in permitidas]


def inicio_for(telas: list[str]) -> str:
    return next((href for tela, _, href in MENU if tela in telas), "/conta")
