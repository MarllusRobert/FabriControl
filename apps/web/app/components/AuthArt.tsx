export function AuthArt() {
  return (
    <aside className="auth-art">
      <div className="brand">
        <div className="brand-mark">
          <GearIcon />
        </div>
        <div>
          <strong>FabriControl</strong>
          <span>Controle de produção industrial</span>
        </div>
      </div>
      <div>
        <h1>A fábrica inteira numa tela só.</h1>
        <p>
          Ordens de produção, apontamento no chão de fábrica e indicadores como o OEE, com cada pessoa vendo
          exatamente o que é da função dela.
        </p>
        <ul>
          <li>Máquinas e centros de trabalho organizados</li>
          <li>Planejamento e fila de produção por máquina</li>
          <li>Paradas, refugo e eficiência em tempo real</li>
        </ul>
      </div>
      <small style={{ color: "#8b96a1" }}>FabriControl · Zion Sistemas</small>
    </aside>
  );
}

export function GearIcon({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <circle cx="12" cy="12" r="3.2" />
      <path d="M12 2.5v3M12 18.5v3M4.2 6.2l2.1 2.1M17.7 15.7l2.1 2.1M2.5 12h3M18.5 12h3M4.2 17.8l2.1-2.1M17.7 8.3l2.1-2.1" />
    </svg>
  );
}
