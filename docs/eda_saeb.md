# EDA — Saeb e Ideb (T1.5–T1.7)

Bases: `data/interim/saeb_escola.parquet` (Saeb 2017, 2019, 2021, 2023; EF2 = 9º ano EF, EM = 3ª série EM),
`ideb_escola.parquet` e `ideb_municipio.parquet` (Ideb 2025, séries 2005–2025).

> **Limitação central.** No Saeb (microdados), `ID_ESCOLA` e `ID_MUNICIPIO` são **máscaras ("códigos fictícios")**
> segundo o dicionário oficial. Não casam com `co_entidade` INEP nem com o município IBGE (0% de sobreposição com Ideb e ENEM)
> e mudam a cada edição (0 escolas em comum entre 2017/2019/2021/2023). Só a UF é real. Por isso `saeb_escola` usa
> `id_escola_saeb`/`id_municipio_saeb` e **não serve para linkage**. As notas Saeb por escola/município **com código real** estão no Ideb
> (`nota_saeb_lp`, `nota_saeb_mt`). Detalhes em `lacunas_saeb.md`.

## Volumetria Saeb (escola × etapa × rede)

| ano | etapa | rede | escolas | com_proficiencia | alunos_presentes |
|---|---|---|---|---|---|
| 2017 | EF2 | publica | 37095 | 37095 | 1782431.0 |
| 2017 | EM | privada | 1256 | 1256 | 59042.0 |
| 2017 | EM | publica | 18387 | 18387 | 1397283.0 |
| 2019 | EF2 | publica | 36905 | 29688 | 1912728.0 |
| 2019 | EM | publica | 18875 | 12061 | 1486785.0 |
| 2021 | EF2 | publica | 37168 | 22152 | 1872411.0 |
| 2021 | EM | publica | 19137 | 7161 | 1363397.0 |
| 2023 | EF2 | publica | 36355 | 31080 | 2053389.0 |
| 2023 | EM | publica | 19092 | 14431 | 1493719.0 |

`alunos_presentes` = `NU_PRESENTES_*` do TS_ESCOLA (alunos presentes na etapa). Escolas sem proficiência divulgada têm participação insuficiente.

## % de nulos (Saeb)

| ano | etapa | n | proficiencia_lp | proficiencia_mt | n_alunos | n_matriculados_censo | inse_escola | inse_aluno_medio |
|---|---|---|---|---|---|---|---|---|
| 2017 | EF2 | 37095 | 0.0 | 0.0 | 0.0 | 0.1 | 15.5 | 100.0 |
| 2017 | EM | 19643 | 0.0 | 0.0 | 0.0 | 100.0 | 17.6 | 100.0 |
| 2019 | EF2 | 36905 | 19.6 | 19.6 | 0.0 | 0.1 | 1.7 | 100.0 |
| 2019 | EM | 18875 | 36.1 | 36.1 | 0.0 | 0.1 | 0.6 | 100.0 |
| 2021 | EF2 | 37168 | 40.4 | 40.4 | 0.0 | 0.1 | 1.2 | 1.4 |
| 2021 | EM | 19137 | 62.6 | 62.6 | 0.0 | 0.3 | 2.3 | 2.6 |
| 2023 | EF2 | 36355 | 14.5 | 14.5 | 0.0 | 0.1 | 0.0 | 0.5 |
| 2023 | EM | 19092 | 24.4 | 24.4 | 0.0 | 0.1 | 0.0 | 0.8 |

`n_matriculados_censo` não existe para o EM em 2017. `inse_aluno_medio` só existe em 2021 e 2023 (INSE do aluno ausente antes).

## Proficiência média por escola (escala Saeb; escolas com média divulgada)

Média/desvio calculados **entre escolas** (sem ponderar por alunos).

| ano | etapa | rede | lp_media | lp_dp | lp_p10 | lp_mediana | lp_p90 | mt_media | mt_dp | mt_mediana |
|---|---|---|---|---|---|---|---|---|---|---|
| 2017 | EF2 | publica | 248.3 | 24.3 | 218.3 | 249.8 | 276.6 | 247.2 | 25.4 | 247.3 |
| 2017 | EM | privada | 311.3 | 37.7 | 280.7 | 314.5 | 345.8 | 325.1 | 46.9 | 325.2 |
| 2017 | EM | publica | 260.9 | 24.2 | 232.6 | 260.4 | 288.8 | 262.2 | 25.9 | 260.2 |
| 2019 | EF2 | publica | 252.7 | 21.6 | 224.9 | 253.7 | 279.0 | 255.2 | 23.8 | 255.2 |
| 2019 | EM | publica | 275.5 | 22.3 | 248.1 | 275.4 | 302.8 | 273.8 | 25.1 | 272.4 |
| 2021 | EF2 | publica | 252.0 | 21.7 | 224.0 | 253.4 | 277.7 | 251.3 | 23.4 | 251.7 |
| 2021 | EM | publica | 274.5 | 21.6 | 248.1 | 273.7 | 301.8 | 269.9 | 23.6 | 268.2 |
| 2023 | EF2 | publica | 251.9 | 22.0 | 223.5 | 252.7 | 278.6 | 250.1 | 24.2 | 249.1 |
| 2023 | EM | publica | 272.9 | 20.9 | 246.9 | 272.8 | 298.9 | 268.3 | 19.9 | 266.3 |

Conferência (2023, EF2, LP): a média oficial do `TS_ESCOLA` difere em média 0,29 ponto (máx. 41,9) da média simples dos alunos
com proficiência (`PROFICIENCIA_LP_SAEB`) — usamos a oficial (31.080 escolas comparadas).

## Cobertura por UF (2023, escolas com proficiência LP)

| uf | EF2 | EM |
|---|---|---|
| AC | 137 | 58 |
| AL | 521 | 224 |
| AM | 674 | 273 |
| AP | 119 | 42 |
| BA | 2287 | 812 |
| CE | 1872 | 672 |
| DF | 131 | 50 |
| ES | 697 | 272 |
| GO | 995 | 621 |
| MA | 1909 | 612 |
| MG | 3258 | 1715 |
| MS | 360 | 117 |
| MT | 551 | 302 |
| PA | 1752 | 598 |
| PB | 761 | 374 |
| PE | 1350 | 727 |
| PI | 929 | 441 |
| PR | 1674 | 1368 |
| RJ | 1393 | 571 |
| RN | 495 | 166 |
| RO | 320 | 153 |
| RR | 87 | 28 |
| RS | 2101 | 539 |
| SC | 1137 | 204 |
| SE | 452 | 160 |
| SP | 4706 | 3090 |
| TO | 412 | 242 |

## Cobertura por município (via Ideb, códigos IBGE reais)

Municípios com nota Saeb LP na **rede pública** (`ideb_municipio`), sobre os 5.571 da `dim_municipio_base`:

| etapa | ano | municipios_com_nota | pct_dos_municipios |
|---|---|---|---|
| EF2 | 2017 | 5462 | 98.0 |
| EF2 | 2019 | 5287 | 94.9 |
| EF2 | 2021 | 4818 | 86.5 |
| EF2 | 2023 | 5383 | 96.6 |
| EF2 | 2025 | 5491 | 98.6 |
| EM | 2017 | 5278 | 94.7 |
| EM | 2019 | 4774 | 85.7 |
| EM | 2021 | 3376 | 60.6 |
| EM | 2023 | 5065 | 90.9 |
| EM | 2025 | 5428 | 97.4 |

Escolas e municípios com nota Saeb no `ideb_escola`:

| etapa | ano | escolas_com_nota | municipios |
|---|---|---|---|
| EF2 | 2017 | 25538 | 5137 |
| EF2 | 2019 | 29720 | 5354 |
| EF2 | 2021 | 22218 | 4830 |
| EF2 | 2023 | 31097 | 5432 |
| EF2 | 2025 | 33454 | 5523 |
| EM | 2017 | 9605 | 3871 |
| EM | 2019 | 12081 | 4530 |
| EM | 2021 | 7196 | 2920 |
| EM | 2023 | 14459 | 4986 |
| EM | 2025 | 17585 | 5429 |

## INSE

Nível socioeconômico da **escola** (`inse_escola`, texto do INEP). **2017 usa "Grupo 1–5"; 2019+ usa "Nível I–VII": escalas diferentes, não comparar entre 2017 e os demais.**

| inse_escola | 2017 | 2019 | 2021 | 2023 |
|---|---|---|---|---|
| (nulo) | 9213 | 736 | 896 | 0 |
| Grupo 1 | 2754 | 0 | 0 | 0 |
| Grupo 2 | 7247 | 0 | 0 | 0 |
| Grupo 3 | 20387 | 0 | 0 | 0 |
| Grupo 4 | 13968 | 0 | 0 | 0 |
| Grupo 5 | 2919 | 0 | 0 | 0 |
| Grupo 6 | 250 | 0 | 0 | 0 |
| Nível I | 0 | 14 | 37 | 311 |
| Nível II | 0 | 6335 | 4105 | 3459 |
| Nível III | 0 | 13091 | 12010 | 12481 |
| Nível IV | 0 | 14738 | 15383 | 14763 |
| Nível V | 0 | 16525 | 18207 | 18883 |
| Nível VI | 0 | 4176 | 5432 | 5328 |
| Nível VII | 0 | 165 | 235 | 222 |

INSE médio dos **alunos** por escola (`inse_aluno_medio`, só 2021/2023; entre alunos com `IN_INSE=1`):

| ano | etapa | escolas | media | dp | min | max |
|---|---|---|---|---|---|---|
| 2021 | EF2 | 36657 | 4.83 | 0.57 | 2.45 | 6.85 |
| 2021 | EM | 18647 | 4.86 | 0.55 | 2.82 | 7.13 |
| 2023 | EF2 | 36180 | 4.85 | 0.57 | 2.21 | 6.69 |
| 2023 | EM | 18939 | 4.83 | 0.53 | 2.44 | 6.68 |

## Ideb — cobertura por escola

| etapa | ano | escolas | com_ideb | com_rendimento | com_aprovacao |
|---|---|---|---|---|---|
| EF2 | 2017 | 43469 | 25530 | 37324 | 37330 |
| EF2 | 2019 | 44831 | 29718 | 35679 | 35680 |
| EF2 | 2021 | 45878 | 22212 | 35163 | 35163 |
| EF2 | 2023 | 35442 | 31092 | 35437 | 35437 |
| EF2 | 2025 | 34938 | 33448 | 34932 | 34932 |
| EM | 2017 | 19616 | 9597 | 19605 | 19609 |
| EM | 2019 | 19792 | 12079 | 18513 | 18513 |
| EM | 2021 | 19916 | 7195 | 18021 | 18022 |
| EM | 2023 | 18686 | 14457 | 18684 | 18684 |
| EM | 2025 | 19023 | 17584 | 19021 | 19022 |
