"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { AuthArt } from "../components/AuthArt";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

export default function LoginPage() {
  const { user, ready, login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    if (ready && user) router.replace(user.inicio);
  }, [ready, user, router]);

  useEffect(() => {
    api<{ needs_setup: boolean }>("/setup/status")
      .then((s) => s.needs_setup && router.replace("/setup"))
      .catch(() => undefined);
  }, [router]);

  async function entrar(e: FormEvent) {
    e.preventDefault();
    setErro("");
    setEnviando(true);
    try {
      const u = await login(email, senha);
      router.replace(u.inicio);
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Não foi possível entrar.");
      setEnviando(false);
    }
  }

  return (
    <main className="auth">
      <AuthArt />
      <section className="auth-form">
        <form onSubmit={entrar}>
          <div>
            <h2>Entrar</h2>
            <p>Use o e-mail e a senha cadastrados pelo administrador.</p>
          </div>
          {erro ? <div className="error">{erro}</div> : null}
          <label className="field">
            E-mail
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" required />
          </label>
          <label className="field">
            Senha
            <input
              type="password"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          <button className="btn primary" disabled={enviando}>
            {enviando ? "Entrando…" : "Entrar"}
          </button>
        </form>
      </section>
    </main>
  );
}
