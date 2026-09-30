"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { PageHeader } from "../../components/Shell";
import { api } from "../../lib/api";
import { Perfil, SessionUser, useAuth } from "../../lib/auth";

type PerfilInfo = { perfil: Perfil; label: string; telas: string[]; acoes: string[] };

export default function UsuariosPage() {
  const { user } = useAuth();
  const [usuarios, setUsuarios] = useState<SessionUser[] | null>(null);
  const [perfis, setPerfis] = useState<PerfilInfo[]>([]);
  const [editando, setEditando] = useState<SessionUser | "novo" | null>(null);
  const [erro, setErro] = useState("");

  const carregar = useCallback(() => {
    Promise.all([api<SessionUser[]>("/usuarios"), api<PerfilInfo[]>("/usuarios/perfis")])
      .then(([u, p]) => {
        setUsuarios(u);
        setPerfis(p);
      })
      .catch((e: Error) => setErro(e.message));
  }, []);

  useEffect(carregar, [carregar]);

  async function alternarAtivo(u: SessionUser) {
    setErro("");
    try {
      await api(`/usuarios/${u.id}`, { method: "PATCH", body: JSON.stringify({ ativo: !u.ativo }) });
      carregar();
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não foi possível alterar.");
    }
  }

  return (
    <>
      <PageHeader
        title="Usuários"
        subtitle="Cada pessoa entra com o próprio e-mail e vê só as telas do perfil dela."
        action={
          <button className="btn primary" onClick={() => setEditando("novo")}>
            Novo usuário
          </button>
        }
      />
      {erro ? <p className="error">{erro}</p> : null}
      <div className="table-wrap">
        {usuarios === null ? (
          <p className="empty">Carregando…</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Nome</th>
                <th>E-mail</th>
                <th>Perfil</th>
                <th>Situação</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {usuarios.map((u) => (
                <tr key={u.id}>
                  <td>
                    {u.nome}
                    {u.id === user?.id ? <span className="hint"> (você)</span> : null}
                  </td>
                  <td>{u.email}</td>
                  <td>{u.perfil_label}</td>
                  <td>
                    <span className={`badge ${u.ativo ? "ativa" : "inativa"}`}>{u.ativo ? "Ativo" : "Inativo"}</span>
                  </td>
                  <td className="num" style={{ whiteSpace: "nowrap" }}>
                    <button className="btn small" onClick={() => setEditando(u)}>
                      Editar
                    </button>{" "}
                    {u.id !== user?.id ? (
                      <button className="btn small" onClick={() => alternarAtivo(u)}>
                        {u.ativo ? "Desativar" : "Reativar"}
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <h2 style={{ fontSize: 16, marginTop: 28, marginBottom: 0 }}>O que cada perfil acessa</h2>
      <div className="perfis">
        {perfis.map((p) => (
          <div key={p.perfil} className="card">
            <h3>{p.label}</h3>
            <ul>
              {p.telas.map((t) => (
                <li key={t}>{t}</li>
              ))}
              {p.acoes.map((a) => (
                <li key={a}>{a}</li>
              ))}
              {p.telas.length + p.acoes.length === 0 ? <li>Telas de apontamento (próximas sprints)</li> : null}
            </ul>
          </div>
        ))}
      </div>

      {editando ? (
        <UsuarioForm
          usuario={editando === "novo" ? null : editando}
          perfis={perfis}
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

function UsuarioForm({
  usuario,
  perfis,
  onClose,
  onSalvo,
}: {
  usuario: SessionUser | null;
  perfis: PerfilInfo[];
  onClose: () => void;
  onSalvo: () => void;
}) {
  const [nome, setNome] = useState(usuario?.nome ?? "");
  const [email, setEmail] = useState(usuario?.email ?? "");
  const [perfil, setPerfil] = useState<Perfil>(usuario?.perfil ?? "operador");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState("");

  async function salvar(e: FormEvent) {
    e.preventDefault();
    setErro("");
    const corpo = usuario ? { nome, perfil, ...(senha ? { senha } : {}) } : { nome, email, perfil, senha };
    try {
      await api(usuario ? `/usuarios/${usuario.id}` : "/usuarios", {
        method: usuario ? "PATCH" : "POST",
        body: JSON.stringify(corpo),
      });
      onSalvo();
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Não foi possível salvar.");
    }
  }

  return (
    <div className="modal-back" onClick={onClose}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={salvar}>
        <h2>{usuario ? `Editar ${usuario.nome}` : "Novo usuário"}</h2>
        {erro ? <p className="error">{erro}</p> : null}
        <div className="form-grid">
          <label className="field full">
            Nome
            <input value={nome} onChange={(e) => setNome(e.target.value)} required minLength={2} />
          </label>
          <label className="field">
            E-mail
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} disabled={Boolean(usuario)} required />
          </label>
          <label className="field">
            Perfil
            <select value={perfil} onChange={(e) => setPerfil(e.target.value as Perfil)}>
              {perfis.map((p) => (
                <option key={p.perfil} value={p.perfil}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field full">
            {usuario ? "Nova senha (deixe em branco para manter)" : "Senha inicial (mínimo 8 caracteres)"}
            <input
              type="password"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              autoComplete="new-password"
              minLength={8}
              required={!usuario}
            />
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
