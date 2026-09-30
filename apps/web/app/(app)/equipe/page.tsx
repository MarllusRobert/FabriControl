"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { PageHeader } from "../../components/Shell";
import { api } from "../../lib/api";
import { temAcao, useAuth } from "../../lib/auth";
import { Setor } from "../../lib/cadastros";
import { Operador, Turno, duracaoLabel } from "../../lib/equipe";

type Aba = "operadores" | "turnos";

export default function EquipePage() {
  const { user } = useAuth();
  const podeEditar = temAcao(user, "gerenciar_equipe");
  const [aba, setAba] = useState<Aba>("operadores");
  const [turnos, setTurnos] = useState<Turno[]>([]);
  const [setores, setSetores] = useState<Setor[]>([]);
  const [erro, setErro] = useState("");

  const carregarTurnos = useCallback(() => {
    api<Turno[]>("/turnos")
      .then(setTurnos)
      .catch((e: Error) => setErro(e.message));
  }, []);

  useEffect(carregarTurnos, [carregarTurnos]);
  useEffect(() => {
    api<Setor[]>("/setores")
      .then(setSetores)
      .catch((e: Error) => setErro(e.message));
  }, []);

  return (
    <>
      <PageHeader title="Equipe" subtitle="Turnos de trabalho e operadores de cada centro de trabalho." />
      {erro ? <p className="error">{erro}</p> : null}
      <div className="tabs">
        <button className={aba === "operadores" ? "active" : ""} onClick={() => setAba("operadores")}>
          Operadores
        </button>
        <button className={aba === "turnos" ? "active" : ""} onClick={() => setAba("turnos")}>
          Turnos
        </button>
      </div>
      {aba === "operadores" ? (
        <ListaOperadores turnos={turnos} setores={setores} podeEditar={podeEditar} onMudou={carregarTurnos} />
      ) : (
        <ListaTurnos turnos={turnos} podeEditar={podeEditar} onMudou={carregarTurnos} />
      )}
    </>
  );
}

function ListaOperadores({
  turnos,
  setores,
  podeEditar,
  onMudou,
}: {
  turnos: Turno[];
  setores: Setor[];
  podeEditar: boolean;
  onMudou: () => void;
}) {
  const [operadores, setOperadores] = useState<Operador[] | null>(null);
  const [busca, setBusca] = useState("");
  const [turnoId, setTurnoId] = useState("");
  const [setorId, setSetorId] = useState("");
  const [editando, setEditando] = useState<Operador | "novo" | null>(null);
  const [erro, setErro] = useState("");

  const carregar = useCallback(() => {
    const params = new URLSearchParams();
    if (busca.trim()) params.set("busca", busca.trim());
    if (turnoId) params.set("turno_id", turnoId);
    if (setorId) params.set("setor_id", setorId);
    api<Operador[]>(`/operadores?${params}`)
      .then(setOperadores)
      .catch((e: Error) => setErro(e.message));
  }, [busca, turnoId, setorId]);

  useEffect(() => {
    const t = setTimeout(carregar, 250);
    return () => clearTimeout(t);
  }, [carregar]);

  const semBase = turnos.every((t) => !t.ativo) || setores.every((s) => !s.ativo);

  return (
    <>
      <div className="toolbar">
        <input placeholder="Buscar por matrícula ou nome" value={busca} onChange={(e) => setBusca(e.target.value)} />
        <select value={turnoId} onChange={(e) => setTurnoId(e.target.value)} aria-label="Turno">
          <option value="">Todos os turnos</option>
          {turnos.map((t) => (
            <option key={t.id} value={t.id}>
              {t.nome}
            </option>
          ))}
        </select>
        <select value={setorId} onChange={(e) => setSetorId(e.target.value)} aria-label="Centro de trabalho">
          <option value="">Todos os centros</option>
          {setores.map((s) => (
            <option key={s.id} value={s.id}>
              {s.nome}
            </option>
          ))}
        </select>
        {podeEditar ? (
          <button className="btn primary" onClick={() => setEditando("novo")} disabled={semBase}>
            Novo operador
          </button>
        ) : null}
      </div>
      {podeEditar && semBase ? (
        <p className="hint">Cadastre ao menos um turno e um centro de trabalho ativos antes do primeiro operador.</p>
      ) : null}
      {erro ? <p className="error">{erro}</p> : null}

      <div className="table-wrap">
        {operadores === null ? (
          <p className="empty">Carregando…</p>
        ) : operadores.length === 0 ? (
          <p className="empty">Nenhum operador encontrado.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Matrícula</th>
                <th>Nome</th>
                <th>Turno</th>
                <th>Centro de trabalho</th>
                <th>Situação</th>
                {podeEditar ? <th /> : null}
              </tr>
            </thead>
            <tbody>
              {operadores.map((o) => (
                <tr key={o.id}>
                  <td className="mono">{o.matricula}</td>
                  <td>{o.nome}</td>
                  <td>
                    {o.turno_nome}
                    <div className="hint">{o.turno_horario}</div>
                  </td>
                  <td>{o.setor_nome}</td>
                  <td>
                    <span className={`badge ${o.ativo ? "ativa" : "inativa"}`}>{o.ativo ? "Ativo" : "Inativo"}</span>
                  </td>
                  {podeEditar ? (
                    <td className="num">
                      <button className="btn small" onClick={() => setEditando(o)}>
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
        <OperadorForm
          operador={editando === "novo" ? null : editando}
          turnos={turnos.filter((t) => t.ativo || (editando !== "novo" && t.id === editando.turno_id))}
          setores={setores.filter((s) => s.ativo || (editando !== "novo" && s.id === editando.setor_id))}
          onClose={() => setEditando(null)}
          onSalvo={() => {
            setEditando(null);
            carregar();
            onMudou();
          }}
        />
      ) : null}
    </>
  );
}

function OperadorForm({
  operador,
  turnos,
  setores,
  onClose,
  onSalvo,
}: {
  operador: Operador | null;
  turnos: Turno[];
  setores: Setor[];
  onClose: () => void;
  onSalvo: () => void;
}) {
  const [matricula, setMatricula] = useState(operador?.matricula ?? "");
  const [nome, setNome] = useState(operador?.nome ?? "");
  const [turnoId, setTurnoId] = useState(operador?.turno_id ?? turnos[0]?.id ?? "");
  const [setorId, setSetorId] = useState(operador?.setor_id ?? setores[0]?.id ?? "");
  const [ativo, setAtivo] = useState(operador?.ativo ?? true);
  const [erro, setErro] = useState("");
  const [salvando, setSalvando] = useState(false);

  async function salvar(e: FormEvent) {
    e.preventDefault();
    setErro("");
    setSalvando(true);
    try {
      await api(operador ? `/operadores/${operador.id}` : "/operadores", {
        method: operador ? "PUT" : "POST",
        body: JSON.stringify({ matricula, nome, turno_id: turnoId, setor_id: setorId, ativo }),
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
        <h2>{operador ? `Editar ${operador.nome}` : "Novo operador"}</h2>
        {erro ? <p className="error">{erro}</p> : null}
        <div className="form-grid">
          <label className="field">
            Matrícula
            <input value={matricula} onChange={(e) => setMatricula(e.target.value)} placeholder="1001" required maxLength={20} />
          </label>
          <label className="field">
            Nome
            <input value={nome} onChange={(e) => setNome(e.target.value)} required minLength={2} maxLength={120} />
          </label>
          <label className="field">
            Turno
            <select value={turnoId} onChange={(e) => setTurnoId(e.target.value)} required>
              {turnos.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.nome} · {t.inicio} às {t.fim}
                </option>
              ))}
            </select>
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
          <label className="field full" style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
            <input type="checkbox" checked={ativo} onChange={(e) => setAtivo(e.target.checked)} />
            Ativo
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

function ListaTurnos({ turnos, podeEditar, onMudou }: { turnos: Turno[]; podeEditar: boolean; onMudou: () => void }) {
  const [editando, setEditando] = useState<Turno | "novo" | null>(null);

  return (
    <>
      {podeEditar ? (
        <div className="toolbar" style={{ justifyContent: "flex-end" }}>
          <button className="btn primary" onClick={() => setEditando("novo")}>
            Novo turno
          </button>
        </div>
      ) : null}
      <div className="table-wrap">
        {turnos.length === 0 ? (
          <p className="empty">Nenhum turno cadastrado.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Código</th>
                <th>Turno</th>
                <th>Horário</th>
                <th className="num">Duração</th>
                <th className="num">Operadores</th>
                <th>Situação</th>
                {podeEditar ? <th /> : null}
              </tr>
            </thead>
            <tbody>
              {turnos.map((t) => (
                <tr key={t.id}>
                  <td className="mono">{t.codigo}</td>
                  <td>{t.nome}</td>
                  <td>
                    {t.inicio} às {t.fim}
                    {t.vira_meia_noite ? <div className="hint">Termina no dia seguinte</div> : null}
                  </td>
                  <td className="num">{duracaoLabel(t.duracao_min)}</td>
                  <td className="num">{t.operadores}</td>
                  <td>
                    <span className={`badge ${t.ativo ? "ativa" : "inativa"}`}>{t.ativo ? "Ativo" : "Inativo"}</span>
                  </td>
                  {podeEditar ? (
                    <td className="num">
                      <button className="btn small" onClick={() => setEditando(t)}>
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
        <TurnoForm
          turno={editando === "novo" ? null : editando}
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

function TurnoForm({ turno, onClose, onSalvo }: { turno: Turno | null; onClose: () => void; onSalvo: () => void }) {
  const [codigo, setCodigo] = useState(turno?.codigo ?? "");
  const [nome, setNome] = useState(turno?.nome ?? "");
  const [inicio, setInicio] = useState(turno?.inicio ?? "06:00");
  const [fim, setFim] = useState(turno?.fim ?? "14:00");
  const [ativo, setAtivo] = useState(turno?.ativo ?? true);
  const [erro, setErro] = useState("");

  const viraMeiaNoite = Boolean(inicio && fim && fim < inicio);

  async function salvar(e: FormEvent) {
    e.preventDefault();
    setErro("");
    try {
      await api(turno ? `/turnos/${turno.id}` : "/turnos", {
        method: turno ? "PUT" : "POST",
        body: JSON.stringify({ codigo, nome, inicio, fim, ativo }),
      });
      onSalvo();
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Não foi possível salvar.");
    }
  }

  return (
    <div className="modal-back" onClick={onClose}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={salvar}>
        <h2>{turno ? `Editar ${turno.nome}` : "Novo turno"}</h2>
        {erro ? <p className="error">{erro}</p> : null}
        <div className="form-grid">
          <label className="field">
            Código
            <input value={codigo} onChange={(e) => setCodigo(e.target.value)} placeholder="T1" required maxLength={10} />
          </label>
          <label className="field">
            Nome
            <input value={nome} onChange={(e) => setNome(e.target.value)} placeholder="1º turno" required minLength={2} maxLength={60} />
          </label>
          <label className="field">
            Início
            <input type="time" value={inicio} onChange={(e) => setInicio(e.target.value)} required />
          </label>
          <label className="field">
            Fim
            <input type="time" value={fim} onChange={(e) => setFim(e.target.value)} required />
            {viraMeiaNoite ? <span className="hint">Termina no dia seguinte (passa da meia-noite).</span> : null}
          </label>
          <label className="field full" style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
            <input type="checkbox" checked={ativo} onChange={(e) => setAtivo(e.target.checked)} />
            Ativo (turnos ativos não podem ter horários sobrepostos)
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
