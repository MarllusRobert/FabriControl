"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../../lib/api";
import { temAcao, useAuth } from "../../lib/auth";
import { Maquina, numero } from "../../lib/cadastros";
import { EtapaFila, OperadorSessao, PainelMaquina, hora, horasLabel } from "../../lib/operacao";

const CHAVE_MAQUINA = "fc.operacao.maquina";
const CHAVE_OPERADOR = "fc.operacao.operador";
const ATUALIZA_MS = 15000;

export default function OperacaoPage() {
  const [maquinaId, setMaquinaId] = useState<string | null>(null);
  const [operador, setOperador] = useState<OperadorSessao | null>(null);
  const [pronto, setPronto] = useState(false);

  // O tablet fica na máquina: lembra a máquina e o operador entre recarregamentos.
  useEffect(() => {
    setMaquinaId(localStorage.getItem(CHAVE_MAQUINA));
    const salvo = localStorage.getItem(CHAVE_OPERADOR);
    setOperador(salvo ? (JSON.parse(salvo) as OperadorSessao) : null);
    setPronto(true);
  }, []);

  function escolherMaquina(id: string | null) {
    if (id) localStorage.setItem(CHAVE_MAQUINA, id);
    else localStorage.removeItem(CHAVE_MAQUINA);
    setMaquinaId(id);
  }

  function entrar(op: OperadorSessao | null) {
    if (op) localStorage.setItem(CHAVE_OPERADOR, JSON.stringify(op));
    else localStorage.removeItem(CHAVE_OPERADOR);
    setOperador(op);
  }

  if (!pronto) return null;
  if (!maquinaId) return <EscolherMaquina onEscolher={escolherMaquina} />;
  if (!operador) return <Identificar onEntrar={entrar} onTrocarMaquina={() => escolherMaquina(null)} />;
  return (
    <PainelOperacao
      maquinaId={maquinaId}
      operador={operador}
      onTrocarMaquina={() => escolherMaquina(null)}
      onSair={() => entrar(null)}
    />
  );
}

function EscolherMaquina({ onEscolher }: { onEscolher: (id: string) => void }) {
  const [maquinas, setMaquinas] = useState<Maquina[] | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api<Maquina[]>("/maquinas?status=ativa")
      .then(setMaquinas)
      .catch((e: Error) => setErro(e.message));
  }, []);

  const porSetor = useMemo(() => {
    const grupos = new Map<string, Maquina[]>();
    for (const m of maquinas ?? []) grupos.set(m.setor_nome, [...(grupos.get(m.setor_nome) ?? []), m]);
    return [...grupos.entries()];
  }, [maquinas]);

  return (
    <div className="op-tela">
      <h1 className="op-titulo">Qual é esta máquina?</h1>
      <p className="op-sub">Escolha uma vez; o tablet lembra a máquina.</p>
      {erro ? <p className="error">{erro}</p> : null}
      {maquinas === null ? <p className="empty">Carregando…</p> : null}
      {porSetor.map(([setor, lista]) => (
        <section key={setor} className="op-grupo">
          <h2>{setor}</h2>
          <div className="op-grade">
            {lista.map((m) => (
              <button key={m.id} className="op-maquina" onClick={() => onEscolher(m.id)}>
                <strong>{m.codigo}</strong>
                <span>{m.nome}</span>
              </button>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function Identificar({ onEntrar, onTrocarMaquina }: { onEntrar: (op: OperadorSessao) => void; onTrocarMaquina: () => void }) {
  const [matricula, setMatricula] = useState("");
  const [erro, setErro] = useState("");

  async function entrar(e: FormEvent) {
    e.preventDefault();
    setErro("");
    try {
      const op = await api<OperadorSessao>(`/operacao/operador?matricula=${encodeURIComponent(matricula)}`);
      onEntrar({ id: op.id, nome: op.nome, matricula: op.matricula });
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Matrícula não encontrada.");
    }
  }

  return (
    <div className="op-tela op-centro">
      <form className="op-login" onSubmit={entrar}>
        <h1 className="op-titulo">Quem está operando?</h1>
        <input
          className="op-matricula"
          value={matricula}
          onChange={(e) => setMatricula(e.target.value)}
          placeholder="Matrícula"
          inputMode="numeric"
          autoFocus
          required
          maxLength={20}
        />
        {erro ? <p className="error">{erro}</p> : null}
        <button className="op-botao iniciar">Entrar</button>
        <button type="button" className="btn" onClick={onTrocarMaquina}>
          Trocar máquina
        </button>
      </form>
    </div>
  );
}

function PainelOperacao({
  maquinaId,
  operador,
  onTrocarMaquina,
  onSair,
}: {
  maquinaId: string;
  operador: OperadorSessao;
  onTrocarMaquina: () => void;
  onSair: () => void;
}) {
  const { user } = useAuth();
  const podeMovimentar = temAcao(user, "movimentar_producao");
  const [painel, setPainel] = useState<PainelMaquina | null>(null);
  const [erro, setErro] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [pausando, setPausando] = useState(false);
  const [, setRelogio] = useState(0);

  const carregar = useCallback(() => {
    api<PainelMaquina>(`/operacao/maquinas/${maquinaId}`)
      .then((p) => {
        setPainel(p);
        setErro("");
      })
      .catch((e: Error) => setErro(e.message));
  }, [maquinaId]);

  useEffect(() => {
    carregar();
    const t = setInterval(carregar, ATUALIZA_MS);
    const r = setInterval(() => setRelogio((n) => n + 1), 30000);
    return () => {
      clearInterval(t);
      clearInterval(r);
    };
  }, [carregar]);

  async function acao(caminho: string, corpo: object) {
    setOcupado(true);
    setErro("");
    try {
      const resp = await api<PainelMaquina | object>(caminho, { method: "POST", body: JSON.stringify(corpo) });
      if ("maquina" in resp) setPainel(resp as PainelMaquina);
      else carregar();
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Não foi possível concluir.");
    } finally {
      setOcupado(false);
    }
  }

  const base = `/operacao/maquinas/${maquinaId}`;
  const atual = painel?.atual ?? null;
  const [proxima, ...resto] = painel?.fila ?? [];

  return (
    <div className="op-tela">
      <header className="op-topo">
        <div>
          <strong>{painel ? painel.maquina.codigo : "…"}</strong>
          <span>{painel ? `${painel.maquina.nome} · ${painel.maquina.setor_nome}` : ""}</span>
        </div>
        <div className="op-quem">
          <strong>{operador.nome}</strong>
          <span>Matrícula {operador.matricula}</span>
        </div>
        <div className="op-topo-acoes">
          <button className="btn" onClick={onSair}>
            Trocar operador
          </button>
          <button className="btn" onClick={onTrocarMaquina}>
            Trocar máquina
          </button>
        </div>
      </header>

      {erro ? <p className="error op-erro">{erro}</p> : null}
      {painel === null ? <p className="empty">Carregando…</p> : null}

      {atual ? (
        <section className={`op-card ${atual.ordem_status === "pausada" ? "pausada" : "rodando"}`}>
          <div className="op-estado">{atual.ordem_status === "pausada" ? "Pausada" : "Em produção"}</div>
          <Resumo etapa={atual} />
          {atual.iniciada_em ? (
            <p className="op-tempo">
              Começou às {hora(atual.iniciada_em)} · há {horasLabel((Date.now() - Date.parse(atual.iniciada_em)) / 60000)}
              {atual.operador_nome ? ` · ${atual.operador_nome}` : ""}
            </p>
          ) : null}
          {atual.ordem_status === "pausada" ? <p className="op-pausa">Motivo: {atual.motivo_pausa}</p> : null}
          {podeMovimentar ? (
            <div className="op-botoes">
              {atual.ordem_status === "pausada" ? (
                <button className="op-botao iniciar" disabled={ocupado} onClick={() => acao(`/ordens/${atual.ordem_id}/retomar`, {})}>
                  Retomar
                </button>
              ) : (
                <>
                  <button className="op-botao pausar" disabled={ocupado} onClick={() => setPausando(true)}>
                    Pausar
                  </button>
                  <button
                    className="op-botao finalizar"
                    disabled={ocupado}
                    onClick={() => {
                      if (confirm(`Finalizar a etapa da OP ${atual.ordem_numero}?`)) acao(`${base}/finalizar`, { operador_id: operador.id });
                    }}
                  >
                    Finalizar
                  </button>
                </>
              )}
            </div>
          ) : null}
        </section>
      ) : proxima ? (
        <section className="op-card proxima">
          <div className="op-estado">Próxima da fila</div>
          <Resumo etapa={proxima} />
          <p className="op-tempo">Carga prevista: {horasLabel(proxima.carga_min)}</p>
          {podeMovimentar ? (
            <div className="op-botoes">
              <button
                className="op-botao iniciar"
                disabled={ocupado}
                onClick={() => acao(`${base}/iniciar`, { operador_id: operador.id, ordem_id: proxima.ordem_id })}
              >
                Iniciar
              </button>
            </div>
          ) : null}
        </section>
      ) : painel ? (
        <section className="op-card vazia">
          <div className="op-estado">Sem ordens na fila</div>
          <p>Nenhuma ordem liberada para {painel.maquina.setor_nome} agora. A tela atualiza sozinha.</p>
        </section>
      ) : null}

      {(atual ? painel?.fila ?? [] : resto).length > 0 ? (
        <section className="op-fila">
          <h2>Depois vêm</h2>
          <ol>
            {(atual ? painel?.fila ?? [] : resto).map((f) => (
              <li key={f.ordem_id}>
                <span className="mono">OP {f.ordem_numero}</span>
                <span>
                  {f.produto_codigo} · {numero(f.quantidade)} {f.unidade}
                </span>
                <span className={`chip ${f.prioridade}`}>{f.prioridade}</span>
                <span className="hint">{horasLabel(f.carga_min)}</span>
              </li>
            ))}
          </ol>
        </section>
      ) : null}

      {pausando && atual ? (
        <PausarForm
          onClose={() => setPausando(false)}
          onPausar={(motivo) => {
            setPausando(false);
            acao(`/ordens/${atual.ordem_id}/pausar`, { motivo });
          }}
        />
      ) : null}
    </div>
  );
}

function Resumo({ etapa }: { etapa: EtapaFila }) {
  return (
    <div className="op-resumo">
      <div className="op-op">
        OP {etapa.ordem_numero}
        {etapa.prioridade !== "normal" ? <span className={`chip ${etapa.prioridade}`}>{etapa.prioridade}</span> : null}
        {etapa.atrasada ? <span className="chip urgente">atrasada</span> : null}
      </div>
      <div className="op-produto">
        {etapa.produto_codigo} · {numero(etapa.quantidade)} {etapa.unidade}
      </div>
      <div className="op-desc">{etapa.produto_descricao}</div>
      <div className="op-etapa">
        Etapa {etapa.sequencia} de {etapa.total_etapas}: {etapa.operacao}
        {etapa.proximo_setor ? <span className="hint"> · depois vai para {etapa.proximo_setor}</span> : null}
      </div>
    </div>
  );
}

function PausarForm({ onClose, onPausar }: { onClose: () => void; onPausar: (motivo: string) => void }) {
  const [motivo, setMotivo] = useState("");

  return (
    <div className="modal-back" onClick={onClose}>
      <form
        className="modal"
        onClick={(e) => e.stopPropagation()}
        onSubmit={(e) => {
          e.preventDefault();
          onPausar(motivo);
        }}
      >
        <h2>Por que vai pausar?</h2>
        <label className="field full">
          Motivo
          <textarea value={motivo} onChange={(e) => setMotivo(e.target.value)} rows={3} required minLength={3} maxLength={300} autoFocus />
        </label>
        <div className="form-actions">
          <button type="button" className="btn" onClick={onClose}>
            Cancelar
          </button>
          <button className="btn primary">Pausar</button>
        </div>
      </form>
    </div>
  );
}
