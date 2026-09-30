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
  ordem: number;
  ativo: boolean;
  maquinas: number;
};

export type EtapaRoteiro = {
  sequencia: number;
  setor_id: string;
  setor_nome: string;
  operacao: string;
  tempo_padrao_seg: number | null;
};

export type Produto = {
  id: string;
  codigo: string;
  descricao: string;
  unidade: string;
  comprimento_mm: number | null;
  ativo: boolean;
  roteiro: EtapaRoteiro[];
};

export function comprimentoLabel(mm: number | null) {
  if (!mm) return null;
  return mm % 1000 === 0 ? `${mm / 1000} m` : `${numero(mm)} mm`;
}

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
