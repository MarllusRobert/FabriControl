from app.constants import PERFIS, STATUS_MAQUINA, STATUS_RECEBE_ORDEM, inicio_for, menu_for
from app.models import Maquina, Usuario
from app.schemas import MaquinaOut, MenuItem, UsuarioOut


def usuario_out(user: Usuario) -> UsuarioOut:
    telas = user.telas
    return UsuarioOut(
        id=user.id,
        nome=user.nome,
        email=user.email,
        perfil=user.perfil,
        perfil_label=PERFIS[user.perfil]["label"],
        ativo=user.ativo,
        telas=telas,
        acoes=user.acoes,
        menu=[MenuItem(**item) for item in menu_for(telas)],
        inicio=inicio_for(telas),
    )


def maquina_out(m: Maquina) -> MaquinaOut:
    ciclo = float(m.ciclo_padrao_seg)
    return MaquinaOut(
        id=m.id,
        codigo=m.codigo,
        nome=m.nome,
        setor_id=m.setor_id,
        setor_nome=m.setor.nome,
        ciclo_padrao_seg=ciclo,
        pecas_por_hora=round(3600 / ciclo, 1),
        status=m.status,
        status_label=STATUS_MAQUINA[m.status],
        recebe_ordem=m.status in STATUS_RECEBE_ORDEM,
        observacao=m.observacao,
        atualizado_em=m.atualizado_em,
    )
