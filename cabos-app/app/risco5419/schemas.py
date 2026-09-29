from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, model_validator


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
    situacao: str
    data_criacao: datetime
