from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
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

    # Sobreposição opcional dos valores-padrão de risco/frequência tolerável (5.3: a
    # autoridade com jurisdição local tem prioridade sobre a Tabela 4). None = usar padrão da tabela.
    rt1_customizado = Column(Float, nullable=True)
    rt3_customizado = Column(Float, nullable=True)

    situacao = Column(String, nullable=False, default="rascunho")  # rascunho ou emitida
    data_criacao = Column(DateTime, default=datetime.utcnow)
    data_atualizacao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    projeto = relationship("Projeto")
    estrutura = relationship("Estrutura", uselist=False, cascade="all, delete-orphan", back_populates="analise")
    zonas = relationship("ZonaEstudo", cascade="all, delete-orphan", back_populates="analise", order_by="ZonaEstudo.id")
    linhas = relationship("LinhaEletrica", cascade="all, delete-orphan", back_populates="analise", order_by="LinhaEletrica.id")
    medidas_protecao = relationship("MedidasProtecao", uselist=False, cascade="all, delete-orphan", back_populates="analise")
    resultado = relationship("ResultadoRisco", uselist=False, cascade="all, delete-orphan", back_populates="analise")


class Estrutura(Base):
    """Dimensões e características gerais da estrutura (Anexo A e Tabela C.7)."""
    __tablename__ = "risco5419_estruturas"

    id = Column(Integer, primary_key=True)
    analise_id = Column(Integer, ForeignKey("analises_risco_5419.id"), nullable=False, unique=True)

    comprimento_m = Column(Float, nullable=False)  # L
    largura_m = Column(Float, nullable=False)      # W
    altura_m = Column(Float, nullable=False)        # H

    fator_localizacao = Column(String, nullable=False)  # chave de anexo_a_tabela_a1_cd (CD)
    tipo_construcao = Column(String, nullable=False)    # chave de anexo_c_tabela_c7_rs (rs)
    risco_explosao = Column(Boolean, nullable=False, default=False)
    # Nota da Equação 1: RC1, RM1, RW1 e RZ1 só se aplicam a estruturas com risco de explosão
    # OU onde falha de sistema interno pode imediatamente colocar em risco a vida humana.
    falha_sistema_interno_risco_vida = Column(Boolean, nullable=False, default=False)
    sistema_critico = Column(Boolean, nullable=False, default=False)  # define FT (7.3.4): 0,1/ano se crítico, 1/ano se não

    num_pessoas_total = Column(Integer, nullable=False, default=1)  # nt

    localizacao = Column(String, nullable=True)  # endereço/localização, para o memorial de cálculo (Seção 1)

    analise = relationship("AnaliseRisco", back_populates="estrutura")


class ZonaEstudo(Base):
    """Zona de estudo ZS da estrutura (6.7) — parâmetros de perdas e de pessoas."""
    __tablename__ = "risco5419_zonas"

    id = Column(Integer, primary_key=True)
    analise_id = Column(Integer, ForeignKey("analises_risco_5419.id"), nullable=False)
    nome = Column(String, nullable=False, default="Zona única")

    num_pessoas_zona = Column(Integer, nullable=False, default=1)      # nz
    tempo_pessoas_horas_ano = Column(Float, nullable=False, default=8760)  # tz

    tipo_piso = Column(String, nullable=False)             # chave anexo_c_tabela_c3_rt_piso (rt)
    providencias_incendio = Column(String, nullable=False) # chave anexo_c_tabela_c4_rp (rp)
    risco_incendio = Column(String, nullable=False)         # chave anexo_c_tabela_c5_rf (rf)
    perigo_especial = Column(String, nullable=False)        # chave anexo_c_tabela_c6_hz (hz)

    categoria_dano_fisico_lf = Column(String, nullable=False)    # chave do grupo LF em anexo_c_tabela_c2_perdas_r1
    categoria_falha_sistema_lo = Column(String, nullable=False)  # chave do grupo LO em anexo_c_tabela_c2_perdas_r1

    # R3 (opcional) — só usado se a análise incluir perda de patrimônio cultural nesta zona
    valor_patrimonio_cultural = Column(Float, nullable=True)  # cz

    # R4 detalhado (opcional) — se ausentes, R4 usa a relação simplificada (=1) da nota D.1.4
    valor_animais = Column(Float, nullable=True)              # ca
    valor_edificacao = Column(Float, nullable=True)           # cb
    valor_conteudo = Column(Float, nullable=True)             # cc
    valor_sistemas_internos = Column(Float, nullable=True)    # cs

    analise = relationship("AnaliseRisco", back_populates="zonas")


class LinhaEletrica(Base):
    """Linha elétrica (energia ou sinal) conectada à estrutura (6.4, 6.5, 6.8)."""
    __tablename__ = "risco5419_linhas"

    id = Column(Integer, primary_key=True)
    analise_id = Column(Integer, ForeignKey("analises_risco_5419.id"), nullable=False)
    tag = Column(String, nullable=False)
    tipo = Column(String, nullable=False)  # "energia" ou "sinal"
    tem_transformador_at_bt = Column(Boolean, nullable=False, default=False)  # define CT (Tabela A.3)
    tensao_suportavel_kv = Column(Float, nullable=False)  # UW do equipamento conectado a esta linha

    analise = relationship("AnaliseRisco", back_populates="linhas")
    trechos = relationship("TrechoLinha", cascade="all, delete-orphan", back_populates="linha", order_by="TrechoLinha.ordem")


class TrechoLinha(Base):
    """Trecho SL de uma linha elétrica (6.8) — cada trecho tem seus próprios fatores de exposição."""
    __tablename__ = "risco5419_trechos_linha"

    id = Column(Integer, primary_key=True)
    linha_id = Column(Integer, ForeignKey("risco5419_linhas.id"), nullable=False)
    ordem = Column(Integer, nullable=False, default=0)

    comprimento_m = Column(Float, nullable=False)  # LL
    tipo_instalacao = Column(String, nullable=False)  # chave anexo_a_tabela_a2_ci (CI)
    ambiente = Column(String, nullable=False)         # chave anexo_a_tabela_a4_ce (CE)
    categoria_blindagem = Column(String, nullable=False)  # chave anexo_b_tabela_b4_cld_cli (CLD, CLI)
    categoria_pld = Column(String, nullable=False)    # chave anexo_b_tabela_b8_pld (usada em PU, PV, PW)

    linha = relationship("LinhaEletrica", back_populates="trechos")


class MedidasProtecao(Base):
    """Medidas de proteção contra descargas atmosféricas adotadas (SPDA, DPS etc.) — Tabela 3."""
    __tablename__ = "risco5419_medidas_protecao"

    id = Column(Integer, primary_key=True)
    analise_id = Column(Integer, ForeignKey("analises_risco_5419.id"), nullable=False, unique=True)

    classe_spda = Column(String, nullable=False)  # chave anexo_b_tabela_b2_pb (PB)
    medidas_pta_json = Column(Text, nullable=False, default="[]")  # lista de chaves de anexo_b_tabela_b1_pta (produto)

    dps_coordenado = Column(String, nullable=False, default="nenhum_sistema_coordenado_dps")  # chave anexo_b_tabela_b3_pspd
    dps_classe_i = Column(String, nullable=False, default="sem_dps_classe_i")  # chave anexo_b_tabela_b7_peb
    medida_ptu = Column(String, nullable=False)     # chave anexo_b_tabela_b6_ptu

    fiacao_interna = Column(String, nullable=False)  # chave anexo_b_tabela_b5_ks3 (KS3)
    largura_malha_externa_m = Column(Float, nullable=True)  # wm1, para KS1 (None = sem blindagem espacial)
    largura_malha_interna_m = Column(Float, nullable=True)  # wm2, para KS2
    tensao_suportavel_sistema_interno_kv = Column(Float, nullable=False)  # UW do sistema interno, para KS4

    analise = relationship("AnaliseRisco", back_populates="medidas_protecao")


class ResultadoRisco(Base):
    """Resultado do último cálculo de uma análise — substituído a cada recálculo."""
    __tablename__ = "risco5419_resultados"

    id = Column(Integer, primary_key=True)
    analise_id = Column(Integer, ForeignKey("analises_risco_5419.id"), nullable=False, unique=True)

    r1 = Column(Float, nullable=True)
    rt1 = Column(Float, nullable=True)
    r1_atende = Column(Boolean, nullable=True)

    r3 = Column(Float, nullable=True)
    rt3 = Column(Float, nullable=True)
    r3_atende = Column(Boolean, nullable=True)

    r4 = Column(Float, nullable=True)
    rt4 = Column(Float, nullable=True)
    r4_atende = Column(Boolean, nullable=True)

    f_total = Column(Float, nullable=True)
    ft = Column(Float, nullable=True)
    f_atende = Column(Boolean, nullable=True)

    componentes_json = Column(Text, nullable=True)      # RA, RB, RC, RM, RU, RV, RW, RZ por risco
    memoria_calculo_json = Column(Text, nullable=True)
    data_calculo = Column(DateTime, default=datetime.utcnow)

    analise = relationship("AnaliseRisco", back_populates="resultado")
