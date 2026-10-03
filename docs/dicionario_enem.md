# Dicionário — ENEM (T1.3)

Fonte: dicionários oficiais do INEP (`microdados_enem_AAAA/**/Dicionário_*.xlsx`). Parquets em `data/interim/enem_AAAA.parquet` (+ `enem_all.parquet`).
Convenções: ver `convencoes.md`. Layout varia por ano: ver mapeamento em `src/enem.py` (`FONTES`).

## Colunas do parquet

| coluna | variável original | descrição |
|---|---|---|
| ano | NU_ANO (fixo no pipeline) | Ano do Enem |
| origem | — | `microdados` (2023), `participantes` ou `resultados` (2024+): de qual arquivo a linha veio |
| co_escola | CO_ESCOLA (RESULTADOS 2024+) | Código INEP da escola (8 dígitos, str); nulo em 2023. Mascarado se escola < 10 participantes |
| co_escola_mascarado | derivado | True se o código começa com 6 (máscara do INEP) |
| co_municipio_esc / sg_uf_esc | CO_MUNICIPIO_ESC / SG_UF_ESC | Município (IBGE 7 dígitos, str) e UF da escola |
| co_municipio_prova / sg_uf_prova | CO_MUNICIPIO_PROVA / SG_UF_PROVA | Município e UF onde fez a prova |
| tp_escola | TP_ESCOLA (só 2023) | Tipo de escola do EM (autodeclarado) |
| tp_sexo | TP_SEXO (MICRODADOS 2023, PARTICIPANTES 2024+) | M/F |
| tp_st_conclusao | TP_ST_CONCLUSAO | Situação de conclusão do EM |
| tp_dependencia_adm_esc | TP_DEPENDENCIA_ADM_ESC | Dependência administrativa da escola (nulo se sem escola) |
| nu_nota_cn / ch / lc / mt | NU_NOTA_CN/CH/LC/MT | Notas: Ciências da Natureza, Ciências Humanas, Linguagens e Códigos, Matemática (nulo se ausente/eliminado) |
| nu_nota_redacao | NU_NOTA_REDACAO | Nota da redação (0–1000) |
| q005 | Q005 | Nº de pessoas na residência (1–20) |
| q006 | Q006 | Como publicado. **2023:** renda familiar. **2024+:** "Você possui renda?" (A=Não, B=Sim) |
| renda_familiar_faixa | Q006 (2023) / Q007 (2024, 2025) | Faixa de renda familiar A–Q, **harmonizada** (letras iguais, valores em R$ mudam por ano; ver abaixo) |

Colunas ausentes na origem de uma linha ficam **nulas**. Em 2024+ cada ano tem duas origens independentes (sem junção possível); agregue por `origem`.

## Categorias

### TP_SEXO
| código | descrição |
|---|---|
| M | Masculino |
| F | Feminino |

### TP_ST_CONCLUSAO (2023; em 2024/2025 muda só o ano citado)
| código | descrição |
|---|---|
| 1 | Já concluí o Ensino Médio |
| 2 | Estou cursando e concluirei o Ensino Médio em 2023 |
| 3 | Estou cursando e concluirei o Ensino Médio após 2023 |
| 4 | Não concluí e não estou cursando o Ensino Médio |

### TP_ESCOLA (apenas 2023)
| código | descrição |
|---|---|
| 1 | Não Respondeu |
| 2 | Pública |
| 3 | Privada |

### TP_DEPENDENCIA_ADM_ESC
| código | descrição |
|---|---|
| 1 | Federal |
| 2 | Estadual |
| 3 | Municipal |
| 4 | Privada |

### Q005 — pessoas na residência
Códigos 1 a 20: 1 = "moro sozinho(a)"; 2..20 = número de pessoas.

### Q006
- **2023** — renda mensal familiar (faixas A–Q):

| código | descrição |
|---|---|
| A | Nenhuma Renda |
| B | Até R$ 1.320,00 |
| C | De R$ 1.320,01 até R$ 1.980,00. |
| D | De R$ 1.980,01 até R$ 2.640,00. |
| E | De R$ 2.640,01 até R$ 3.300,00. |
| F | De R$ 3.300,01 até R$ 3.960,00. |
| G | De R$ 3.960,01 até R$ 5.280,00. |
| H | De R$ 5.280,01 até R$ 6.600,00. |
| I | De R$ 6.600,01 até R$ 7.920,00. |
| J | De R$ 7.920,01 até R$ 9240,00. |
| K | De R$ 9.240,01 até R$ 10.560,00. |
| L | De R$ 10.560,01 até R$ 11.880,00. |
| M | De R$ 11.880,01 até R$ 13.200,00. |
| N | De R$ 13.200,01 até R$ 15.840,00. |
| O | De R$ 15.840,01 até R$19.800,00. |
| P | De R$ 19.800,01 até R$ 26.400,00. |
| Q | Acima de R$ 26.400,00. |

- **2024 e 2025** — "Você possui renda?":

| código | descrição |
|---|---|
| A | Não |
| B | Sim |

### Renda familiar em 2024 (Q007)
| código | descrição |
|---|---|
| A | Nenhuma Renda |
| B | Até R$ 1.412,00. |
| C | De R$ 1.412,01 até R$ 2.118,00. |
| D | De R$ 2.118,01 até R$ 2.824,00. |
| E | De R$ 2.824,01 até R$ 3.530,00. |
| F | De R$ 3.530,01 até R$ 4.236,00. |
| G | De R$ 4.236,01 até R$ 5.648,00. |
| H | De R$ 5.648,01 até R$ 7.060,00. |
| I | De R$ 7.060,01 até R$ 8.472,00. |
| J | De R$ 8.472,01 até R$9.884,00. |
| K | De R$ 9.884,01 até R$ 11.296,00. |
| L | De R$ 11.296,01 até R$ 12.708,00. |
| M | De R$ 12.708,01 até R$ 14.120,00. |
| N | De R$ 14.120,01 até R$ 16.944,00. |
| O | De R$ 16.944,01 até R$ 21.180,00. |
| P | De R$ 21.180,01 até R$ 28.240,00. |
| Q | Acima de R$ 28.240,00. |

### Renda familiar em 2025 (Q007)
| código | descrição |
|---|---|
| A | Nenhuma renda |
| B | Até R$ 1.518,00 |
| C | De R$ 1.518,01 até R$ 2.277,00 |
| D | De R$ 2.277,01 até R$ 3.036,00 |
| E | De R$ 3.036,01 até R$ 3.795,00 |
| F | De R$ 3.795,01 até R$ 4.554,00 |
| G | De R$ 4.554,01 até R$ 6.072,00 |
| H | De R$ 6.072,01 até R$ 7.590,00 |
| I | De R$ 7.590,01 até R$ 9.108,00 |
| J | De R$ 9.108,01 até R$10.626,00 |
| K | De R$ 10.626,01 até R$ 12.144,00 |
| L | De R$ 12.144,01 até R$ 13.662,00 |
| M | De R$ 13.662,01 até R$ 15.180,00 |
| N | De R$ 15.180,01 até R$ 18.216,00 |
| O | De R$ 18.216,01 até R$ 22.770,00 |
| P | De R$ 22.770,01 até R$ 30.360,00 |
| Q | Acima de R$ 30.360,00 |

Observações sobre renda (importante para T2.5):
- 2023: faixas em múltiplos do SM de R$ 1.320
- 2024: SM R$ 1.412
- 2025: SM R$ 1.518
- As letras A–Q são as mesmas nos três anos, mas os limites em R$ mudam com o salário mínimo; as faixas são **múltiplos do SM** (B = até 1 SM; C = 1–1,5 SM; D = 1,5–2 SM ...). Para o corte "≤ 1,5 SM por pessoa", combinar `renda_familiar_faixa` com `q005`.
- `renda_familiar_faixa` já aponta para a coluna certa de cada ano (Q006 em 2023, Q007 depois). Quem usar `q006` cru em 2024+ está lendo "possui renda?".

## Limitação T1.4
Ver `lacunas_enem.md`: sem junção aluno-a-aluno entre perfil e notas/escola em 2024–2025; `co_escola` só em RESULTADOS 2024+ e mascarado para escolas pequenas. Granularidade comum confiável: **município**.
