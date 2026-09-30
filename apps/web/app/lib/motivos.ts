export type TipoParada = "planejada" | "nao_planejada";

export type MotivoParada = {
  id: string;
  codigo: string;
  descricao: string;
  tipo: TipoParada;
  tipo_label: string;
  planejada: boolean;
  ativo: boolean;
};

export type MotivoRefugo = {
  id: string;
  codigo: string;
  descricao: string;
  categoria: string;
  categoria_label: string;
  ativo: boolean;
};

export type Opcao = { valor: string; label: string };

export type OpcoesMotivos = { tipos_parada: Opcao[]; categorias_refugo: Opcao[] };
