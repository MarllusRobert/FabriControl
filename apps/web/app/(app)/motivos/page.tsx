"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { PageHeader } from "../../components/Shell";
import { api } from "../../lib/api";
import { temAcao, useAuth } from "../../lib/auth";
import { MotivoParada, MotivoRefugo, Opcao, OpcoesMotivos } from "../../lib/motivos";

type Aba = "parada" | "refugo";
type Motivo = MotivoParada | MotivoRefugo;

export default function MotivosPage() {
  const { user } = useAuth();
  const podeEditar = temAcao(user, "gerenciar_equipe");
  const [aba, setAba] = useState<Aba>("parada");
  const [opcoes, setOpcoes] = useState<OpcoesMotivos | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api<OpcoesMotivos>("/motivos/opcoes")
      .then(setOpcoes)
      .catch((e: Error) => setErro(e.message));
  }, []);

  return (
    <>
      <PageHeader
        title="Motivos"
        subtitle="Motivos de parada de máquina e de refugo de peças, usados no apontamento e no OEE."
      />
      {erro ? <p className="error">{erro}</p> : null}
      <div className="tabs">
        <button className={aba === "parada" ? "active" : ""} onClick={() => setAba("parada")}>
          Paradas
        </button>
        <button className={aba === "refugo" ? "active" : ""} onClick={() => setAba("refugo")}>
          Refugo
        </button>
      </div>
      {opcoes ? (
        <ListaMotivos
          key={aba}
          aba={aba}
          grupos={aba === "parada" ? opcoes.tipos_parada : opcoes.categorias_refugo}
          podeEditar={podeEditar}
        />
      ) : null}
    </>
  );
}

function grupoDe(aba: Aba, m: Motivo) {
  return aba === "parada" ? (m as MotivoParada).tipo : (m as MotivoRefugo).categoria;
}

function rotuloDe(aba: Aba, m: Motivo) {
  return aba === "parada" ? (m as MotivoParada).tipo_label : (m as MotivoRefugo).categoria_label;
}

function ListaMotivos({ aba, grupos, podeEditar }: { aba: Aba; grupos: Opcao[]; podeEditar: boolean }) {
  const [motivos, setMotivos] = useState<Motivo[] | null>(null);
  const [grupo, setGrupo] = useState("");
  const [editando, setEditando] = useState<Motivo | "novo" | null>(null);
  const [erro, setErro] = useState("");
  const campo = aba === "parada" ? "tipo" : "categoria";

  const carregar = useCallback(() => {
    const params = new URLSearchParams();
    if (grupo) params.set(campo, grupo);
    api<Motivo[]>(`/motivos/${aba}?${params}`)
      .then(setMotivos)
      .catch((e: Error) => setErro(e.message));
  }, [aba, campo, grupo]);

  useEffect(carregar, [carregar]);

  return (
    <>
      <div className="toolbar">
        <select value={grupo} onChange={(e) => setGrupo(e.target.value)} aria-label={aba === "parada" ? "Tipo" : "Categoria"}>
          <option value="">{aba === "parada" ? "Todos os tipos" : "Todas as categorias"}</option>
          {grupos.map((g) => (
            <option key={g.valor} value={g.valor}>
              {g.label}
            </option>
          ))}
        </select>
        <div style={{ flex: 1 }} />
        {podeEditar ? (
          <button className="btn primary" onClick={() => setEditando("novo")}>
            {aba === "parada" ? "Novo motivo de parada" : "Novo motivo de refugo"}
          </button>
        ) : null}
      </div>
      {aba === "parada" ? (
        <p className="hint">
          Parada planejada (setup, preventiva) sai do tempo disponível; a não planejada (quebra, falta de material) derruba a
          disponibilidade no OEE.
        </p>
      ) : null}
      {erro ? <p className="error">{erro}</p> : null}

      <div className="table-wrap">
        {motivos === null ? (
          <p className="empty">Carregando…</p>
        ) : motivos.length === 0 ? (
          <p className="empty">Nenhum motivo cadastrado.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Código</th>
                <th>Descrição</th>
                <th>{aba === "parada" ? "Tipo" : "Categoria"}</th>
                <th>Situação</th>
                {podeEditar ? <th /> : null}
              </tr>
            </thead>
            <tbody>
              {motivos.map((m) => (
                <tr key={m.id}>
                  <td className="mono">{m.codigo}</td>
                  <td>{m.descricao}</td>
                  <td>
                    {aba === "parada" ? (
                      <span className={`badge ${grupoDe(aba, m)}`}>{rotuloDe(aba, m)}</span>
                    ) : (
                      rotuloDe(aba, m)
                    )}
                  </td>
                  <td>
                    <span className={`badge ${m.ativo ? "ativa" : "inativa"}`}>{m.ativo ? "Ativo" : "Inativo"}</span>
                  </td>
                  {podeEditar ? (
                    <td className="num">
                      <button className="btn small" onClick={() => setEditando(m)}>
                        Editar
                      </button>
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {editando ? (
        <MotivoForm
          aba={aba}
          motivo={editando === "novo" ? null : editando}
          grupos={grupos}
          onClose={() => setEditando(null)}
          onSalvo={() => {
            setEditando(null);
            carregar();
          }}
        />
      ) : null}
    </>
  );
}

function MotivoForm({
  aba,
  motivo,
  grupos,
  onClose,
  onSalvo,
}: {
  aba: Aba;
  motivo: Motivo | null;
  grupos: Opcao[];
  onClose: () => void;
  onSalvo: () => void;
}) {
  const campo = aba === "parada" ? "tipo" : "categoria";
  const [codigo, setCodigo] = useState(motivo?.codigo ?? "");
  const [descricao, setDescricao] = useState(motivo?.descricao ?? "");
  const [grupo, setGrupo] = useState(motivo ? grupoDe(aba, motivo) : grupos[0]?.valor ?? "");
  const [ativo, setAtivo] = useState(motivo?.ativo ?? true);
  const [erro, setErro] = useState("");

  async function salvar(e: FormEvent) {
    e.preventDefault();
    setErro("");
    try {
      await api(motivo ? `/motivos/${aba}/${motivo.id}` : `/motivos/${aba}`, {
        method: motivo ? "PUT" : "POST",
        body: JSON.stringify({ codigo, descricao, [campo]: grupo, ativo }),
      });
      onSalvo();
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Não foi possível salvar.");
    }
  }

  const titulo = aba === "parada" ? "motivo de parada" : "motivo de refugo";

  return (
    <div className="modal-back" onClick={onClose}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={salvar}>
        <h2>{motivo ? `Editar ${motivo.codigo}` : `Novo ${titulo}`}</h2>
        {erro ? <p className="error">{erro}</p> : null}
        <div className="form-grid">
          <label className="field">
            Código
            <input value={codigo} onChange={(e) => setCodigo(e.target.value)} placeholder="SET" required maxLength={10} />
          </label>
          <label className="field">
            {aba === "parada" ? "Tipo" : "Categoria"}
            <select value={grupo} onChange={(e) => setGrupo(e.target.value)} required>
              {grupos.map((g) => (
                <option key={g.valor} value={g.valor}>
                  {g.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field full">
            Descrição
            <input value={descricao} onChange={(e) => setDescricao(e.target.value)} required minLength={2} maxLength={120} />
          </label>
          <label className="field full" style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
            <input type="checkbox" checked={ativo} onChange={(e) => setAtivo(e.target.checked)} />
            Ativo (só motivos ativos aparecem no apontamento)
          </label>
        </div>
        <div className="form-actions">
          <button type="button" className="btn" onClick={onClose}>
            Cancelar
          </button>
          <button className="btn primary">Salvar</button>
        </div>
      </form>
    </div>
  );
}
