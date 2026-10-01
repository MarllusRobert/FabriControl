"use client";

import { DragEvent, useCallback, useEffect, useRef, useState } from "react";
import { PageHeader } from "../../components/Shell";
import { api } from "../../lib/api";
import { temAcao, useAuth } from "../../lib/auth";
import { numero } from "../../lib/cadastros";
import { EtapaFila, Fila, FilaSetor, horasLabel } from "../../lib/operacao";
import { PRIORIDADE_LABEL, dataCurta, dataHora } from "../../lib/producao";

const ATUALIZAR_MS = 30000;
const SEM_MAQUINA = "a_distribuir";

type Colunas = Record<string, EtapaFila[]>;
type Arraste = { ordemId: string; de: string };
type Alvo = { coluna: string; antesDe: string | null };
type Aviso = { tipo: "ok" | "erro"; texto: string };

function colunasDo(setor: FilaSetor): Colunas {
  const colunas: Colunas = { [SEM_MAQUINA]: setor.a_distribuir };
  for (const m of setor.maquinas) colunas[m.maquina.id] = m.fila;
  return colunas;
}

function carga(itens: EtapaFila[]) {
  return itens.reduce((total, e) => total + e.carga_min, 0);
}

export default function FilaPage() {
  const { user } = useAuth();
  const podePlanejar = temAcao(user, "planejar_producao");

  const [fila, setFila] = useState<Fila | null>(null);
  const [setorId, setSetorId] = useState("");
  const [colunas, setColunas] = useState<Colunas>({});
  const [arraste, setArraste] = useState<Arraste | null>(null);
  const [alvo, setAlvo] = useState<Alvo | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [aviso, setAviso] = useState<Aviso | null>(null);
  const ocupado = useRef(false);
  ocupado.current = Boolean(arraste || salvando);

  const aplicar = useCallback((dados: Fila) => {
    setFila(dados);
    setSetorId((atual) => (dados.setores.some((s) => s.setor_id === atual) ? atual : dados.setores[0]?.setor_id ?? ""));
  }, []);

  const carregar = useCallback(() => {
    api<Fila>("/fila")
      .then(aplicar)
      .catch((e: Error) => setAviso({ tipo: "erro", texto: e.message }));
  }, [aplicar]);

  useEffect(() => {
    carregar();
    const t = setInterval(() => !ocupado.current && carregar(), ATUALIZAR_MS);
    return () => clearInterval(t);
  }, [carregar]);

  const setor = fila?.setores.find((s) => s.setor_id === setorId);

  useEffect(() => {
    if (setor) setColunas(colunasDo(setor));
  }, [setor]);

  async function salvar(novas: Colunas) {
    if (!setor) return;
    setColunas(novas);
    setSalvando(true);
    try {
      const dados = await api<Fila>(`/fila/setores/${setor.setor_id}`, {
        method: "PUT",
        body: JSON.stringify({
          maquinas: setor.maquinas.map((m) => ({ maquina_id: m.maquina.id, ordens: novas[m.maquina.id].map((e) => e.ordem_id) })),
          a_distribuir: novas[SEM_MAQUINA].map((e) => e.ordem_id),
        }),
      });
      aplicar(dados);
      setAviso({ tipo: "ok", texto: `Sequência de ${setor.setor_nome} gravada. Os operadores já veem a nova ordem.` });
    } catch (e) {
      setAviso({ tipo: "erro", texto: e instanceof Error ? e.message : "Não foi possível gravar a sequência." });
      carregar();
    } finally {
      setSalvando(false);
    }
  }

  function soltar(coluna: string, antesDe: string | null) {
    const origem = arraste;
    setArraste(null);
    setAlvo(null);
    if (!origem || origem.ordemId === antesDe) return;
    const item = colunas[origem.de].find((e) => e.ordem_id === origem.ordemId);
    if (!item) return;
    const novas: Colunas = { ...colunas, [origem.de]: colunas[origem.de].filter((e) => e.ordem_id !== origem.ordemId) };
    const destino = [...novas[coluna]];
    const pos = antesDe ? destino.findIndex((e) => e.ordem_id === antesDe) : -1;
    destino.splice(pos < 0 ? destino.length : pos, 0, item);
    novas[coluna] = destino;
    const igual = novas[coluna].map((e) => e.ordem_id).join() === colunas[coluna].map((e) => e.ordem_id).join();
    if (coluna === origem.de && igual) return;
    salvar(novas);
  }

  function propsColuna(coluna: string) {
    return {
      onDragOver: (e: DragEvent) => {
        if (!arraste) return;
        e.preventDefault();
        if (alvo?.coluna !== coluna) setAlvo({ coluna, antesDe: null });
      },
      onDrop: (e: DragEvent) => {
        e.preventDefault();
        soltar(coluna, alvo?.coluna === coluna ? alvo.antesDe : null);
      },
    };
  }

  function cards(coluna: string) {
    const itens = colunas[coluna] ?? [];
    if (itens.length === 0) return <p className="vazio">Fila vazia</p>;
    return itens.map((e, i) => (
      <CardFila
        key={e.ordem_id}
        etapa={e}
        posicao={i + 1}
        arrastavel={podePlanejar && !salvando}
        indicador={alvo?.coluna === coluna && alvo.antesDe === e.ordem_id && arraste?.ordemId !== e.ordem_id}
        onDragStart={() => setArraste({ ordemId: e.ordem_id, de: coluna })}
        onDragEnd={() => {
          setArraste(null);
          setAlvo(null);
        }}
        onDragOver={(ev: DragEvent) => {
          if (!arraste) return;
          ev.preventDefault();
          ev.stopPropagation();
          if (alvo?.coluna !== coluna || alvo.antesDe !== e.ordem_id) setAlvo({ coluna, antesDe: e.ordem_id });
        }}
      />
    ));
  }

  const multiplas = (setor?.maquinas.length ?? 0) > 1;

  return (
    <>
      <PageHeader
        title="Fila por máquina"
        subtitle={
          podePlanejar
            ? "Arraste as OPs para definir a sequência de cada máquina. A tela do operador segue esta ordem."
            : "Sequência de produção de cada máquina, definida pelo PCP."
        }
      />
      <div className="toolbar">
        <button className="btn" onClick={carregar} disabled={salvando}>
          Atualizar
        </button>
        {fila ? <span className="hint" style={{ alignSelf: "center" }}>Atualizado às {dataHora(fila.atualizado_em).slice(-5)}</span> : null}
        {salvando ? <span className="hint" style={{ alignSelf: "center" }}>Gravando…</span> : null}
      </div>
      {aviso ? (
        <div className={aviso.tipo === "erro" ? "error" : "aviso-ok"} onClick={() => setAviso(null)} role="status">
          {aviso.texto}
        </div>
      ) : null}

      {!fila ? (
        <p className="center-msg">Carregando fila…</p>
      ) : fila.setores.length === 0 ? (
        <p className="center-msg">Nenhum centro de trabalho com máquina ativa.</p>
      ) : (
        <>
          <div className="tabs fila-tabs">
            {fila.setores.map((s) => {
              const total = s.maquinas.reduce((t, m) => t + m.carga_min, 0) + s.carga_a_distribuir_min;
              return (
                <button key={s.setor_id} className={s.setor_id === setorId ? "active" : ""} onClick={() => setSetorId(s.setor_id)}>
                  {s.setor_nome} <span className="fila-tab-carga">{horasLabel(total)}</span>
                </button>
              );
            })}
          </div>

          {setor ? (
            <div className="board">
              {multiplas ? (
                <section className={`coluna fila-coluna ${arraste && alvo?.coluna === SEM_MAQUINA ? "alvo" : ""}`} {...propsColuna(SEM_MAQUINA)}>
                  <header>
                    <strong>A distribuir</strong>
                    <span className="contagem">{colunas[SEM_MAQUINA]?.length ?? 0}</span>
                  </header>
                  <p className="coluna-info">Qualquer máquina do centro pode pegar · {horasLabel(carga(colunas[SEM_MAQUINA] ?? []))}</p>
                  <div className="cards">{cards(SEM_MAQUINA)}</div>
                </section>
              ) : null}
              {setor.maquinas.map((m) => {
                const id = m.maquina.id;
                const total = (m.atual?.carga_min ?? 0) + carga(colunas[id] ?? []);
                return (
                  <section key={id} className={`coluna fila-coluna ${arraste && alvo?.coluna === id ? "alvo" : ""}`} {...propsColuna(id)}>
                    <header>
                      <div>
                        <strong className="card-produto">{m.maquina.codigo}</strong> <span className="hint">{m.maquina.nome}</span>
                      </div>
                      <span className="contagem">{colunas[id]?.length ?? 0}</span>
                    </header>
                    <p className="fila-carga">
                      Carga <strong>{horasLabel(total)}</strong>
                      {m.parada ? <span className="chip urgente">Parada</span> : null}
                    </p>
                    {m.atual ? (
                      <div className="fila-rodando">
                        <span>Rodando agora</span>
                        <strong>
                          OP {m.atual.ordem_numero} · {m.atual.produto_codigo}
                        </strong>
                        <span className="hint">
                          Saldo {numero(m.atual.saldo)} de {numero(m.atual.entrada)} · {horasLabel(m.atual.carga_min)}
                          {m.atual.operador_nome ? ` · ${m.atual.operador_nome}` : ""}
                        </span>
                      </div>
                    ) : null}
                    <div className="cards">{cards(id)}</div>
                  </section>
                );
              })}
            </div>
          ) : null}
        </>
      )}
    </>
  );
}

function CardFila({
  etapa,
  posicao,
  arrastavel,
  indicador,
  onDragStart,
  onDragEnd,
  onDragOver,
}: {
  etapa: EtapaFila;
  posicao: number;
  arrastavel: boolean;
  indicador: boolean;
  onDragStart: () => void;
  onDragEnd: () => void;
  onDragOver: (e: DragEvent) => void;
}) {
  return (
    <article
      className={`card-op prioridade-${etapa.prioridade} ${indicador ? "fila-antes" : ""}`}
      draggable={arrastavel}
      onDragStart={(e) => {
        e.dataTransfer.effectAllowed = "move";
        onDragStart();
      }}
      onDragEnd={onDragEnd}
      onDragOver={onDragOver}
    >
      <div className="card-topo">
        <strong>
          <span className="fila-pos">{posicao}º</span> OP {etapa.ordem_numero}
        </strong>
        {etapa.prioridade !== "normal" ? (
          <span className={`chip ${etapa.prioridade}`}>{PRIORIDADE_LABEL[etapa.prioridade as keyof typeof PRIORIDADE_LABEL]}</span>
        ) : null}
      </div>
      <strong className="card-produto">{etapa.produto_codigo}</strong>
      <span className="card-desc">{etapa.operacao}</span>
      <div className="card-dados">
        <span>
          {numero(etapa.saldo)} {etapa.unidade}
        </span>
        <span>{horasLabel(etapa.carga_min)}</span>
        {etapa.prazo ? <span className={etapa.atrasada ? "atraso" : ""}>Prazo {dataCurta(etapa.prazo)}</span> : null}
      </div>
    </article>
  );
}
