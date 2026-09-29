from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database import Base


class MunicipioNG(Base):
    """Densidade de descargas atmosféricas NG por município (Anexo F da NBR 5419-2)."""
    __tablename__ = "municipios_ng"
    __table_args__ = (UniqueConstraint("municipio", "uf", name="uq_municipio_ng_municipio_uf"),)

    id = Column(Integer, primary_key=True)
    codigo_ibge = Column(String, nullable=True)
    municipio = Column(String, nullable=False, index=True)
    uf = Column(String(2), nullable=False, index=True)
    ng = Column(Float, nullable=False)
    referencia = Column(String, nullable=False)
    importado_em = Column(DateTime, default=datetime.utcnow)


class AnaliseRisco(Base):
    """Análise de risco de descargas atmosféricas (NBR 5419-2) vinculada a um projeto."""
    __tablename__ = "analises_risco_5419"

    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer, ForeignKey("projetos.id"), nullable=False)
    tag = Column(String, nullable=False)
    edicao_norma = Column(String, nullable=False, default="Projeto de Revisão ABNT NBR 5419-2, JUL/2025")

    # Snapshot do NG usado nesta análise (congelado no momento da criação/edição,
    # para que uma futura reimportação da tabela municipios_ng não altere análises já emitidas).
    ng_modo = Column(String, nullable=False)  # "manual" ou "municipio"
    ng_valor = Column(Float, nullable=False)
    ng_municipio = Column(String, nullable=True)
    ng_uf = Column(String(2), nullable=True)
    ng_fonte_justificativa = Column(String, nullable=True)  # usado no modo manual
    ng_referencia = Column(String, nullable=False)

    situacao = Column(String, nullable=False, default="rascunho")  # rascunho ou emitida
    data_criacao = Column(DateTime, default=datetime.utcnow)
    data_atualizacao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    projeto = relationship("Projeto")
