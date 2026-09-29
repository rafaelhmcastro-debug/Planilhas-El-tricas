# Dados normativos — NBR 5419-2

**Fonte:** Projeto de Revisão ABNT NBR 5419-2, JUL/2025 ("Projeto em Consulta
Nacional", marcado "NÃO TEM VALOR NORMATIVO" em todas as páginas — não é a
edição final publicada em 10/03/2026). Por instrução explícita do engenheiro
responsável, os valores deste rascunho são tratados como equivalentes aos da
edição final. Cada entrada abaixo registra a tabela exata de onde veio, para
que uma eventual divergência com o texto final seja fácil de auditar e corrigir.

Todos os arquivos seguem o contrato: `chave`, `descricao`, `valor`, `referencia`
(mais campos específicos quando a tabela é bidimensional). Nenhum valor foi
digitado de memória — todos vieram da extração de texto do PDF fornecido,
tabela por tabela, com conferência manual dos números antes de gravar.

## Arquivos (extraídos e preenchidos)

| Arquivo | Símbolo(s) | Tabela da norma |
|---|---|---|
| `tabela_04_risco_toleravel.json` | RT (R1, R3, R4) | Tabela 4, Anexo D §D.1.2 |
| `anexo_a_tabela_a1_cd.json` | CD | Tabela A.1 |
| `anexo_a_tabela_a2_ci.json` | CI | Tabela A.2 |
| `anexo_a_tabela_a3_ct.json` | CT | Tabela A.3 |
| `anexo_a_tabela_a4_ce.json` | CE | Tabela A.4 |
| `anexo_b_tabela_b1_pta.json` | PTA | Tabela B.1 |
| `anexo_b_tabela_b2_pb.json` | PB | Tabela B.2 |
| `anexo_b_tabela_b3_pspd.json` | PSPD | Tabela B.3 (1 faixa sem valor fechado — ver `nota`) |
| `anexo_b_tabela_b4_cld_cli.json` | CLD, CLI | Tabela B.4 |
| `anexo_b_tabela_b5_ks3.json` | KS3 | Tabela B.5 |
| `anexo_b_tabela_b6_ptu.json` | PTU | Tabela B.6 |
| `anexo_b_tabela_b7_peb.json` | PEB | Tabela B.7 (1 faixa sem valor fechado — ver `nota`) |
| `anexo_b_tabela_b8_pld.json` | PLD | Tabela B.8 (2D: tipo de linha × UW) |
| `anexo_b_tabela_b9_pli.json` | PLI | Tabela B.9 (2D: tipo de linha × UW) |
| `anexo_c_tabela_c2_perdas_r1.json` | LT, LF, LO | Tabela C.2 |
| `anexo_c_tabela_c3_rt_piso.json` | rt | Tabela C.3 |
| `anexo_c_tabela_c4_rp.json` | rp | Tabela C.4 |
| `anexo_c_tabela_c5_rf.json` | rf | Tabela C.5 |
| `anexo_c_tabela_c6_hz.json` | hz | Tabela C.6 |
| `anexo_c_tabela_c7_rs.json` | rs | Tabela C.7 |
| `anexo_c_tabela_c9_perdas_r3.json` | LF (R3) | Tabela C.9 (só lista "Museus, galerias" — ver `nota`) |
| `anexo_d_tabela_d2_perdas_r4.json` | LT, LF, LO (R4) | Tabela D.2 |

Duas entradas (`anexo_b_tabela_b3_pspd.json` → "melhor que NP I" e
`anexo_b_tabela_b7_peb.json` → idem) ficaram com `"valor": null` de propósito:
a norma só dá uma faixa (0,001–0,005), não um valor fechado, e exige
justificativa técnica específica do projeto — preencher caso a caso, nunca com
um padrão da faixa.

## NG por município (Anexo F) — não fica em `dados/*.json`

Densidade de descargas atmosféricas por município vem de
`municipios_ng_anexo_f.csv` (5.572 municípios, extraído mecanicamente da
Tabela F.1 do Anexo F, com verificação de que o total bate com a contagem
oficial do IBGE e spot-check em municípios conhecidos). `codigo_ibge` fica
vazio em todas as linhas — o Anexo F da norma não traz esse código, só
município/UF/NG; se for necessário no futuro, precisa vir de outra fonte,
nunca inventado aqui.

Esse CSV é importado automaticamente na tabela `municipios_ng` na primeira
subida da aplicação (ver `_seed_municipios_ng` em `app/main.py`) e pode ser
reimportado a qualquer momento via `python scripts/importar_ng_municipios.py
<csv> "<referência>"` — análises já criadas guardam um snapshot do NG usado e
não são afetadas por uma reimportação posterior.

## Ainda não implementado

O motor de cálculo (`eventos.py`, `probabilidades.py`, `perdas.py`,
`riscos.py`, `memoria.py`) que combina estes coeficientes em N, P, L, R1, R3,
R4 e F ainda não foi escrito — o que existe hoje é a resolução do NG
(`ng.py`) e o cadastro básico de uma análise (`AnaliseRisco` em
`modelos.py`), com o snapshot do NG persistido.
