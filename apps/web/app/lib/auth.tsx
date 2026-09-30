"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api, clearToken, getToken, setToken } from "./api";

export type MenuItem = { tela: string; label: string; href: string };

export type Perfil = "administrador" | "pcp" | "supervisor" | "operador" | "qualidade";

export type SessionUser = {
  id: string;
  nome: string;
  email: string;
  perfil: Perfil;
  perfil_label: string;
  ativo: boolean;
  telas: string[];
  acoes: string[];
  menu: MenuItem[];
  inicio: string;
};

export type Acao = "editar_cadastros" | "gerenciar_usuarios";

export function temAcao(user: SessionUser | null, acao: Acao) {
  return Boolean(user && user.acoes.includes(acao));
}

type Sessao = { access_token: string; user: SessionUser };

type AuthState = {
  user: SessionUser | null;
  ready: boolean;
  login: (email: string, senha: string) => Promise<SessionUser>;
  enter: (sessao: Sessao) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      setReady(true);
      return;
    }
    api<SessionUser>("/auth/me")
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setReady(true));
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      user,
      ready,
      async login(email: string, senha: string) {
        const data = await api<Sessao>("/auth/login", { method: "POST", body: JSON.stringify({ email, senha }) });
        setToken(data.access_token);
        setUser(data.user);
        return data.user;
      },
      enter(sessao: Sessao) {
        setToken(sessao.access_token);
        setUser(sessao.user);
      },
      logout() {
        clearToken();
        setUser(null);
        window.location.href = "/login";
      },
    }),
    [user, ready],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("Auth ausente");
  return ctx;
}
