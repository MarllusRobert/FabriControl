"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { PageHeader } from "../../components/Shell";
import { api } from "../../lib/api";
import { temAcao, useAuth } from "../../lib/auth";
import { Produto, Setor, comprimentoLabel, decimalInput } from "../../lib/cadastros";

export default function ProdutosPage() {
  const { user } = useAuth();
  const podeEditar = temAcao(user, "editar_cadastros");
  const [produtos, setProdutos] = useState<Produto[] | null>(null);
  const [setores, setSetores] = useState<Setor[]>([]);
  const [busca, setBusca] = useState("");
  const [editando, setEditando] = useState<Produto | "novo" | null>(null);
  const [erro, setErro] = useState("");

  const carregar = useCallback(() => {
    const params = busca.trim() ? `?busca=${encodeURIComponent(busca.trim())}` : "";
    api<Produto[]>(`/produtos${params}`)
      .then(setProdutos)
      .catch((e: Error) => setErro(e.message));
  }, [busca]);

  useEffect(() => {
    const t = setTimeout(carregar, 250);
    return () => clearTimeout(t);
  }, [carregar]);

  useEffect(() => {
    api<Setor[]>("/setores")
      .then(setSetores)
      .catch((e: Error) => setErro(e.message));
  }, []);

  return (
    <>
      <PageHeader title="Produtos" subtitle="O que a fábrica produz e por quais etapas cada produto passa." />
      {erro ? <p className="error">{erro}</p> : null}
      <div className="toolbar">
        <input placeholder="Buscar por código ou descrição" value={busca} onChange={(e) => setBusca(e.target.value)} />
        {podeEditar ? (
          <button className="btn primary" onClick={() => setEditando("novo")} disabled={setores.length === 0}>
            Novo produto
          </button>
        ) : null}
      </div>

      <div className="table-wrap">
        {produtos === null ? (
          <p className="empty">Carregando…</p>
        ) : produtos.length === 0 ? (
          <p className="empty">Nenhum produto cadastrado.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Código</th>
                <th>Produto</th>
                <th>Chapa</th>
                <th>Roteiro de fabricação</th>
                {podeEditar ? <th /> : null}
              </tr>
            </thead>
            <tbody>
              {produtos.map((p) => (
                <tr key={p.id}>
                  <td className="mono">{p.codigo}</td>
                  <td>
                    {p.descricao}
                    {!p.ativo ? <span className="badge inativa" style={{ marginLeft: 8 }}>Inativo</span> : null}
                  </td>
                  <td>{comprimentoLabel(p.comprimento_mm) ?? "—"}</td>
                  <td>
                    <div className="rota">
                      {p.roteiro.map((e) => (
                        <span key={e.sequencia} title={e.operacao}>
                          {e.sequencia}. {e.setor_nome}
                        </span>
                      ))}
                    </div>
                  </td>
                  {podeEditar ? (
                    <td className="num">
                      <button className="btn small" onClick={() => setEditando(p)}>
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
        <ProdutoForm
          produto={editando === "novo" ? null : editando}
          setores={setores.filter((s) => s.ativo)}
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

type LinhaRoteiro = { setor_id: string; operacao: string; tempo: string };

function ProdutoForm({
  produto,
  setores,
  onClose,
  onSalvo,
}: {
  produto: Produto | null;
  setores: Setor[];
  onClose: () => void;
  onSalvo: () => void;
}) {
  const [codigo, setCodigo] = useState(produto?.codigo ?? "");
  const [descricao, setDescricao] = useState(produto?.descricao ?? "");
  const [unidade, setUnidade] = useState(produto?.unidade ?? "PC");
  const [comprimento, setComprimento] = useState(produto?.comprimento_mm ? String(produto.comprimento_mm) : "6000");
  const [ativo, setAtivo] = useState(produto?.ativo ?? true);
  const [roteiro, setRoteiro] = useState<LinhaRoteiro[]>(
    produto
      ? produto.roteiro.map((e) => ({
          setor_id: e.setor_id,
          operacao: e.operacao,
          tempo: e.tempo_padrao_seg ? String(e.tempo_padrao_seg).replace(".", ",") : "",
        }))
      : [{ setor_id: setores[0]?.id ?? "", operacao: "", tempo: "" }],
  );
  const [erro, setErro] = useState("");

  function mudar(i: number, campo: keyof LinhaRoteiro, valor: string) {
    setRoteiro(roteiro.map((l, j) => (j === i ? { ...l, [campo]: valor } : l)));
  }

  function mover(i: number, delta: number) {
    const j = i + delta;
    if (j < 0 || j >= roteiro.length) return;
    const novo = [...roteiro];
    [novo[i], novo[j]] = [novo[j], novo[i]];
    setRoteiro(novo);
  }

  function adicionar() {
    const ultimo = setores.findIndex((s) => s.id === roteiro[roteiro.length - 1]?.setor_id);
    const proximo = setores[ultimo + 1] ?? setores[0];
    setRoteiro([...roteiro, { setor_id: proximo?.id ?? "", operacao: "", tempo: "" }]);
  }

  async function salvar(e: FormEvent) {
    e.preventDefault();
    setErro("");
    const corpo = {
      codigo,
      descricao,
      unidade,
      comprimento_mm: comprimento ? Number(comprimento) : null,
      ativo,
      roteiro: roteiro.map((l) => ({
        setor_id: l.setor_id,
        operacao: l.operacao,
        tempo_padrao_seg: l.tempo.trim() ? decimalInput(l.tempo) : null,
      })),
    };
    try {
      await api(produto ? `/produtos/${produto.id}` : "/produtos", {
        method: produto ? "PUT" : "POST",
        body: JSON.stringify(corpo),
      });
      onSalvo();
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Não foi possível salvar.");
    }
  }

  return (
    <div className="modal-back" onClick={onClose}>
      <form className="modal wide" onClick={(e) => e.stopPropagation()} onSubmit={salvar}>
        <h2>{produto ? `Editar ${produto.codigo}` : "Novo produto"}</h2>
        {erro ? <p className="error">{erro}</p> : null}
        <div className="form-grid">
          <label className="field">
            Código
            <input value={codigo} onChange={(e) => setCodigo(e.target.value)} placeholder="PU-100-6" required maxLength={30} />
          </label>
          <label className="field">
            Comprimento da chapa
            <select value={comprimento} onChange={(e) => setComprimento(e.target.value)}>
              <option value="3000">3 m</option>
              <option value="6000">6 m</option>
              {!["3000", "6000", ""].includes(comprimento) ? <option value={comprimento}>{comprimento} mm</option> : null}
              <option value="">Não se aplica</option>
            </select>
          </label>
          <label className="field full">
            Descrição
            <input
              value={descricao}
              onChange={(e) => setDescricao(e.target.value)}
              placeholder="Perfil U 100x40x2,00 mm - 6 m"
              required
              minLength={2}
            />
          </label>
          <label className="field">
            Unidade
            <select value={unidade} onChange={(e) => setUnidade(e.target.value)}>
              <option value="PC">PC (peça)</option>
              <option value="KG">KG</option>
              <option value="M">M (metro)</option>
            </select>
          </label>
          <label className="field" style={{ flexDirection: "row", alignItems: "center", gap: 8, marginTop: 22 }}>
            <input type="checkbox" checked={ativo} onChange={(e) => setAtivo(e.target.checked)} />
            Ativo (pode receber ordens)
          </label>
        </div>

        <h3 className="sub">Roteiro de fabricação</h3>
        <p className="hint">A ordem das linhas é o caminho da peça na fábrica. Cada etapa vira uma coluna no Kanban.</p>
        <div className="roteiro">
          {roteiro.map((l, i) => (
            <div key={i} className="roteiro-linha">
              <span className="seq">{i + 1}</span>
              <select value={l.setor_id} onChange={(e) => mudar(i, "setor_id", e.target.value)} aria-label="Centro de trabalho">
                {setores.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.nome}
                  </option>
                ))}
              </select>
              <input
                value={l.operacao}
                onChange={(e) => mudar(i, "operacao", e.target.value)}
                placeholder="O que é feito (ex.: cortar tiras de 180 mm)"
                required
                minLength={2}
              />
              <input
                value={l.tempo}
                onChange={(e) => mudar(i, "tempo", e.target.value)}
                placeholder="seg/peça"
                inputMode="decimal"
                aria-label="Tempo padrão por peça"
              />
              <button type="button" className="btn small" onClick={() => mover(i, -1)} disabled={i === 0} title="Subir">
                ↑
              </button>
              <button
                type="button"
                className="btn small"
                onClick={() => mover(i, 1)}
                disabled={i === roteiro.length - 1}
                title="Descer"
              >
                ↓
              </button>
              <button
                type="button"
                className="btn small"
                onClick={() => setRoteiro(roteiro.filter((_, j) => j !== i))}
                disabled={roteiro.length === 1}
                title="Remover"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
        <button type="button" className="btn small" onClick={adicionar} style={{ marginTop: 8 }}>
          + Adicionar etapa
        </button>

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
