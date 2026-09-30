"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "../lib/auth";
import { GearIcon } from "./AuthArt";

const stroke = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

const ICONES: Record<string, React.ReactNode> = {
  painel: (
    <svg width="18" height="18" viewBox="0 0 24 24" {...stroke}>
      <rect x="3.5" y="3.5" width="7" height="7" rx="1.5" />
      <rect x="13.5" y="3.5" width="7" height="4.5" rx="1.5" />
      <rect x="13.5" y="10.5" width="7" height="10" rx="1.5" />
      <rect x="3.5" y="13" width="7" height="7.5" rx="1.5" />
    </svg>
  ),
  kanban: (
    <svg width="18" height="18" viewBox="0 0 24 24" {...stroke}>
      <rect x="3" y="4" width="5" height="16" rx="1.2" />
      <rect x="10" y="4" width="5" height="10" rx="1.2" />
      <rect x="17" y="4" width="4" height="13" rx="1.2" />
    </svg>
  ),
  maquinas: (
    <svg width="18" height="18" viewBox="0 0 24 24" {...stroke}>
      <rect x="3" y="9" width="18" height="11" rx="1.5" />
      <path d="M7 9V5h4v4M15 13h3M6 13h5v4H6z" />
    </svg>
  ),
  produtos: (
    <svg width="18" height="18" viewBox="0 0 24 24" {...stroke}>
      <path d="M4 7h16M4 7v4h16V7M6 11v8M18 11v8M4 19h16" />
    </svg>
  ),
  usuarios: (
    <svg width="18" height="18" viewBox="0 0 24 24" {...stroke}>
      <circle cx="9" cy="7.5" r="3" />
      <path d="M3.5 19.5c.6-3 2.8-4.5 5.5-4.5s4.9 1.5 5.5 4.5" />
      <circle cx="17" cy="8.5" r="2.2" />
      <path d="M14.8 15.2c1.5-.5 3.1-.2 4.2.8" />
    </svg>
  ),
};

// Rotas protegidas: a tela exigida para abrir cada uma.
const TELA_DA_ROTA: [string, string][] = [
  ["/painel", "painel"],
  ["/kanban", "kanban"],
  ["/maquinas", "maquinas"],
  ["/produtos", "produtos"],
  ["/usuarios", "usuarios"],
];

export function Shell({ children }: { children: React.ReactNode }) {
  const { user, ready, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (ready && !user) router.replace("/login");
  }, [ready, user, router]);

  if (!ready || !user) return <p className="center-msg">Carregando…</p>;

  const exigida = TELA_DA_ROTA.find(([rota]) => pathname === rota || pathname.startsWith(`${rota}/`))?.[1];
  const permitido = !exigida || user.telas.includes(exigida);

  return (
    <div className="app">
      <aside className="side">
        <div className="brand">
          <div className="brand-mark">
            <GearIcon />
          </div>
          <div>
            <strong>FabriControl</strong>
            <span>Controle de produção</span>
          </div>
        </div>

        <nav className="nav">
          {user.menu.map((item) => {
            const ativo = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link key={item.tela} href={item.href} className={ativo ? "active" : ""}>
                {ICONES[item.tela]}
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="side-user">
          <strong>{user.nome}</strong>
          <span>{user.perfil_label}</span>
          <div className="side-actions">
            <Link href="/conta">Minha conta</Link>
            <button type="button" onClick={logout}>
              Sair
            </button>
          </div>
        </div>
      </aside>

      <div className="main">{permitido ? children : <p className="error">Seu perfil não acessa esta tela.</p>}</div>
    </div>
  );
}

export function PageHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <header className="page-head">
      <div>
        <h1>{title}</h1>
        {subtitle ? <p>{subtitle}</p> : null}
      </div>
      {action}
    </header>
  );
}
