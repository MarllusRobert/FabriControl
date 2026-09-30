"use client";

import { DragEvent, FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { PageHeader } from "../../components/Shell";
import { api } from "../../lib/api";
import { temAcao, useAuth } from "../../lib/auth";
import { Produto, comprimentoLabel, numero } from "../../lib/cadastros";
import {
  Coluna,
  Kanban,
  MaquinaResumo,
  Ordem,
  OrdemDetalhe,
  PRIORIDADE_LABEL,
  Prioridade,
  dataCurta,
  dataHora,
  destinoPermitido,
  etapaAtual,
} from "../../lib/producao";

type AcaoMaquina = "iniciar" | "concluir";
type Pendente = { ordem: Ordem; acao: AcaoMaquina; maquinas: MaquinaResumo[] };
type Motivo = { ordem: Ordem; acao: "pausar" | "cancelar" };
type Aviso = { tipo: "ok" | "erro"; texto: string };

const ATUALIZAR_MS = 15000;

export default function KanbanPage() {
  const { user } = useAuth();
  const podePlanejar = temAcao(user, "planejar_producao");
  const podeMovimentar = temAcao(user, "movimentar_producao");

  const [quadro, setQuadro] = useState<Kanban | null>(null);
  const [busca, setBusca] = useState("");
  const [aviso, setAviso] = useState<Aviso | null>(null);
  const [arrastando, setArrastando] = useState<Ordem | null>(null);
  const [pendente, setPendente] = useState<Pendente | null>(null);
  const [motivo, setMotivo] = useState<Motivo | null>(null);
  const [detalhe, setDetalhe] = useState<string | null>(null);
  const [nova, setNova] = useState(false);
  const ocupado = useRef(false);
  ocupado.current = Boolean(arrastando || pendente || motivo || detalhe || nova);

  const carregar = useCallback(() => {
    api<Kanban>("/kanban")
      .then(setQuadro)
      .catch((e: Error) => setAviso({ tipo: "erro", texto: e.message }));
  }, []);

  useEffect(() => {
    carregar();
    const t = setInterval(() => !ocupado.current && carregar(), ATUALIZAR_MS);
    return () => clearInterval(t);
  }, [carregar]);

  async function executar(ordem: Ordem, caminho: string, corpo: object | undefined, sucesso: string) {
    try {
      await api(`/ordens/${ordem.id}/${caminho}`, { method: "POST", body: corpo ? JSON.stringify(corpo) : undefined });
      setAviso({ tipo: "ok", texto: sucesso });
      carregar();
    } catch (e) {
      setAviso({ tipo: "erro", texto: e instanceof Error ? e.message : "Não foi possível concluir." });
    }
  }

  function colunaDaOrdem(ordem: Ordem): Coluna | undefined {
    const etapa = etapaAtual(ordem);
    return quadro?.colunas.find((c) => c.setor_id === etapa?.setor_id);
  }

  function comMaquina(ordem: Ordem, acao: AcaoMaquina) {
    const etapa = etapaAtual(ordem);
    if (!etapa) return;
    const maquinas = colunaDaOrdem(ordem)?.maquinas ?? [];
    const escolhida = etapa.maquina_id ?? (maquinas.length === 1 ? maquinas[0].id : null);
    if (escolhida) {
      rodar(ordem, acao, escolhida);
    } else if (maquinas.length === 0) {
      setAviso({ tipo: "erro", texto: `Nenhuma máquina ativa em ${etapa.setor_nome}.` });
    } else {
      setPendente({ ordem, acao, maquinas });
    }
  }

  function rodar(ordem: Ordem, acao: AcaoMaquina, maquinaId: string) {
    const etapa = etapaAtual(ordem);
    const proxima = ordem.etapas.find((e) => e.sequencia === (etapa?.sequencia ?? 0) + 1);
    if (acao === "iniciar") {
      executar(ordem, "iniciar", { maquina_id: maquinaId }, `OP ${ordem.numero}: ${etapa?.setor_nome} iniciado.`);
    } else {
      const texto = proxima
        ? `OP ${ordem.numero} seguiu para ${proxima.setor_nome}.`
        : `OP ${ordem.numero} concluída: produto final pronto.`;
      executar(ordem, "concluir-etapa", { maquina_id: maquinaId }, texto);
    }
  }

  function soltar(coluna: Coluna) {
    const ordem = arrastando;
    setArrastando(null);
    if (!ordem) return;
    const destino = destinoPermitido(ordem);
    const alvo = coluna.tipo === "concluidas" ? "concluidas" : coluna.setor_id;
    if (colunaDaOrdem(ordem)?.id === coluna.id || (ordem.status === "planejada" && coluna.tipo === "planejadas")) return;
    if (alvo !== destino) {
      const nome = destino === "concluidas" ? "Concluídas" : quadro?.colunas.find((c) => c.setor_id === destino)?.titulo;
      setAviso({
        tipo: "erro",
        texto: nome
          ? `A OP ${ordem.numero} segue o roteiro: o próximo passo é ${nome}.`
          : `A OP ${ordem.numero} não pode ser movida agora.`,
      });
      return;
    }
    if (ordem.status === "planejada") {
      executar(ordem, "liberar", undefined, `OP ${ordem.numero} liberada para ${coluna.titulo}.`);
    } else {
      comMaquina(ordem, "concluir");
    }
  }

  function podeArrastar(ordem: Ordem) {
    if (ordem.status === "planejada") return podePlanejar;
    return podeMovimentar && (ordem.status === "liberada" || ordem.status === "em_producao");
  }

  const termo = busca.trim().toLowerCase();
  const filtrar = (cards: Ordem[]) =>
    termo
      ? cards.filter(
          (o) =>
            `op ${o.numero}`.includes(termo) ||
            String(o.numero) === termo ||
            o.produto_codigo.toLowerCase().includes(termo) ||
            o.produto_descricao.toLowerCase().includes(termo),
        )
      : cards;

  const destinoArraste = arrastando ? destinoPermitido(arrastando) : null;

  return (
    <>
      <PageHeader
        title="Kanban da produção"
        subtitle="Cada ordem anda de processo em processo, na sequência do roteiro do produto. Arraste o cartão para a próxima etapa."
        action={
          podePlanejar ? (
            <button className="btn primary" onClick={() => setNova(true)}>
              Nova ordem
            </button>
          ) : null
        }
      />
      <div className="toolbar">
        <input placeholder="Filtrar por OP ou produto" value={busca} onChange={(e) => setBusca(e.target.value)} />
        <button className="btn" onClick={carregar}>
          Atualizar
        </button>
        {quadro ? <span className="hint" style={{ alignSelf: "center" }}>Atualizado às {dataHora(quadro.atualizado_em).slice(-5)}</span> : null}
      </div>
      {aviso ? (
        <div className={aviso.tipo === "erro" ? "error" : "aviso-ok"} onClick={() => setAviso(null)} role="status">
          {aviso.texto}
        </div>
      ) : null}

      {!quadro ? (
        <p className="center-msg">Carregando quadro…</p>
      ) : (
        <div className="board">
          {quadro.colunas.map((coluna, i) => {
            const cards = filtrar(coluna.cards);
            const rodando = coluna.cards.filter((o) => etapaAtual(o)?.status === "em_andamento" && o.status !== "pausada").length;
            const alvo = coluna.tipo === "concluidas" ? "concluidas" : coluna.setor_id;
            const valido = Boolean(arrastando) && alvo === destinoArraste;
            return (
              <section
                key={coluna.id}
                className={`coluna ${coluna.tipo} ${valido ? "alvo" : ""}`}
                onDragOver={(e: DragEvent) => {
                  if (arrastando) e.preventDefault();
                }}
                onDrop={(e: DragEvent) => {
                  e.preventDefault();
                  soltar(coluna);
                }}
              >
                <header>
                  <div>
                    {coluna.tipo === "setor" ? <span className="passo">{i}</span> : null}
                    <strong>{coluna.titulo}</strong>
                  </div>
                  <span className="contagem">{coluna.cards.length}</span>
                </header>
                {coluna.tipo === "setor" ? (
                  <p className="coluna-info">
                    {rodando} em andamento · {coluna.cards.length - rodando} na fila
                    {coluna.maquinas.length ? ` · ${coluna.maquinas.map((m) => m.codigo).join(", ")}` : " · sem máquina ativa"}
                  </p>
                ) : null}
                <div className="cards">
                  {cards.length === 0 ? <p className="vazio">—</p> : null}
                  {cards.map((o) => (
                    <CardOrdem
                      key={o.id}
                      ordem={o}
                      arrastavel={podeArrastar(o)}
                      podePlanejar={podePlanejar}
                      podeMovimentar={podeMovimentar}
                      onDragStart={() => setArrastando(o)}
                      onDragEnd={() => setArrastando(null)}
                      onLiberar={() => executar(o, "liberar", undefined, `OP ${o.numero} liberada para a fábrica.`)}
                      onIniciar={() => comMaquina(o, "iniciar")}
                      onConcluir={() => comMaquina(o, "concluir")}
                      onRetomar={() => executar(o, "retomar", undefined, `OP ${o.numero} retomada.`)}
                      onPausar={() => setMotivo({ ordem: o, acao: "pausar" })}
                      onCancelar={() => setMotivo({ ordem: o, acao: "cancelar" })}
                      onDetalhe={() => setDetalhe(o.id)}
                    />
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}

      {pendente ? (
        <EscolherMaquina
          pendente={pendente}
          onClose={() => setPendente(null)}
          onEscolher={(id) => {
            setPendente(null);
            rodar(pendente.ordem, pendente.acao, id);
          }}
        />
      ) : null}
      {motivo ? (
        <MotivoModal
          motivo={motivo}
          onClose={() => setMotivo(null)}
          onConfirmar={(texto) => {
            setMotivo(null);
            const verbo = motivo.acao === "pausar" ? "pausada" : "cancelada";
            executar(motivo.ordem, motivo.acao, { motivo: texto }, `OP ${motivo.ordem.numero} ${verbo}.`);
          }}
        />
      ) : null}
      {detalhe ? <DetalheOrdem ordemId={detalhe} onClose={() => setDetalhe(null)} /> : null}
      {nova ? (
        <NovaOrdem
          onClose={() => setNova(false)}
          onCriada={(o) => {
            setNova(false);
            setAviso({ tipo: "ok", texto: `OP ${o.numero} criada em Planejadas.` });
            carregar();
          }}
        />
      ) : null}
    </>
  );
}

function CardOrdem({
  ordem,
  arrastavel,
  podePlanejar,
  podeMovimentar,
  onDragStart,
  onDragEnd,
  onLiberar,
  onIniciar,
  onConcluir,
  onRetomar,
  onPausar,
  onCancelar,
  onDetalhe,
}: {
  ordem: Ordem;
  arrastavel: boolean;
  podePlanejar: boolean;
  podeMovimentar: boolean;
  onDragStart: () => void;
  onDragEnd: () => void;
  onLiberar: () => void;
  onIniciar: () => void;
  onConcluir: () => void;
  onRetomar: () => void;
  onPausar: () => void;
  onCancelar: () => void;
  onDetalhe: () => void;
}) {
  const etapa = etapaAtual(ordem);
  const proxima = ordem.etapas.find((e) => e.sequencia === (etapa?.sequencia ?? 0) + 1);
  const pausada = ordem.status === "pausada";
  const emCurso = ordem.status === "liberada" || ordem.status === "em_producao";
  const aberta = ordem.status !== "concluida" && ordem.status !== "cancelada";
  const chapa = comprimentoLabel(ordem.comprimento_mm);

  return (
    <article
      className={`card-op prioridade-${ordem.prioridade} ${pausada ? "pausada" : ""} ${ordem.atrasada ? "atrasada" : ""}`}
      draggable={arrastavel}
      onDragStart={(e) => {
        e.dataTransfer.effectAllowed = "move";
        onDragStart();
      }}
      onDragEnd={onDragEnd}
    >
      <div className="card-topo">
        <button type="button" className="op-numero" onClick={onDetalhe} title="Ver histórico">
          OP {ordem.numero}
        </button>
        {ordem.prioridade !== "normal" ? <span className={`chip ${ordem.prioridade}`}>{PRIORIDADE_LABEL[ordem.prioridade]}</span> : null}
      </div>
      <strong className="card-produto">{ordem.produto_codigo}</strong>
      <span className="card-desc">{ordem.produto_descricao}</span>
      <div className="card-dados">
        <span>
          {numero(ordem.quantidade)} {ordem.unidade}
        </span>
        {chapa ? <span>Chapa {chapa}</span> : null}
        {ordem.prazo ? <span className={ordem.atrasada ? "atraso" : ""}>Prazo {dataCurta(ordem.prazo)}</span> : null}
      </div>

      <div className="trilha" aria-label="Etapas do roteiro">
        {ordem.etapas.map((e) => (
          <span
            key={e.sequencia}
            className={`passo-trilha ${e.status}`}
            title={`${e.sequencia}. ${e.setor_nome}: ${e.operacao} (${e.status_label}${e.maquina_codigo ? ` · ${e.maquina_codigo}` : ""})`}
          >
            {e.setor_nome}
          </span>
        ))}
      </div>

      {ordem.status === "concluida" ? (
        <p className="card-estado ok">Produto final pronto · {ordem.concluida_em ? dataHora(ordem.concluida_em) : ""}</p>
      ) : etapa && ordem.status !== "planejada" ? (
        <p className={`card-estado ${pausada ? "pausa" : etapa.status}`}>
          {pausada
            ? `Pausada: ${ordem.motivo_pausa}`
            : etapa.status === "em_andamento"
              ? `Em andamento na ${etapa.maquina_codigo} · ${etapa.operacao}`
              : `Na fila · ${etapa.operacao}`}
        </p>
      ) : (
        <p className="card-estado">Aguardando liberação · 1º passo: {ordem.etapas[0]?.setor_nome}</p>
      )}

      <div className="card-acoes">
        {ordem.status === "planejada" && podePlanejar ? (
          <button className="btn small primary" onClick={onLiberar}>
            Liberar para {ordem.etapas[0]?.setor_nome}
          </button>
        ) : null}
        {emCurso && podeMovimentar && etapa?.status === "na_fila" ? (
          <button className="btn small" onClick={onIniciar}>
            Iniciar
          </button>
        ) : null}
        {emCurso && podeMovimentar ? (
          <button className="btn small primary" onClick={onConcluir}>
            {proxima ? `Concluir → ${proxima.setor_nome}` : "Finalizar OP"}
          </button>
        ) : null}
        {pausada && podeMovimentar ? (
          <button className="btn small primary" onClick={onRetomar}>
            Retomar
          </button>
        ) : null}
        <span className="card-links">
          {emCurso && podeMovimentar ? (
            <button type="button" onClick={onPausar}>
              Pausar
            </button>
          ) : null}
          {aberta && podePlanejar ? (
            <button type="button" onClick={onCancelar}>
              Cancelar
            </button>
          ) : null}
        </span>
      </div>
    </article>
  );
}

function EscolherMaquina({
  pendente,
  onClose,
  onEscolher,
}: {
  pendente: Pendente;
  onClose: () => void;
  onEscolher: (maquinaId: string) => void;
}) {
  const etapa = etapaAtual(pendente.ordem);
  return (
    <div className="modal-back" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>
          OP {pendente.ordem.numero} · {etapa?.setor_nome}
        </h2>
        <p className="hint">
          {pendente.acao === "iniciar" ? "Em qual máquina esta etapa vai rodar?" : "Em qual máquina esta etapa foi feita?"}{" "}
          {etapa?.operacao}
        </p>
        <div className="escolha-maquinas">
          {pendente.maquinas.map((m) => (
            <button key={m.id} className="btn" onClick={() => onEscolher(m.id)}>
              <strong>{m.codigo}</strong>
              <span>{m.nome}</span>
            </button>
          ))}
        </div>
        <div className="form-actions">
          <button className="btn" onClick={onClose}>
            Cancelar
          </button>
        </div>
      </div>
    </div>
  );
}

function MotivoModal({ motivo, onClose, onConfirmar }: { motivo: Motivo; onClose: () => void; onConfirmar: (t: string) => void }) {
  const [texto, setTexto] = useState("");
  const pausar = motivo.acao === "pausar";
  return (
    <div className="modal-back" onClick={onClose}>
      <form
        className="modal"
        onClick={(e) => e.stopPropagation()}
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          onConfirmar(texto);
        }}
      >
        <h2>
          {pausar ? "Pausar" : "Cancelar"} OP {motivo.ordem.numero}
        </h2>
        <label className="field">
          Motivo (fica no histórico)
          <input
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder={pausar ? "Ex.: falta de bobina de 2,00 mm" : "Ex.: pedido do cliente cancelado"}
            required
            minLength={3}
            autoFocus
          />
        </label>
        <div className="form-actions">
          <button type="button" className="btn" onClick={onClose}>
            Voltar
          </button>
          <button className="btn primary">{pausar ? "Pausar" : "Cancelar OP"}</button>
        </div>
      </form>
    </div>
  );
}

function DetalheOrdem({ ordemId, onClose }: { ordemId: string; onClose: () => void }) {
  const [ordem, setOrdem] = useState<OrdemDetalhe | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api<OrdemDetalhe>(`/ordens/${ordemId}`)
      .then(setOrdem)
      .catch((e: Error) => setErro(e.message));
  }, [ordemId]);

  return (
    <div className="modal-back" onClick={onClose}>
      <div className="modal wide" onClick={(e) => e.stopPropagation()}>
        {erro ? <p className="error">{erro}</p> : null}
        {!ordem ? (
          <p className="center-msg">Carregando…</p>
        ) : (
          <>
            <h2>
              OP {ordem.numero} · {ordem.produto_codigo} <span className="hint">({ordem.status_label})</span>
            </h2>
            <p className="hint">
              {ordem.produto_descricao} · {numero(ordem.quantidade)} {ordem.unidade}
              {ordem.prazo ? ` · prazo ${dataCurta(ordem.prazo)}` : ""}
              {ordem.observacao ? ` · ${ordem.observacao}` : ""}
            </p>
            <table className="table" style={{ marginTop: 12 }}>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Centro</th>
                  <th>Operação</th>
                  <th>Máquina</th>
                  <th>Início</th>
                  <th>Fim</th>
                  <th>Situação</th>
                </tr>
              </thead>
              <tbody>
                {ordem.etapas.map((e) => (
                  <tr key={e.sequencia}>
                    <td>{e.sequencia}</td>
                    <td>{e.setor_nome}</td>
                    <td>{e.operacao}</td>
                    <td className="mono">{e.maquina_codigo ?? "—"}</td>
                    <td>{e.iniciada_em ? dataHora(e.iniciada_em) : "—"}</td>
                    <td>{e.concluida_em ? dataHora(e.concluida_em) : "—"}</td>
                    <td>{e.status_label}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <h3 className="sub">Histórico</h3>
            <ul className="linha-tempo">
              {ordem.eventos.map((ev, i) => (
                <li key={i}>
                  <span className="hint">{dataHora(ev.em)}</span> {ev.descricao}
                  {ev.usuario_nome ? <span className="hint"> · {ev.usuario_nome}</span> : null}
                </li>
              ))}
            </ul>
          </>
        )}
        <div className="form-actions">
          <button className="btn" onClick={onClose}>
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
}

function NovaOrdem({ onClose, onCriada }: { onClose: () => void; onCriada: (o: Ordem) => void }) {
  const [produtos, setProdutos] = useState<Produto[]>([]);
  const [produtoId, setProdutoId] = useState("");
  const [quantidade, setQuantidade] = useState("");
  const [prazo, setPrazo] = useState("");
  const [prioridade, setPrioridade] = useState<Prioridade>("normal");
  const [observacao, setObservacao] = useState("");
  const [erro, setErro] = useState("");

  useEffect(() => {
    api<Produto[]>("/produtos?ativos=true")
      .then((lista) => {
        setProdutos(lista);
        setProdutoId((atual) => atual || lista[0]?.id || "");
      })
      .catch((e: Error) => setErro(e.message));
  }, []);

  const produto = produtos.find((p) => p.id === produtoId);

  async function salvar(e: FormEvent) {
    e.preventDefault();
    setErro("");
    try {
      const ordem = await api<Ordem>("/ordens", {
        method: "POST",
        body: JSON.stringify({
          produto_id: produtoId,
          quantidade: Number(quantidade),
          prazo: prazo || null,
          prioridade,
          observacao: observacao || null,
        }),
      });
      onCriada(ordem);
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Não foi possível criar a ordem.");
    }
  }

  return (
    <div className="modal-back" onClick={onClose}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={salvar}>
        <h2>Nova ordem de produção</h2>
        {erro ? <p className="error">{erro}</p> : null}
        <div className="form-grid">
          <label className="field full">
            Produto
            <select value={produtoId} onChange={(e) => setProdutoId(e.target.value)} required>
              {produtos.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.codigo} · {p.descricao}
                </option>
              ))}
            </select>
            {produto ? (
              <span className="rota" style={{ marginTop: 4 }}>
                {produto.roteiro.map((e) => (
                  <span key={e.sequencia}>{e.setor_nome}</span>
                ))}
              </span>
            ) : null}
          </label>
          <label className="field">
            Quantidade ({produto?.unidade ?? "PC"})
            <input type="number" min={1} value={quantidade} onChange={(e) => setQuantidade(e.target.value)} required />
          </label>
          <label className="field">
            Prazo
            <input type="date" value={prazo} onChange={(e) => setPrazo(e.target.value)} />
          </label>
          <label className="field">
            Prioridade
            <select value={prioridade} onChange={(e) => setPrioridade(e.target.value as Prioridade)}>
              {Object.entries(PRIORIDADE_LABEL).map(([valor, label]) => (
                <option key={valor} value={valor}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="field full">
            Observação
            <input value={observacao} onChange={(e) => setObservacao(e.target.value)} maxLength={500} placeholder="Ex.: pedido 4512 - Construtora Rio Verde" />
          </label>
        </div>
        <div className="form-actions">
          <button type="button" className="btn" onClick={onClose}>
            Cancelar
          </button>
          <button className="btn primary" disabled={!produtoId}>
            Criar ordem
          </button>
        </div>
      </form>
    </div>
  );
}
