export type Turno = {
  id: string;
  codigo: string;
  nome: string;
  inicio: string;
  fim: string;
  duracao_min: number;
  vira_meia_noite: boolean;
  ativo: boolean;
  operadores: number;
};

export type Operador = {
  id: string;
  matricula: string;
  nome: string;
  turno_id: string;
  turno_nome: string;
  turno_horario: string;
  setor_id: string;
  setor_nome: string;
  ativo: boolean;
};

export function duracaoLabel(minutos: number) {
  const h = Math.floor(minutos / 60);
  const m = minutos % 60;
  return m ? `${h}h${String(m).padStart(2, "0")}` : `${h}h`;
}
