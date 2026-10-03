# EDA — ENEM (T1.2)

Base: `data/interim/enem_all.parquet` (anos 2023, 2024, 2025; 2016–2022 ausentes, ver `lacunas_enem.md`).
Em 2024–2025 a base se divide em duas origens independentes (`participantes` e `resultados`) com o **mesmo número de linhas** mas **sem junção possível**.

## Volumetria

| ano | origem | linhas |
|---|---|---|
| 2023 | microdados | 3933955 |
| 2024 | participantes | 4332944 |
| 2024 | resultados | 4332944 |
| 2025 | participantes | 4810772 |
| 2025 | resultados | 4810772 |

### Inscritos por UF da prova (origem `microdados`/`participantes`)

| uf | 2023 | 2024 | 2025 |
|---|---|---|---|
| AC | 24274 | 26424 | 28957 |
| AL | 82760 | 88896 | 96480 |
| AM | 92916 | 96898 | 110831 |
| AP | 28807 | 30650 | 33190 |
| BA | 324268 | 376845 | 427983 |
| CE | 241960 | 250607 | 275902 |
| DF | 72975 | 74520 | 82955 |
| ES | 73724 | 74543 | 85910 |
| GO | 149110 | 151158 | 166747 |
| MA | 165756 | 178833 | 211370 |
| MG | 358575 | 393824 | 464937 |
| MS | 47455 | 51311 | 57932 |
| MT | 63912 | 67782 | 80396 |
| PA | 229162 | 248061 | 289328 |
| PB | 124511 | 128546 | 142035 |
| PE | 218859 | 237615 | 272279 |
| PI | 99639 | 108113 | 120032 |
| PR | 166506 | 179954 | 195836 |
| RJ | 282296 | 289397 | 328943 |
| RN | 100706 | 102215 | 113208 |
| RO | 36038 | 38609 | 46798 |
| RR | 9639 | 12695 | 14158 |
| RS | 159919 | 279039 | 186503 |
| SC | 91263 | 95126 | 110459 |
| SE | 65540 | 69529 | 78341 |
| SP | 590767 | 647215 | 751612 |
| TO | 32618 | 34539 | 37650 |
| TOTAL | 3933955 | 4332944 | 4810772 |

**Observação:** o RS tem 279 mil inscritos em 2024, contra 160 mil (2023) e 187 mil (2025) — valor atípico não explicado nos dados; não corrigido, verificar na fonte antes de usar RS em séries.

## % de nulos (somente colunas que existem na origem; `n/d` = coluna inexistente na origem)

Nulo em nota = ausente/eliminado na prova. `co_escola`/`*_esc` nulos = sem escola recenseada (não concluinte do EM, ou fora do Censo).

| ano | origem | co_escola | co_escola_mascarado | co_municipio_esc | sg_uf_esc | co_municipio_prova | sg_uf_prova | tp_escola | tp_sexo | tp_st_conclusao | tp_dependencia_adm_esc | nu_nota_cn | nu_nota_ch | nu_nota_lc | nu_nota_mt | nu_nota_redacao | q005 | q006 | renda_familiar_faixa |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2023 | microdados | n/d | n/d | 75.6 | 75.6 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 75.6 | 31.6 | 28.2 | 28.2 | 31.6 | 28.2 | 0.0 | 0.0 | 0.0 |
| 2024 | participantes | n/d | n/d | n/d | n/d | 0.0 | 0.0 | n/d | 0.0 | 0.0 | n/d | n/d | n/d | n/d | n/d | n/d | 0.0 | 0.0 | 0.0 |
| 2024 | resultados | 63.9 | 63.9 | 63.9 | 63.9 | 0.0 | 0.0 | n/d | n/d | n/d | 63.9 | 30.6 | 26.9 | 26.9 | 30.6 | 26.9 | n/d | n/d | n/d |
| 2025 | participantes | n/d | n/d | n/d | n/d | 0.0 | 0.0 | n/d | 0.0 | 0.0 | n/d | n/d | n/d | n/d | n/d | n/d | 0.0 | 0.0 | 0.0 |
| 2025 | resultados | 63.9 | 63.9 | 63.9 | 63.9 | 0.0 | 0.0 | n/d | n/d | n/d | 63.9 | 32.2 | 28.1 | 28.1 | 32.2 | 28.1 | n/d | n/d | n/d |

## Distribuição das notas (apenas valores não nulos)

| nota | ano | n_validos | media | dp | min | p25 | mediana | p75 | max |
|---|---|---|---|---|---|---|---|---|---|
| cn | 2023 | 2692427 | 495.8 | 87.9 | 0.0 | 440.5 | 493.9 | 551.2 | 868.4 |
| cn | 2024 | 3004981 | 493.9 | 79.1 | 0.0 | 431.4 | 488.4 | 550.2 | 867.2 |
| cn | 2025 | 3260336 | 500.0 | 78.6 | 0.0 | 443.5 | 498.2 | 550.9 | 858.7 |
| ch | 2023 | 2822643 | 523.4 | 88.6 | 0.0 | 467.8 | 530.4 | 584.9 | 823.0 |
| ch | 2024 | 3167955 | 511.0 | 93.1 | 0.0 | 446.4 | 516.3 | 576.2 | 819.7 |
| ch | 2025 | 3457555 | 511.2 | 88.3 | 0.0 | 446.6 | 513.0 | 574.0 | 856.4 |
| lc | 2023 | 2822643 | 518.1 | 75.5 | 0.0 | 471.4 | 523.1 | 570.3 | 820.8 |
| lc | 2024 | 3167955 | 524.5 | 70.0 | 0.0 | 484.1 | 531.5 | 572.1 | 795.8 |
| lc | 2025 | 3457555 | 532.1 | 72.6 | 0.0 | 490.3 | 538.8 | 581.6 | 794.5 |
| mt | 2023 | 2692427 | 533.8 | 131.6 | 0.0 | 431.2 | 523.6 | 630.1 | 958.6 |
| mt | 2024 | 3004981 | 527.0 | 114.2 | 0.0 | 431.2 | 499.0 | 610.8 | 961.9 |
| mt | 2025 | 3260336 | 520.0 | 127.6 | 0.0 | 416.5 | 500.0 | 606.8 | 980.3 |
| redacao | 2023 | 2822643 | 617.8 | 214.6 | 0.0 | 500.0 | 620.0 | 780.0 | 1000.0 |
| redacao | 2024 | 3167955 | 624.6 | 216.3 | 0.0 | 520.0 | 640.0 | 780.0 | 1000.0 |
| redacao | 2025 | 3457555 | 580.8 | 212.9 | 0.0 | 480.0 | 600.0 | 720.0 | 1000.0 |

## Cobertura de escola pública

### 2023 — `TP_ESCOLA` (autodeclarado, todas as linhas)

| tp_escola | n | pct |
|---|---|---|
| 1 Não respondeu | 2532796 | 64.4 |
| 2 Pública | 1166540 | 29.7 |
| 3 Privada | 234619 | 6.0 |

`tp_escola` **não existe** em 2024/2025. A rede passa a vir de `tp_dependencia_adm_esc` (Censo Escolar, só em `resultados`; 1–3 = pública, 4 = privada):

| ano | linhas_resultados | com_escola | pct_com_escola | publica | privada | pct_publica_entre_com_escola |
|---|---|---|---|---|---|---|
| 2023 | 3933955 | 958506 | 24.4 | 728878 | 229628 | 76.0 |
| 2024 | 4332944 | 1565797 | 36.1 | 1302806 | 262991 | 83.2 |
| 2025 | 4810772 | 1739028 | 36.1 | 1466229 | 272799 | 84.3 |

(2023: `linhas_resultados` = total de linhas do microdados; escola identificada via `TP_DEPENDENCIA_ADM_ESC` preenchido.)
Atenção: 2023 (24% com escola) e 2024–2025 (36%) **não são diretamente comparáveis** — o percentual de escola pública entre quem tem escola sobe de 76% para 83–84%, o que pode refletir mudança de cobertura do vínculo com o Censo Escolar, não só da realidade.

### % de escola pública por UF da escola (2025, entre linhas com escola)

| uf | ano | pct |
|---|---|---|
| AC | 2025 | 94.1 |
| AL | 2025 | 87.7 |
| AM | 2025 | 95.1 |
| AP | 2025 | 89.6 |
| BA | 2025 | 89.0 |
| CE | 2025 | 92.5 |
| DF | 2025 | 73.1 |
| ES | 2025 | 86.4 |
| GO | 2025 | 88.1 |
| MA | 2025 | 92.8 |
| MG | 2025 | 85.8 |
| MS | 2025 | 86.7 |
| MT | 2025 | 88.8 |
| PA | 2025 | 89.1 |
| PB | 2025 | 85.2 |
| PE | 2025 | 87.5 |
| PI | 2025 | 90.1 |
| PR | 2025 | 80.9 |
| RJ | 2025 | 71.8 |
| RN | 2025 | 85.5 |
| RO | 2025 | 92.8 |
| RR | 2025 | 92.3 |
| RS | 2025 | 82.7 |
| SC | 2025 | 79.1 |
| SE | 2025 | 85.2 |
| SP | 2025 | 76.1 |
| TO | 2025 | 92.6 |

### Escolas identificáveis (2024–2025)

| ano | escolas_codigo_real | codigos_mascara | linhas_mascaradas |
|---|---|---|---|
| 2024 | 25179 | 4221 | 22309.0 |
| 2025 | 25963 | 3941 | 21233.0 |

Códigos mascarados agrupam escolas com < 10 participantes: não identificam escola individual.
