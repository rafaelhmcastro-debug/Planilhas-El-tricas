# Dados normativos — NBR 5419-2:2026

**Status: RASCUNHO aguardando revisão do engenheiro.**

Estes arquivos foram montados sem acesso ao texto da edição 2026 (publicada
10/03/2026, após o corte de conhecimento do assistente). A estrutura segue a
metodologia consolidada de avaliação de risco (linhagem IEC 62305-2 / NBR
5419-2:2015), usando os símbolos que o engenheiro confirmou existirem na
edição 2026 (NG, AD, AM, AL, AI, PTA, PB, LT, LF, LO, rt, rp, rf, rs, hz).

**Nenhum valor numérico foi preenchido.** Todo campo `"valor"` está `null` e
deve ser preenchido pelo engenheiro a partir da cópia licenciada da norma.
O campo `"referencia"` também está `null` nos arquivos marcados como
`"status": "AGUARDA_CONFIRMACAO_SIMBOLO"` — nesses casos nem o nome do
símbolo está confirmado, então não escrevi um número de tabela.

## Contrato de cada entrada

```json
{
  "chave": "identificador_interno_estavel",
  "descricao": "o que a grandeza representa",
  "valor": null,
  "referencia": null,
  "unidade": "opcional"
}
```

`tabelas.py` (Fase 1) vai validar que nenhum `"valor"` usado em um cálculo é
`null`, apontando a chave e a `referencia` esperada no erro.

## Arquivos e o que falta preencher

| Arquivo | Símbolo(s) | Confirmado por você? | O que fazer |
|---|---|---|---|
| `01_pb_classe_spda.json` | PB | sim | preencher `valor` e `referencia` (nº da tabela 2026) por classe de SPDA |
| `02_pta_protecao_choque_estrutura.json` | PTA | sim | idem, por medida de proteção contra choque |
| `04_perdas_referencia_lt_lf_lo.json` | LT, LF, LO | sim | idem, valores típicos de perda por tipo de zona/dano |
| `05_fatores_reducao_perda.json` | rt, rp, rf, rs, hz | sim | idem, por medida/tipo de piso/risco |
| `06_limites_toleraveis.json` | RT1, RT3 | parcial (risco existe; símbolo do limite não confirmado) | confirmar nome do símbolo do limite tolerável e preencher valor |
| `03_fatores_localizacao_ambiente_linha.json` | CD, CE, CI, CT (tentativo) | **não** | confirmar se esses símbolos existem na edição 2026 e corrigir nomes se necessário, depois preencher |
| `07_anexo_d_valores_economicos_r4.json` | ca, cb, cc, cz (tentativo) | **não** | mesma ressalva acima |
| `08_secao7_frequencia_danos_f.json` | — | **não, estrutura desconhecida** | ver pergunta aberta na resposta da Fase 0 — preciso que você descreva a equação/tabelas antes de eu desenhar este arquivo |

Arquivos marcados "tentativo" usam nomenclatura da edição 2015/IEC 62305-2
como placeholder. Se a edição 2026 renomeou ou reestruturou esses fatores,
me avise em vez de editar o JSON diretamente — a estrutura de chaves pode
precisar mudar, não só os valores.
