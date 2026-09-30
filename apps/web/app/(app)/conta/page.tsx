"use client";

import { FormEvent, useState } from "react";
import { PageHeader } from "../../components/Shell";
import { api } from "../../lib/api";
import { SessionUser, useAuth } from "../../lib/auth";

export default function ContaPage() {
  const { user, enter } = useAuth();
  const [atual, setAtual] = useState("");
  const [nova, setNova] = useState("");
  const [confirma, setConfirma] = useState("");
  const [erro, setErro] = useState("");
  const [ok, setOk] = useState(false);

  async function salvar(e: FormEvent) {
    e.preventDefault();
    setErro("");
    setOk(false);
    if (nova !== confirma) {
      setErro("A confirmação não confere com a nova senha.");
      return;
    }
    try {
      const sessao = await api<{ access_token: string; user: SessionUser }>("/auth/senha", {
        method: "POST",
        body: JSON.stringify({ senha_atual: atual, nova_senha: nova }),
      });
      enter(sessao);
      setAtual("");
      setNova("");
      setConfirma("");
      setOk(true);
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Não foi possível trocar a senha.");
    }
  }

  return (
    <>
      <PageHeader title="Minha conta" subtitle={`${user?.email} · ${user?.perfil_label}`} />
      <form className="card" style={{ maxWidth: 460 }} onSubmit={salvar}>
        <h2>Trocar senha</h2>
        {erro ? <p className="error">{erro}</p> : null}
        {ok ? <p className="hint">Senha alterada. As sessões abertas em outros aparelhos foram encerradas.</p> : null}
        <div className="form-grid">
          <label className="field full">
            Senha atual
            <input type="password" value={atual} onChange={(e) => setAtual(e.target.value)} autoComplete="current-password" required />
          </label>
          <label className="field full">
            Nova senha (mínimo 8 caracteres)
            <input type="password" value={nova} onChange={(e) => setNova(e.target.value)} autoComplete="new-password" minLength={8} required />
          </label>
          <label className="field full">
            Confirme a nova senha
            <input
              type="password"
              value={confirma}
              onChange={(e) => setConfirma(e.target.value)}
              autoComplete="new-password"
              minLength={8}
              required
            />
          </label>
        </div>
        <div className="form-actions">
          <button className="btn primary">Salvar nova senha</button>
        </div>
      </form>
    </>
  );
}
