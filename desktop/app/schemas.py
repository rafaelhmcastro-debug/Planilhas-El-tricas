import re
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, field_validator

NUMERO_PROJETO_RE = re.compile(r"^\d{4}-\d{2}-\d{4}$")

UNIDADES_POTENCIA = ("kW", "W", "CV", "HP", "kVA")
METODOS_INSTALACAO = ("A1", "A2", "B1", "B2", "C", "D", "E", "F", "G")


class ProjetoBase(BaseModel):
    numero_projeto: str
    nome_projeto: str
    cliente: Optional[str] = ""
    descricao: Optional[str] = ""
    revisao: Optional[str] = "Rev. 0"

    @field_validator("numero_projeto")
    @classmethod
    def valida_numero(cls, v):
        if not NUMERO_PROJETO_RE.match(v or ""):
            raise ValueError('Número do projeto deve seguir o formato "9999-99-9999"')
        return v


class ProjetoCreate(ProjetoBase):
    pass


class ProjetoOut(ProjetoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    data_criacao: datetime


class EquipamentoBase(BaseModel):
    tag: str
    descricao: Optional[str] = ""
    tipo_carga: Optional[str] = ""
    potencia_valor: float
    potencia_unidade: str = "kW"
    rendimento: float = 1.0
    tensao_v: float
    num_fases: int = 3
    possui_neutro: bool = False
    possui_terra: bool = True
    fator_potencia: float = 0.92
    fator_demanda: float = 1.0
    painel_transformador_tag: Optional[str] = ""
    dimensoes: Optional[str] = ""
    peso_kg: Optional[float] = None
    folha_dados_numero: Optional[str] = ""
    diagrama_eletrico_numero: Optional[str] = ""
    fornecedor: Optional[str] = ""
    observacao: Optional[str] = ""

    @field_validator("potencia_unidade")
    @classmethod
    def valida_unidade(cls, v):
        if v not in UNIDADES_POTENCIA:
            raise ValueError(f"Unidade de potência inválida. Use uma de: {', '.join(UNIDADES_POTENCIA)}")
        return v

    @field_validator("num_fases")
    @classmethod
    def valida_fases(cls, v):
        if v not in (1, 2, 3):
            raise ValueError("Número de fases deve ser 1, 2 ou 3")
        return v

    @field_validator("rendimento", "fator_potencia")
    @classmethod
    def valida_0_1(cls, v):
        if v is None or v <= 0 or v > 1:
            raise ValueError("Valor deve estar entre 0 (exclusivo) e 1")
        return v


class EquipamentoCreate(EquipamentoBase):
    pass


class EquipamentoOut(EquipamentoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    projeto_id: int
    potencia_nominal_kw: Optional[float] = None
    potencia_ativa_calc_kw: Optional[float] = None
    potencia_aparente_calc_kva: Optional[float] = None
    potencia_reativa_calc_kvar: Optional[float] = None
    corrente_nominal_a: Optional[float] = None
    potencia_demanda_kw: Optional[float] = None
    potencia_demanda_reativa_kvar: Optional[float] = None


class InfraBase(BaseModel):
    tag: str
    tipo: str
    catalogo_infraestrutura_id: Optional[int] = None
    no_origem: Optional[str] = ""
    no_destino: Optional[str] = ""
    comprimento_m: float = 0
    dimensao_definida_manualmente: bool = False


class InfraCreate(InfraBase):
    pass


class InfraOut(InfraBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    projeto_id: int
    diametro_nominal_mm: Optional[float] = None
    parede_mm: Optional[float] = None
    area_util_mm2: Optional[float] = None
    largura_util_mm: Optional[float] = None
    dimensao_sugerida_id: Optional[int] = None


class CaboTrechoIn(BaseModel):
    eletroduto_bandeja_id: int
    ordem: int


class CaboBase(BaseModel):
    tag: str
    equipamento_de_id: Optional[int] = None
    painel_de_id: Optional[int] = None
    equipamento_para_id: Optional[int] = None
    painel_para_id: Optional[int] = None
    tipo_isolacao: str = "PVC"
    metodo_instalacao: str = "B1"
    temperatura_ambiente_c: float = 30.0
    fator_agrupamento_manual: Optional[float] = None
    queda_tensao_admissivel_pct: float = 3.0
    num_cabos_paralelo: int = 1
    catalogo_cabo_id: Optional[int] = None
    observacao: Optional[str] = ""

    @field_validator("metodo_instalacao")
    @classmethod
    def valida_metodo(cls, v):
        if v not in METODOS_INSTALACAO:
            raise ValueError(f"Método de instalação inválido. Use um de: {', '.join(METODOS_INSTALACAO)}")
        return v


class CaboCreate(CaboBase):
    trechos: List[CaboTrechoIn] = []


class CaboOut(CaboBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    projeto_id: int
    secao_definida_manualmente: bool
    de_tag: str = ""
    para_tag: str = ""
    tensao_v: Optional[float] = None
    num_fases: Optional[int] = None
    num_condutores_calc: Optional[int] = None
    num_condutores_carregados: Optional[int] = None
    tipo_construcao: Optional[str] = None
    num_cabos_fisicos: Optional[int] = None
    corrente_projeto_a: Optional[float] = None
    fator_temperatura_calc: Optional[float] = None
    fator_agrupamento_calc: Optional[float] = None
    secao_por_capacidade_mm2: Optional[float] = None
    secao_por_queda_mm2: Optional[float] = None
    secao_sugerida_mm2: Optional[float] = None
    secao_mm2: Optional[float] = None
    queda_tensao_calc_pct: Optional[float] = None
    distancia_total_m: Optional[float] = None
    diametro_externo_mm: Optional[float] = None
    area_secao_transversal_mm2: Optional[float] = None
    alerta_secao_insuficiente: bool = False


class PainelCreate(BaseModel):
    tag: str
    tipo: str = "painel"
    tensao_v: float = 380
    num_fases: int = 3
    fator_diversidade: float = 1.0
    painel_alimentador_tag: Optional[str] = ""


class PainelUpdate(BaseModel):
    tag: Optional[str] = None
    tipo: Optional[str] = None
    tensao_v: Optional[float] = None
    num_fases: Optional[int] = None
    fator_diversidade: Optional[float] = None
    painel_alimentador_tag: Optional[str] = None


class PainelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    projeto_id: int
    tag: str
    tipo: str
    tensao_v: float
    num_fases: Optional[int] = 3
    fator_diversidade: float
    painel_alimentador_tag: Optional[str] = ""
    potencia_instalada_kw: Optional[float] = None
    potencia_reativa_instalada_kvar: Optional[float] = None
    demanda_total_kw: Optional[float] = None
    demanda_reativa_kvar: Optional[float] = None
    demanda_aparente_kva: Optional[float] = None
    fator_potencia_calc: Optional[float] = None
    corrente_total_a: Optional[float] = None
    corrente_instalada_a: Optional[float] = None


class CatalogoCaboIn(BaseModel):
    fabricante: str = "Prysmian"
    linha_produto: str
    aplicacao: Optional[str] = ""
    material_condutor: str = "cobre"
    tipo_isolacao: str
    possui_blindagem: bool = False
    tensao_isolamento: Optional[str] = ""
    construcao_basica: Optional[str] = ""
    num_condutores: int = 1
    secao_nominal_mm2: float
    diametro_externo_nominal_mm: float
    peso_kg_km: Optional[float] = None
    resistencia_condutor_20c_ohm_km: Optional[float] = None
    reatancia_ohm_km: Optional[float] = None
    capacidade_conducao_a: Optional[float] = None
    norma_referencia: Optional[str] = ""
    fonte_datasheet: Optional[str] = "Cadastro manual"
