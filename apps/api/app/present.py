from app.constants import PERFIS, STATUS_MAQUINA, STATUS_RECEBE_ORDEM, inicio_for, menu_for
from app.models import Maquina, Produto, Usuario
from app.schemas import MaquinaOut, MenuItem, ProdutoOut, RoteiroOut, UsuarioOut


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


def produto_out(p: Produto) -> ProdutoOut:
    return ProdutoOut(
        id=p.id,
        codigo=p.codigo,
        descricao=p.descricao,
        unidade=p.unidade,
        comprimento_mm=p.comprimento_mm,
        ativo=p.ativo,
        roteiro=[
            RoteiroOut(
                sequencia=e.sequencia,
                setor_id=e.setor_id,
                setor_nome=e.setor.nome,
                operacao=e.operacao,
                tempo_padrao_seg=float(e.tempo_padrao_seg) if e.tempo_padrao_seg is not None else None,
            )
            for e in p.roteiro
        ],
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
