from datetime import datetime

from app.constants import (
    PERFIS,
    STATUS_ETAPA,
    STATUS_MAQUINA,
    STATUS_ORDEM,
    STATUS_RECEBE_ORDEM,
    TZ,
    inicio_for,
    menu_for,
)
from app.models import Maquina, OrdemProducao, Produto, Usuario
from app.schemas import (
    MaquinaOut,
    MenuItem,
    OrdemDetalheOut,
    OrdemEtapaOut,
    OrdemEventoOut,
    OrdemOut,
    ProdutoOut,
    RoteiroOut,
    UsuarioOut,
)


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


def ordem_atrasada(o: OrdemProducao) -> bool:
    if o.prazo is None or o.status in ("concluida", "cancelada"):
        return False
    return o.prazo < datetime.now(TZ).date()


def ordem_out(o: OrdemProducao) -> OrdemOut:
    atual = o.etapa_atual
    return OrdemOut(
        id=o.id,
        numero=o.numero,
        produto_id=o.produto_id,
        produto_codigo=o.produto.codigo,
        produto_descricao=o.produto.descricao,
        comprimento_mm=o.produto.comprimento_mm,
        unidade=o.produto.unidade,
        quantidade=o.quantidade,
        prazo=o.prazo,
        prioridade=o.prioridade,
        status=o.status,
        status_label=STATUS_ORDEM[o.status],
        atrasada=ordem_atrasada(o),
        motivo_pausa=o.motivo_pausa,
        observacao=o.observacao,
        etapa_atual=atual.sequencia if atual is not None and o.status != "planejada" else None,
        total_etapas=len(o.etapas),
        etapas=[
            OrdemEtapaOut(
                sequencia=e.sequencia,
                setor_id=e.setor_id,
                setor_nome=e.setor.nome,
                operacao=e.operacao,
                status=e.status,
                status_label=STATUS_ETAPA[e.status],
                maquina_id=e.maquina_id,
                maquina_codigo=e.maquina.codigo if e.maquina else None,
                iniciada_em=e.iniciada_em,
                concluida_em=e.concluida_em,
            )
            for e in o.etapas
        ],
        criado_em=o.criado_em,
        concluida_em=o.concluida_em,
    )


def ordem_detalhe_out(o: OrdemProducao) -> OrdemDetalheOut:
    return OrdemDetalheOut(
        **ordem_out(o).model_dump(),
        eventos=[
            OrdemEventoOut(em=ev.em, tipo=ev.tipo, descricao=ev.descricao, usuario_nome=ev.usuario.nome if ev.usuario else None)
            for ev in reversed(o.eventos)
        ],
    )
