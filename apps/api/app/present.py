from datetime import datetime, timezone

from app.constants import (
    PERFIS,
    STATUS_ETAPA,
    STATUS_MAQUINA,
    STATUS_ORDEM,
    STATUS_RECEBE_ORDEM,
    TIPOS_PARADA,
    TZ,
    inicio_for,
    menu_for,
)
from app.models import Maquina, Operador, OrdemEtapa, OrdemProducao, Parada, Produto, Turno, Usuario
from app.schemas import (
    EtapaFilaOut,
    MaquinaOut,
    MenuItem,
    OperadorOut,
    OrdemDetalheOut,
    OrdemEtapaOut,
    OrdemEventoOut,
    OrdemOut,
    ParadaOut,
    ProdutoOut,
    RoteiroOut,
    TurnoOut,
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


def horario(t: Turno) -> str:
    return f"{t.inicio:%H:%M} às {t.fim:%H:%M}"


def turno_out(t: Turno, operadores: int = 0) -> TurnoOut:
    return TurnoOut(
        id=t.id,
        codigo=t.codigo,
        nome=t.nome,
        inicio=f"{t.inicio:%H:%M}",
        fim=f"{t.fim:%H:%M}",
        duracao_min=t.duracao_min,
        vira_meia_noite=t.vira_meia_noite,
        ativo=t.ativo,
        operadores=operadores,
    )


def operador_out(o: Operador) -> OperadorOut:
    return OperadorOut(
        id=o.id,
        matricula=o.matricula,
        nome=o.nome,
        turno_id=o.turno_id,
        turno_nome=o.turno.nome,
        turno_horario=horario(o.turno),
        setor_id=o.setor_id,
        setor_nome=o.setor.nome,
        ativo=o.ativo,
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
                operador_nome=e.operador.nome if e.operador else None,
                boas=e.boas,
                refugo=e.refugo,
                iniciada_em=e.iniciada_em,
                concluida_em=e.concluida_em,
            )
            for e in o.etapas
        ],
        criado_em=o.criado_em,
        concluida_em=o.concluida_em,
    )


def etapa_fila_out(o: OrdemProducao, e: OrdemEtapa, maquina: Maquina) -> EtapaFilaOut:
    ciclo = float(e.tempo_padrao_seg if e.tempo_padrao_seg is not None else maquina.ciclo_padrao_seg)
    proxima = next((x for x in o.etapas if x.sequencia > e.sequencia), None)
    return EtapaFilaOut(
        ordem_id=o.id,
        ordem_numero=o.numero,
        ordem_status=o.status,
        motivo_pausa=o.motivo_pausa,
        produto_codigo=o.produto.codigo,
        produto_descricao=o.produto.descricao,
        unidade=o.produto.unidade,
        quantidade=o.quantidade,
        prioridade=o.prioridade,
        prazo=o.prazo,
        atrasada=ordem_atrasada(o),
        sequencia=e.sequencia,
        total_etapas=len(o.etapas),
        operacao=e.operacao,
        proximo_setor=proxima.setor.nome if proxima else None,
        status=e.status,
        carga_min=round(o.saldo(e) * ciclo / 60, 1),
        iniciada_em=e.iniciada_em,
        operador_nome=e.operador.nome if e.operador else None,
        entrada=o.entrada(e),
        boas=e.boas,
        refugo=e.refugo,
        saldo=o.saldo(e),
    )


def parada_out(p: Parada) -> ParadaOut:
    fim = p.fim or datetime.now(timezone.utc)
    return ParadaOut(
        id=p.id,
        maquina_id=p.maquina_id,
        maquina_codigo=p.maquina.codigo,
        maquina_nome=p.maquina.nome,
        setor_nome=p.maquina.setor.nome,
        motivo_codigo=p.motivo.codigo,
        motivo_descricao=p.motivo.descricao,
        tipo=p.motivo.tipo,
        tipo_label=TIPOS_PARADA[p.motivo.tipo],
        planejada=p.motivo.tipo == "planejada",
        inicio=p.inicio,
        fim=p.fim,
        duracao_min=round((fim - p.inicio).total_seconds() / 60, 1),
        operador_nome=p.operador.nome if p.operador else None,
        ordem_numero=p.ordem.numero if p.ordem else None,
        observacao=p.observacao,
    )


def ordem_detalhe_out(o: OrdemProducao) -> OrdemDetalheOut:
    return OrdemDetalheOut(
        **ordem_out(o).model_dump(),
        eventos=[
            OrdemEventoOut(em=ev.em, tipo=ev.tipo, descricao=ev.descricao, usuario_nome=ev.usuario.nome if ev.usuario else None)
            for ev in reversed(o.eventos)
        ],
    )
