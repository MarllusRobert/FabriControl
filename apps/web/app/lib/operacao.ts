import { Maquina } from "./cadastros";

export type EtapaFila = {
  ordem_id: string;
  ordem_numero: number;
  ordem_status: string;
  motivo_pausa: string | null;
  produto_codigo: string;
  produto_descricao: string;
  unidade: string;
  quantidade: number;
  prioridade: string;
  prazo: string | null;
  atrasada: boolean;
  sequencia: number;
  total_etapas: number;
  operacao: string;
  proximo_setor: string | null;
  status: string;
  carga_min: number;
  iniciada_em: string | null;
  operador_nome: string | null;
};

export type PainelMaquina = {
  maquina: Maquina;
  atual: EtapaFila | null;
  fila: EtapaFila[];
  atualizado_em: string;
};

export type OperadorSessao = { id: string; nome: string; matricula: string };

export function horasLabel(minutos: number) {
  if (minutos < 60) return `${Math.round(minutos)} min`;
  const h = Math.floor(minutos / 60);
  const m = Math.round(minutos % 60);
  return m ? `${h}h${String(m).padStart(2, "0")}` : `${h}h`;
}

export function hora(iso: string) {
  return new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}
