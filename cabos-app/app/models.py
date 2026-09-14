from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from .database import Base


class Projeto(Base):
    __tablename__ = "projetos"

    id = Column(Integer, primary_key=True)
    numero_projeto = Column(String, unique=True, nullable=False, index=True)
    nome_projeto = Column(String, nullable=False)
    cliente = Column(String, default="")
    descricao = Column(Text, default="")
    revisao = Column(String, default="Rev. 0")
    data_criacao = Column(DateTime, default=datetime.utcnow)

    equipamentos = relationship("Equipamento", cascade="all, delete-orphan", back_populates="projeto")
    eletrodutos_bandejas = relationship("EletrodutoBandeja", cascade="all, delete-orphan", back_populates="projeto")
    cabos = relationship("Cabo", cascade="all, delete-orphan", back_populates="projeto")
    paineis = relationship("PainelTransformador", cascade="all, delete-orphan", back_populates="projeto")


class Equipamento(Base):
    __tablename__ = "equipamentos"
    __table_args__ = (UniqueConstraint("projeto_id", "tag", name="uq_equipamento_tag_projeto"),)

    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer, ForeignKey("projetos.id"), nullable=False)
    tag = Column(String, nullable=False)
    descricao = Column(String, default="")
    tipo_carga = Column(String, default="")

    # Potência informada pelo usuário: um único valor + unidade (kW, W, CV, HP, kVA)
    potencia_valor = Column(Float, nullable=True)
    potencia_unidade = Column(String, default="kW")
    rendimento = Column(Float, default=1.0)  # η — rendimento do equipamento (0–1)

    tensao_v = Column(Float, nullable=False, default=380)
    num_fases = Column(Integer, nullable=False, default=3)   # 1, 2 ou 3
    possui_neutro = Column(Boolean, default=False)
    possui_terra = Column(Boolean, default=True)
    fator_potencia = Column(Float, nullable=False, default=0.92)
    fator_demanda = Column(Float, nullable=False, default=1.0)
    painel_transformador_tag = Column(String, default="")
    dimensoes = Column(String, default="")
    peso_kg = Column(Float, nullable=True)
    folha_dados_numero = Column(String, default="")
    diagrama_eletrico_numero = Column(String, default="")
    fornecedor = Column(String, default="")
    observacao = Column(Text, default="")

    # Calculados
    potencia_nominal_kw = Column(Float, nullable=True)        # potência informada convertida para kW (no eixo / nominal)
    potencia_ativa_calc_kw = Column(Float, nullable=True)     # P elétrica absorvida = Pn / η
    potencia_aparente_calc_kva = Column(Float, nullable=True) # S = P / cosφ
    potencia_reativa_calc_kvar = Column(Float, nullable=True) # Q = P × tgφ
    corrente_nominal_a = Column(Float, nullable=True)
    potencia_demanda_kw = Column(Float, nullable=True)        # Pd = P × FD
    potencia_demanda_reativa_kvar = Column(Float, nullable=True)

    projeto = relationship("Projeto", back_populates="equipamentos")


class CatalogoInfraestrutura(Base):
    __tablename__ = "catalogo_infraestrutura_eletrica"

    id = Column(Integer, primary_key=True)
    fabricante = Column(String, default="Elecon")
    linha_produto = Column(String, nullable=False)
    tipo = Column(String, nullable=False)  # eletroduto, eletrocalha, perfilado, leito
    diametro_nominal_pol = Column(String, default="")
    diametro_nominal_mm = Column(Float, nullable=True)
    parede_mm = Column(Float, nullable=True)
    diametro_externo_mm = Column(Float, nullable=True)
    diametro_interno_mm = Column(Float, nullable=True)
    area_util_mm2 = Column(Float, nullable=True)
    largura_nominal_mm = Column(Float, nullable=True)
    altura_nominal_mm = Column(Float, nullable=True)
    largura_util_mm = Column(Float, nullable=True)
    fonte_datasheet = Column(String, default="Catálogo Elecon 2018")
    customizado = Column(Boolean, default=False)


class EletrodutoBandeja(Base):
    __tablename__ = "eletrodutos_bandejas"
    __table_args__ = (UniqueConstraint("projeto_id", "tag", name="uq_infra_tag_projeto"),)

    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer, ForeignKey("projetos.id"), nullable=False)
    tag = Column(String, nullable=False)
    tipo = Column(String, nullable=False)  # eletroduto, eletrocalha, perfilado, leito
    catalogo_infraestrutura_id = Column(Integer, ForeignKey("catalogo_infraestrutura_eletrica.id"), nullable=True)
    no_origem = Column(String, default="")
    no_destino = Column(String, default="")
    comprimento_m = Column(Float, nullable=False, default=0)
    dimensao_definida_manualmente = Column(Boolean, default=False)

    diametro_nominal_mm = Column(Float, nullable=True)
    parede_mm = Column(Float, nullable=True)
    area_util_mm2 = Column(Float, nullable=True)
    largura_util_mm = Column(Float, nullable=True)

    dimensao_sugerida_id = Column(Integer, ForeignKey("catalogo_infraestrutura_eletrica.id"), nullable=True)

    projeto = relationship("Projeto", back_populates="eletrodutos_bandejas")
    catalogo_item = relationship("CatalogoInfraestrutura", foreign_keys=[catalogo_infraestrutura_id])
    catalogo_sugerido = relationship("CatalogoInfraestrutura", foreign_keys=[dimensao_sugerida_id])


class CatalogoCabo(Base):
    __tablename__ = "catalogo_cabos"

    id = Column(Integer, primary_key=True)
    fabricante = Column(String, default="Prysmian")
    linha_produto = Column(String, nullable=False)
    aplicacao = Column(String, default="")
    material_condutor = Column(String, default="cobre")
    tipo_isolacao = Column(String, nullable=False)  # PVC, EPR, XLPE, HEPR...
    possui_blindagem = Column(Boolean, default=False)
    tensao_isolamento = Column(String, default="")
    construcao_basica = Column(String, default="")
    num_condutores = Column(Integer, nullable=False, default=1)
    secao_nominal_mm2 = Column(Float, nullable=False)
    diametro_externo_nominal_mm = Column(Float, nullable=False)
    peso_kg_km = Column(Float, nullable=True)
    resistencia_condutor_20c_ohm_km = Column(Float, nullable=True)
    reatancia_ohm_km = Column(Float, nullable=True)
    capacidade_conducao_a = Column(Float, nullable=True)
    norma_referencia = Column(String, default="")
    fonte_datasheet = Column(String, default="")

    @property
    def area_secao_mm2(self):
        import math
        return math.pi * (self.diametro_externo_nominal_mm / 2) ** 2


class Cabo(Base):
    __tablename__ = "cabos"
    __table_args__ = (UniqueConstraint("projeto_id", "tag", name="uq_cabo_tag_projeto"),)

    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer, ForeignKey("projetos.id"), nullable=False)
    tag = Column(String, nullable=False)

    # Origem (De) e destino (Para): cada ponta pode ser um equipamento OU um painel/transformador.
    # A carga alimentada pelo cabo é sempre a ponta "Para".
    equipamento_de_id = Column(Integer, ForeignKey("equipamentos.id"), nullable=True)
    painel_de_id = Column(Integer, ForeignKey("paineis_transformadores.id"), nullable=True)
    equipamento_para_id = Column(Integer, ForeignKey("equipamentos.id"), nullable=True)
    painel_para_id = Column(Integer, ForeignKey("paineis_transformadores.id"), nullable=True)

    tipo_isolacao = Column(String, nullable=False, default="PVC")
    metodo_instalacao = Column(String, nullable=False, default="B1")
    temperatura_ambiente_c = Column(Float, default=30.0)
    fator_agrupamento_manual = Column(Float, nullable=True)  # se informado, sobrescreve o cálculo automático
    queda_tensao_admissivel_pct = Column(Float, nullable=False, default=3.0)
    num_cabos_paralelo = Column(Integer, nullable=False, default=1)
    catalogo_cabo_id = Column(Integer, ForeignKey("catalogo_cabos.id"), nullable=True)
    secao_definida_manualmente = Column(Boolean, default=False)
    observacao = Column(Text, default="")

    # Calculados
    tensao_v = Column(Float, nullable=True)
    num_fases = Column(Integer, nullable=True)
    num_condutores_calc = Column(Integer, nullable=True)      # fases + neutro + terra
    num_condutores_carregados = Column(Integer, nullable=True)
    tipo_construcao = Column(String, nullable=True)           # 'multipolar' (≤35mm²) ou 'unipolar' (≥50mm²)
    num_cabos_fisicos = Column(Integer, nullable=True)        # nº de cabos físicos que ocupam o eletroduto/bandeja
    corrente_projeto_a = Column(Float, nullable=True)
    fator_temperatura_calc = Column(Float, nullable=True)
    fator_agrupamento_calc = Column(Float, nullable=True)
    secao_por_capacidade_mm2 = Column(Float, nullable=True)
    secao_por_queda_mm2 = Column(Float, nullable=True)
    secao_sugerida_mm2 = Column(Float, nullable=True)
    secao_mm2 = Column(Float, nullable=True)
    queda_tensao_calc_pct = Column(Float, nullable=True)
    distancia_total_m = Column(Float, nullable=True)
    diametro_externo_mm = Column(Float, nullable=True)
    area_secao_transversal_mm2 = Column(Float, nullable=True)
    memoria_calculo_json = Column(Text, nullable=True)
    alerta_secao_insuficiente = Column(Boolean, default=False)

    projeto = relationship("Projeto", back_populates="cabos")
    equipamento_de = relationship("Equipamento", foreign_keys=[equipamento_de_id])
    equipamento_para = relationship("Equipamento", foreign_keys=[equipamento_para_id])
    painel_de = relationship("PainelTransformador", foreign_keys=[painel_de_id])
    painel_para = relationship("PainelTransformador", foreign_keys=[painel_para_id])
    catalogo_cabo = relationship("CatalogoCabo", foreign_keys=[catalogo_cabo_id])
    trechos = relationship("CaboTrecho", cascade="all, delete-orphan", back_populates="cabo", order_by="CaboTrecho.ordem")

    @property
    def de_tag(self):
        if self.painel_de:
            return self.painel_de.tag
        return self.equipamento_de.tag if self.equipamento_de else ""

    @property
    def para_tag(self):
        if self.painel_para:
            return self.painel_para.tag
        return self.equipamento_para.tag if self.equipamento_para else ""


class CaboTrecho(Base):
    __tablename__ = "cabo_trechos"

    id = Column(Integer, primary_key=True)
    cabo_id = Column(Integer, ForeignKey("cabos.id"), nullable=False)
    eletroduto_bandeja_id = Column(Integer, ForeignKey("eletrodutos_bandejas.id"), nullable=False)
    ordem = Column(Integer, nullable=False, default=0)

    cabo = relationship("Cabo", back_populates="trechos")
    eletroduto_bandeja = relationship("EletrodutoBandeja")


class PainelTransformador(Base):
    __tablename__ = "paineis_transformadores"
    __table_args__ = (UniqueConstraint("projeto_id", "tag", name="uq_painel_tag_projeto"),)

    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer, ForeignKey("projetos.id"), nullable=False)
    tag = Column(String, nullable=False)
    tipo = Column(String, default="painel")  # painel, quadro, transformador, CCM
    tensao_v = Column(Float, nullable=False, default=380)
    num_fases = Column(Integer, default=3)
    fator_diversidade = Column(Float, nullable=False, default=1.0)
    # TAG do painel/transformador a montante (que alimenta este). Vazio = painel TOP/geral.
    painel_alimentador_tag = Column(String, default="")

    # Calculados (somando equipamentos diretos + painéis a jusante)
    potencia_instalada_kw = Column(Float, nullable=True)
    potencia_reativa_instalada_kvar = Column(Float, nullable=True)
    demanda_total_kw = Column(Float, nullable=True)
    demanda_reativa_kvar = Column(Float, nullable=True)
    demanda_aparente_kva = Column(Float, nullable=True)
    fator_potencia_calc = Column(Float, nullable=True)
    corrente_total_a = Column(Float, nullable=True)
    corrente_instalada_a = Column(Float, nullable=True)  # soma das correntes nominais a jusante

    projeto = relationship("Projeto", back_populates="paineis")


# ---- Tabelas normativas (globais, somente leitura / editáveis via importação) ----

class TabCapacidadeConducao(Base):
    __tablename__ = "tab_capacidade_conducao"

    id = Column(Integer, primary_key=True)
    isolacao_grupo = Column(String, nullable=False)  # 'PVC' ou 'EPR_XLPE'
    metodo_instalacao = Column(String, nullable=False)  # A1, A2, B1, B2, C, D, E, F, G
    num_condutores_carregados = Column(Integer, nullable=False)  # 2 ou 3
    secao_mm2 = Column(Float, nullable=False)
    capacidade_a = Column(Float, nullable=False)


class TabFatorTemperatura(Base):
    __tablename__ = "tab_fator_temperatura"

    id = Column(Integer, primary_key=True)
    isolacao_grupo = Column(String, nullable=False)
    temperatura_c = Column(Float, nullable=False)
    fator = Column(Float, nullable=False)


class TabFatorAgrupamento(Base):
    __tablename__ = "tab_fator_agrupamento"

    id = Column(Integer, primary_key=True)
    num_circuitos = Column(Integer, nullable=False)
    fator = Column(Float, nullable=False)


class TabResistividadeCondutor(Base):
    __tablename__ = "tab_resistividade_condutor"

    id = Column(Integer, primary_key=True)
    secao_mm2 = Column(Float, nullable=False)
    resistencia_ohm_km = Column(Float, nullable=False)


class TabLimiteOcupacaoEletroduto(Base):
    __tablename__ = "tab_limite_ocupacao_eletroduto"

    id = Column(Integer, primary_key=True)
    num_cabos = Column(String, nullable=False)  # "1", "2", "3+"
    taxa_max_pct = Column(Float, nullable=False)


class TabLimiteOcupacaoBandeja(Base):
    __tablename__ = "tab_limite_ocupacao_bandeja"

    id = Column(Integer, primary_key=True)
    criterio = Column(String, nullable=False, default="camada_unica")
    folga_percentual = Column(Float, nullable=False, default=0.0)
    espacamento_minimo_mm = Column(Float, nullable=False, default=0.0)
