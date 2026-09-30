"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { AuthArt } from "../components/AuthArt";
import { api } from "../lib/api";
import { SessionUser, useAuth } from "../lib/auth";

export default function SetupPage() {
  const { enter } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({ nome: "", email: "", senha: "", confirma: "" });
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    api<{ needs_setup: boolean }>("/setup/status")
      .then((s) => !s.needs_setup && router.replace("/login"))
      .catch(() => undefined);
  }, [router]);

  async function salvar(e: FormEvent) {
    e.preventDefault();
    setErro("");
    if (form.senha !== form.confirma) {
      setErro("As senhas não conferem.");
      return;
    }
    setEnviando(true);
    try {
      const sessao = await api<{ access_token: string; user: SessionUser }>("/setup", {
        method: "POST",
        body: JSON.stringify({ nome: form.nome, email: form.email, senha: form.senha }),
      });
      enter(sessao);
      router.replace(sessao.user.inicio);
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Não foi possível concluir.");
      setEnviando(false);
    }
  }

  const campo = (chave: keyof typeof form) => ({
    value: form[chave],
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [chave]: e.target.value }),
  });

  return (
    <main className="auth">
      <AuthArt />
      <section className="auth-form">
        <form onSubmit={salvar}>
          <div>
            <h2>Primeiro acesso</h2>
            <p>Crie o usuário administrador. Depois ele cadastra o restante da equipe.</p>
          </div>
          {erro ? <div className="error">{erro}</div> : null}
          <label className="field">
            Seu nome
            <input {...campo("nome")} required minLength={2} />
          </label>
          <label className="field">
            E-mail
            <input type="email" {...campo("email")} autoComplete="username" required />
          </label>
          <label className="field">
            Senha (mínimo 8 caracteres)
            <input type="password" {...campo("senha")} autoComplete="new-password" required minLength={8} />
          </label>
          <label className="field">
            Confirme a senha
            <input type="password" {...campo("confirma")} autoComplete="new-password" required minLength={8} />
          </label>
          <button className="btn primary" disabled={enviando}>
            {enviando ? "Criando…" : "Criar administrador"}
          </button>
        </form>
      </section>
    </main>
  );
}
