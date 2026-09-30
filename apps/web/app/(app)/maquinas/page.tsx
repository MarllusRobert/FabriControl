"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { PageHeader } from "../../components/Shell";
import { api } from "../../lib/api";
import { temAcao, useAuth } from "../../lib/auth";
import { Maquina, STATUS_LABEL, Setor, StatusMaquina, decimalInput, numero } from "../../lib/cadastros";

type Aba = "maquinas" | "setores";

export default function MaquinasPage() {
  const { user } = useAuth();
  const podeEditar = temAcao(user, "editar_cadastros");
  const [aba, setAba] = useState<Aba>("maquinas");
  const [setores, setSetores] = useState<Setor[]>([]);
  const [erro, setErro] = useState("");

  const carregarSetores = useCallback(() => {
    api<Setor[]>("/setores")
      .then(setSetores)
      .catch((e: Error) => setErro(e.message));
  }, []);

  useEffect(carregarSetores, [carregarSetores]);

  return (
    <>
      <PageHeader title="Máquinas" subtitle="Parque de máquinas, centros de trabalho e tempo de ciclo padrão." />
      {erro ? <p className="error">{erro}</p> : null}
      <div className="tabs">
        <button className={aba === "maquinas" ? "active" : ""} onClick={() => setAba("maquinas")}>
          Máquinas
        </button>
        <button className={aba === "setores" ? "active" : ""} onClick={() => setAba("setores")}>
          Centros de trabalho
        </button>
      </div>
      {aba === "maquinas" ? (
        <ListaMaquinas setores={setores} podeEditar={podeEditar} />
      ) : (
        <ListaSetores setores={setores} podeEditar={podeEditar} onMudou={carregarSetores} />
      )}
    </>
  );
}

function ListaMaquinas({ setores, podeEditar }: { setores: Setor[]; podeEditar: boolean }) {
  const [maquinas, setMaquinas] = useState<Maquina[] | null>(null);
  const [busca, setBusca] = useState("");
  const [setorId, setSetorId] = useState("");
  const [status, setStatus] = useState("");
  const [editando, setEditando] = useState<Maquina | "nova" | null>(null);
  const [erro, setErro] = useState("");

  const carregar = useCallback(() => {
    const params = new URLSearchParams();
    if (busca.trim()) params.set("busca", busca.trim());
    if (setorId) params.set("setor_id", setorId);
    if (status) params.set("status", status);
    api<Maquina[]>(`/maquinas?${params}`)
      .then(setMaquinas)
      .catch((e: Error) => setErro(e.message));
  }, [busca, setorId, status]);

  useEffect(() => {
    const t = setTimeout(carregar, 250);
    return () => clearTimeout(t);
  }, [carregar]);

  return (
    <>
      <div className="toolbar">
        <input placeholder="Buscar por código ou nome" value={busca} onChange={(e) => setBusca(e.target.value)} />
        <select value={setorId} onChange={(e) => setSetorId(e.target.value)} aria-label="Centro de trabalho">
          <option value="">Todos os centros</option>
          {setores.map((s) => (
            <option key={s.id} value={s.id}>
              {s.nome}
            </option>
          ))}
        </select>
        <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
          <option value="">Todos os status</option>
          {Object.entries(STATUS_LABEL).map(([valor, label]) => (
            <option key={valor} value={valor}>
              {label}
            </option>
          ))}
        </select>
        {podeEditar ? (
          <button className="btn primary" onClick={() => setEditando("nova")} disabled={setores.length === 0}>
            Nova máquina
          </button>
        ) : null}
      </div>
      {podeEditar && setores.length === 0 ? (
        <p className="hint">Cadastre um centro de trabalho antes da primeira máquina.</p>
      ) : null}
      {erro ? <p className="error">{erro}</p> : null}

      <div className="table-wrap">
        {maquinas === null ? (
          <p className="empty">Carregando…</p>
        ) : maquinas.length === 0 ? (
          <p className="empty">Nenhuma máquina encontrada.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Código</th>
                <th>Máquina</th>
                <th>Centro de trabalho</th>
                <th className="num">Ciclo padrão</th>
                <th className="num">Peças/hora</th>
                <th>Status</th>
                {podeEditar ? <th /> : null}
              </tr>
            </thead>
            <tbody>
              {maquinas.map((m) => (
                <tr key={m.id}>
                  <td className="mono">{m.codigo}</td>
                  <td>
                    {m.nome}
                    {m.observacao ? <div className="hint">{m.observacao}</div> : null}
                  </td>
                  <td>{m.setor_nome}</td>
                  <td className="num">{numero(m.ciclo_padrao_seg, m.ciclo_padrao_seg % 1 ? 1 : 0)} s</td>
                  <td className="num">{numero(m.pecas_por_hora, 1)}</td>
                  <td>
                    <span className={`badge ${m.status}`}>{m.status_label}</span>
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
        <MaquinaForm
          maquina={editando === "nova" ? null : editando}
          setores={setores.filter((s) => s.ativo || (editando !== "nova" && s.id === editando.setor_id))}
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

function MaquinaForm({
  maquina,
  setores,
  onClose,
  onSalvo,
}: {
  maquina: Maquina | null;
  setores: Setor[];
  onClose: () => void;
  onSalvo: () => void;
}) {
  const [codigo, setCodigo] = useState(maquina?.codigo ?? "");
  const [nome, setNome] = useState(maquina?.nome ?? "");
  const [setorId, setSetorId] = useState(maquina?.setor_id ?? setores[0]?.id ?? "");
  const [ciclo, setCiclo] = useState(maquina ? String(maquina.ciclo_padrao_seg).replace(".", ",") : "");
  const [status, setStatus] = useState<StatusMaquina>(maquina?.status ?? "ativa");
  const [observacao, setObservacao] = useState(maquina?.observacao ?? "");
  const [erro, setErro] = useState("");
  const [salvando, setSalvando] = useState(false);

  const cicloNum = decimalInput(ciclo);
  const pecasHora = cicloNum > 0 ? 3600 / cicloNum : 0;

  async function salvar(e: FormEvent) {
    e.preventDefault();
    setErro("");
    if (!(cicloNum > 0)) {
      setErro("Informe o tempo de ciclo em segundos (ex.: 12 ou 12,5).");
      return;
    }
    setSalvando(true);
    const corpo = { codigo, nome, setor_id: setorId, ciclo_padrao_seg: cicloNum, status, observacao: observacao || null };
    try {
      await api(maquina ? `/maquinas/${maquina.id}` : "/maquinas", {
        method: maquina ? "PATCH" : "POST",
        body: JSON.stringify(corpo),
      });
      onSalvo();
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Não foi possível salvar.");
      setSalvando(false);
    }
  }

  return (
    <div className="modal-back" onClick={onClose}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={salvar}>
        <h2>{maquina ? `Editar ${maquina.codigo}` : "Nova máquina"}</h2>
        {erro ? <p className="error">{erro}</p> : null}
        <div className="form-grid">
          <label className="field">
            Código
            <input value={codigo} onChange={(e) => setCodigo(e.target.value)} placeholder="COR-01" required maxLength={20} />
          </label>
          <label className="field">
            Centro de trabalho
            <select value={setorId} onChange={(e) => setSetorId(e.target.value)} required>
              {setores.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.codigo} · {s.nome}
                </option>
              ))}
            </select>
          </label>
          <label className="field full">
            Nome da máquina
            <input value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Guilhotina hidráulica 3 m" required minLength={2} />
          </label>
          <label className="field">
            Tempo de ciclo padrão (segundos por peça)
            <input value={ciclo} onChange={(e) => setCiclo(e.target.value)} inputMode="decimal" placeholder="12" required />
            <span className="hint">{pecasHora ? `Capacidade: ${numero(pecasHora, 1)} peças/hora` : "Base da performance no OEE"}</span>
          </label>
          <label className="field">
            Status
            <select value={status} onChange={(e) => setStatus(e.target.value as StatusMaquina)}>
              {Object.entries(STATUS_LABEL).map(([valor, label]) => (
                <option key={valor} value={valor}>
                  {label}
                </option>
              ))}
            </select>
            <span className="hint">Só máquina ativa recebe ordem de produção.</span>
          </label>
          <label className="field full">
            Observação
            <textarea value={observacao} onChange={(e) => setObservacao(e.target.value)} rows={2} maxLength={500} />
          </label>
        </div>
        <div className="form-actions">
          <button type="button" className="btn" onClick={onClose}>
            Cancelar
          </button>
          <button className="btn primary" disabled={salvando}>
            {salvando ? "Salvando…" : "Salvar"}
          </button>
        </div>
      </form>
    </div>
  );
}

function ListaSetores({ setores, podeEditar, onMudou }: { setores: Setor[]; podeEditar: boolean; onMudou: () => void }) {
  const [editando, setEditando] = useState<Setor | "novo" | null>(null);

  return (
    <>
      {podeEditar ? (
        <div className="toolbar" style={{ justifyContent: "flex-end" }}>
          <button className="btn primary" onClick={() => setEditando("novo")}>
            Novo centro de trabalho
          </button>
        </div>
      ) : null}
      <div className="table-wrap">
        {setores.length === 0 ? (
          <p className="empty">Nenhum centro de trabalho cadastrado.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th className="num">Fluxo</th>
                <th>Código</th>
                <th>Nome</th>
                <th className="num">Máquinas</th>
                <th>Situação</th>
                {podeEditar ? <th /> : null}
              </tr>
            </thead>
            <tbody>
              {setores.map((s) => (
                <tr key={s.id}>
                  <td className="num">{s.ordem}</td>
                  <td className="mono">{s.codigo}</td>
                  <td>{s.nome}</td>
                  <td className="num">{s.maquinas}</td>
                  <td>
                    <span className={`badge ${s.ativo ? "ativa" : "inativa"}`}>{s.ativo ? "Ativo" : "Inativo"}</span>
                  </td>
                  {podeEditar ? (
                    <td className="num">
                      <button className="btn small" onClick={() => setEditando(s)}>
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
        <SetorForm
          setor={editando === "novo" ? null : editando}
          onClose={() => setEditando(null)}
          onSalvo={() => {
            setEditando(null);
            onMudou();
          }}
        />
      ) : null}
    </>
  );
}

function SetorForm({ setor, onClose, onSalvo }: { setor: Setor | null; onClose: () => void; onSalvo: () => void }) {
  const [codigo, setCodigo] = useState(setor?.codigo ?? "");
  const [nome, setNome] = useState(setor?.nome ?? "");
  const [ordem, setOrdem] = useState(String(setor?.ordem ?? 0));
  const [ativo, setAtivo] = useState(setor?.ativo ?? true);
  const [erro, setErro] = useState("");

  async function salvar(e: FormEvent) {
    e.preventDefault();
    setErro("");
    try {
      await api(setor ? `/setores/${setor.id}` : "/setores", {
        method: setor ? "PUT" : "POST",
        body: JSON.stringify({ codigo, nome, ordem: Number(ordem) || 0, ativo }),
      });
      onSalvo();
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Não foi possível salvar.");
    }
  }

  return (
    <div className="modal-back" onClick={onClose}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={salvar}>
        <h2>{setor ? `Editar ${setor.nome}` : "Novo centro de trabalho"}</h2>
        {erro ? <p className="error">{erro}</p> : null}
        <div className="form-grid">
          <label className="field">
            Código
            <input value={codigo} onChange={(e) => setCodigo(e.target.value)} placeholder="COR" required maxLength={20} />
          </label>
          <label className="field">
            Nome
            <input value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Corte" required minLength={2} />
          </label>
          <label className="field">
            Posição no fluxo da fábrica
            <input type="number" min={0} max={99} value={ordem} onChange={(e) => setOrdem(e.target.value)} />
            <span className="hint">Ordem das colunas no Kanban (ex.: 1 Desbobinamento, 2 Corte, 3 Dobra).</span>
          </label>
          <label className="field full" style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
            <input type="checkbox" checked={ativo} onChange={(e) => setAtivo(e.target.checked)} />
            Ativo (centro inativo não recebe máquinas novas nem ordens)
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
