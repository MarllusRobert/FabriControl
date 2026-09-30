export type Prioridade = "baixa" | "normal" | "alta" | "urgente";

export const PRIORIDADE_LABEL: Record<Prioridade, string> = {
  baixa: "Baixa",
  normal: "Normal",
  alta: "Alta",
  urgente: "Urgente",
};

export type EtapaOrdem = {
  sequencia: number;
  setor_id: string;
  setor_nome: string;
  operacao: string;
  status: "aguardando" | "na_fila" | "em_andamento" | "concluida";
  status_label: string;
  maquina_id: string | null;
  maquina_codigo: string | null;
  iniciada_em: string | null;
  concluida_em: string | null;
};

export type Ordem = {
  id: string;
  numero: number;
  produto_id: string;
  produto_codigo: string;
  produto_descricao: string;
  comprimento_mm: number | null;
  unidade: string;
  quantidade: number;
  prazo: string | null;
  prioridade: Prioridade;
  status: "planejada" | "liberada" | "em_producao" | "pausada" | "concluida" | "cancelada";
  status_label: string;
  atrasada: boolean;
  motivo_pausa: string | null;
  observacao: string | null;
  etapa_atual: number | null;
  total_etapas: number;
  etapas: EtapaOrdem[];
  criado_em: string;
  concluida_em: string | null;
};

export type OrdemDetalhe = Ordem & {
  eventos: { em: string; tipo: string; descricao: string; usuario_nome: string | null }[];
};

export type MaquinaResumo = { id: string; codigo: string; nome: string };

export type Coluna = {
  id: string;
  tipo: "planejadas" | "setor" | "concluidas";
  titulo: string;
  setor_id: string | null;
  maquinas: MaquinaResumo[];
  cards: Ordem[];
};

export type Kanban = { colunas: Coluna[]; atualizado_em: string };

export function etapaAtual(o: Ordem): EtapaOrdem | null {
  return o.etapa_atual ? o.etapas[o.etapa_atual - 1] : null;
}

/** Coluna para onde o cartão pode ir: a da próxima etapa (ou Concluídas, se for a última). */
export function destinoPermitido(o: Ordem): string | null {
  if (o.status === "planejada") return o.etapas[0]?.setor_id ?? null;
  if (o.status !== "liberada" && o.status !== "em_producao") return null;
  const atual = etapaAtual(o);
  if (!atual) return null;
  const proxima = o.etapas.find((e) => e.sequencia === atual.sequencia + 1);
  return proxima ? proxima.setor_id : "concluidas";
}

export function dataCurta(iso: string | null) {
  if (!iso) return "";
  const [a, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${a.slice(2)}`;
}

export function dataHora(iso: string) {
  return new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}
