"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { PageHeader } from "../../components/Shell";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { Maquina, ResumoMaquinas, numero } from "../../lib/cadastros";

export default function PainelPage() {
  const { user } = useAuth();
  const [resumo, setResumo] = useState<ResumoMaquinas | null>(null);
  const [paradas, setParadas] = useState<Maquina[]>([]);
  const [erro, setErro] = useState("");

  useEffect(() => {
    Promise.all([api<ResumoMaquinas>("/maquinas/resumo"), api<Maquina[]>("/maquinas")])
      .then(([r, maquinas]) => {
        setResumo(r);
        setParadas(maquinas.filter((m) => !m.recebe_ordem));
      })
      .catch((e: Error) => setErro(e.message));
  }, []);

  if (erro) return <p className="error">{erro}</p>;
  if (!resumo) return <p className="center-msg">Carregando painel…</p>;

  const maiorSetor = Math.max(1, ...resumo.por_setor.map((s) => s.total));
  const disponiveis = resumo.por_status.find((s) => s.status === "ativa")?.total ?? 0;
  const disponibilidade = resumo.total ? (disponiveis / resumo.total) * 100 : 0;

  return (
    <>
      <PageHeader
        title={`Olá, ${user?.nome.split(" ")[0]}`}
        subtitle="Situação do parque de máquinas. Produção e OEE entram aqui conforme as próximas sprints."
      />

      <section className="grid-kpi">
        <div className="kpi total">
          <span>Máquinas</span>
          <strong>{resumo.total}</strong>
        </div>
        {resumo.por_status.map((s) => (
          <div key={s.status} className={`kpi ${s.status}`}>
            <span>{s.label}</span>
            <strong>{s.total}</strong>
          </div>
        ))}
      </section>

      <section className="grid-2">
        <div className="card">
          <h2>Máquinas por centro de trabalho</h2>
          {resumo.por_setor.length === 0 ? (
            <p className="hint">Nenhum centro de trabalho cadastrado.</p>
          ) : (
            resumo.por_setor.map((s) => (
              <div key={s.setor} className="bar-row">
                <span>{s.setor}</span>
                <div className="bar">
                  <i style={{ width: `${(s.total / maiorSetor) * 100}%` }} />
                </div>
                <strong className="num">{s.total}</strong>
              </div>
            ))
          )}
          <p className="hint" style={{ marginTop: 14 }}>
            {numero(disponibilidade, 0)}% do parque está liberado para receber ordens de produção.
          </p>
        </div>

        <div className="card">
          <h2>Fora de operação</h2>
          {paradas.length === 0 ? (
            <p className="hint">Todas as máquinas estão ativas.</p>
          ) : (
            <table className="table">
              <tbody>
                {paradas.map((m) => (
                  <tr key={m.id}>
                    <td className="mono">{m.codigo}</td>
                    <td>
                      {m.nome}
                      <div className="hint">{m.setor_nome}</div>
                    </td>
                    <td>
                      <span className={`badge ${m.status}`}>{m.status_label}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p style={{ marginTop: 14 }}>
            <Link href="/maquinas" className="btn small">
              Ver todas as máquinas
            </Link>
          </p>
        </div>
      </section>
    </>
  );
}
