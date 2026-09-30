export type StatusMaquina = "ativa" | "manutencao" | "inativa";

export const STATUS_LABEL: Record<StatusMaquina, string> = {
  ativa: "Ativa",
  manutencao: "Em manutenção",
  inativa: "Inativa",
};

export type Setor = {
  id: string;
  codigo: string;
  nome: string;
  ativo: boolean;
  maquinas: number;
};

export type Maquina = {
  id: string;
  codigo: string;
  nome: string;
  setor_id: string;
  setor_nome: string;
  ciclo_padrao_seg: number;
  pecas_por_hora: number;
  status: StatusMaquina;
  status_label: string;
  recebe_ordem: boolean;
  observacao: string | null;
  atualizado_em: string;
};

export type ResumoMaquinas = {
  total: number;
  por_status: { status: StatusMaquina; label: string; total: number }[];
  por_setor: { setor: string; total: number }[];
};

export function numero(valor: number, casas = 0) {
  return valor.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
}

export function decimalInput(texto: string) {
  return Number(texto.replace(/\./g, "").replace(",", "."));
}
