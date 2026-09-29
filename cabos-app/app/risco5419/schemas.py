from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, model_validator, Field


class MunicipioNGOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    municipio: str
    uf: str
    ng: float


class AnaliseRiscoCreate(BaseModel):
    tag: str
    ng_modo: str  # "manual" ou "municipio"
    ng_valor_manual: Optional[float] = None
    ng_fonte_manual: Optional[str] = None
    ng_municipio: Optional[str] = None
    ng_uf: Optional[str] = None

    @model_validator(mode="after")
    def valida_modo(self):
        if self.ng_modo not in ("manual", "municipio"):
            raise ValueError('ng_modo deve ser "manual" ou "municipio"')
        if self.ng_modo == "manual" and not self.ng_valor_manual:
            raise ValueError("Informe ng_valor_manual para o modo manual.")
        if self.ng_modo == "municipio" and not (self.ng_municipio and self.ng_uf):
            raise ValueError("Informe ng_municipio e ng_uf para o modo município.")
        return self


class AnaliseRiscoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    projeto_id: int
    tag: str
    edicao_norma: str
    ng_modo: str
    ng_valor: float
    ng_municipio: Optional[str] = None
    ng_uf: Optional[str] = None
    ng_fonte_justificativa: Optional[str] = None
    ng_referencia: str
    rt1_customizado: Optional[float] = None
    rt3_customizado: Optional[float] = None
    situacao: str
    data_criacao: datetime


class EstruturaIn(BaseModel):
    comprimento_m: float = Field(gt=0)
    largura_m: float = Field(gt=0)
    altura_m: float = Field(gt=0)
    fator_localizacao: str
    tipo_construcao: str
    localizacao: Optional[str] = None
    risco_explosao: bool = False
    falha_sistema_interno_risco_vida: bool = False
    sistema_critico: bool = False
    num_pessoas_total: int = Field(gt=0)


class EstruturaOut(EstruturaIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ZonaEstudoIn(BaseModel):
    nome: str = "Zona única"
    num_pessoas_zona: int = Field(ge=0)
    tempo_pessoas_horas_ano: float = Field(ge=0, le=8760)
    tipo_piso: str
    providencias_incendio: str
    risco_incendio: str
    perigo_especial: str
    categoria_dano_fisico_lf: str
    categoria_falha_sistema_lo: str
    valor_patrimonio_cultural: Optional[float] = None
    valor_animais: Optional[float] = None
    valor_edificacao: Optional[float] = None
    valor_conteudo: Optional[float] = None
    valor_sistemas_internos: Optional[float] = None


class ZonaEstudoOut(ZonaEstudoIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class TrechoLinhaIn(BaseModel):
    comprimento_m: float = Field(gt=0)
    tipo_instalacao: str
    ambiente: str
    categoria_blindagem: str
    categoria_pld: str


class TrechoLinhaOut(TrechoLinhaIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ordem: int


class LinhaEletricaIn(BaseModel):
    tag: str
    tipo: str  # "energia" ou "sinal"
    tem_transformador_at_bt: bool = False
    tensao_suportavel_kv: float = Field(gt=0)
    trechos: list[TrechoLinhaIn] = []

    @model_validator(mode="after")
    def valida_tipo(self):
        if self.tipo not in ("energia", "sinal"):
            raise ValueError('tipo deve ser "energia" ou "sinal"')
        if not self.trechos:
            raise ValueError("Informe ao menos um trecho para a linha.")
        return self


class LinhaEletricaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tag: str
    tipo: str
    tem_transformador_at_bt: bool
    tensao_suportavel_kv: float
    trechos: list[TrechoLinhaOut] = []


class MedidasProtecaoIn(BaseModel):
    classe_spda: str
    medidas_pta: list[str] = []
    dps_coordenado: str = "nenhum_sistema_coordenado_dps"
    dps_classe_i: str = "sem_dps_classe_i"
    medida_ptu: str
    fiacao_interna: str
    largura_malha_externa_m: Optional[float] = None
    largura_malha_interna_m: Optional[float] = None
    tensao_suportavel_sistema_interno_kv: float = Field(gt=0)


class MedidasProtecaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    classe_spda: str
    dps_coordenado: str
    dps_classe_i: str
    medida_ptu: str
    fiacao_interna: str
    largura_malha_externa_m: Optional[float] = None
    largura_malha_interna_m: Optional[float] = None
    tensao_suportavel_sistema_interno_kv: float
    medidas_pta: list[str] = []

    @model_validator(mode="before")
    @classmethod
    def carrega_medidas_pta(cls, obj):
        import json
        if hasattr(obj, "medidas_pta_json"):
            data = {c: getattr(obj, c) for c in
                     ["id", "classe_spda", "dps_coordenado", "dps_classe_i", "medida_ptu", "fiacao_interna",
                      "largura_malha_externa_m", "largura_malha_interna_m", "tensao_suportavel_sistema_interno_kv"]}
            data["medidas_pta"] = json.loads(obj.medidas_pta_json or "[]")
            return data
        return obj


class ResultadoRiscoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    r1: Optional[float] = None
    rt1: Optional[float] = None
    r1_atende: Optional[bool] = None
    r3: Optional[float] = None
    rt3: Optional[float] = None
    r3_atende: Optional[bool] = None
    f_total: Optional[float] = None
    ft: Optional[float] = None
    f_atende: Optional[bool] = None
    data_calculo: datetime
