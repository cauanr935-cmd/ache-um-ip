# Cobertura das olimpíadas (T1.11)

Base: `data/interim/medalhistas.parquet` (508066 linhas). Pergunta: cada lista liga o aluno a um território (escola e município)?

## Resumo por olimpíada

| olimpiada | linhas | % com escola | % com município | % com UF | % com rede |
|---|---|---|---|---|---|
| OBI | 5485 | 100.0% | 100.0% | 100.0% | 0.0% |
| OBMEP | 502581 | 100.0% | 100.0% | 100.0% | 100.0% |

## Por olimpíada e ano

| olimpiada | ano | linhas | % com escola | % com município | % com UF | % com rede | % com posição |
|---|---|---|---|---|---|---|---|
| OBI | 2016 | 503 | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% |
| OBI | 2017 | 526 | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% |
| OBI | 2019 | 701 | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% |
| OBI | 2020 | 488 | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% |
| OBI | 2021 | 560 | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% |
| OBI | 2022 | 505 | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% |
| OBI | 2023 | 596 | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% |
| OBI | 2024 | 862 | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% |
| OBI | 2025 | 744 | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% |
| OBMEP | 2016 | 48981 | 100.0% | 100.0% | 100.0% | 100.0% | 0.0% |
| OBMEP | 2017 | 51877 | 100.0% | 100.0% | 100.0% | 100.0% | 6.9% |
| OBMEP | 2018 | 54121 | 100.0% | 100.0% | 100.0% | 100.0% | 7.3% |
| OBMEP | 2019 | 55671 | 100.0% | 100.0% | 100.0% | 100.0% | 6.7% |
| OBMEP | 2021 | 57325 | 100.0% | 100.0% | 100.0% | 100.0% | 7.1% |
| OBMEP | 2022 | 55982 | 100.0% | 100.0% | 100.0% | 100.0% | 5.6% |
| OBMEP | 2023 | 59478 | 100.0% | 100.0% | 100.0% | 100.0% | 6.4% |
| OBMEP | 2024 | 59498 | 100.0% | 100.0% | 100.0% | 100.0% | 7.1% |
| OBMEP | 2025 | 59648 | 100.0% | 100.0% | 100.0% | 100.0% | 6.4% |

## Leitura

- **OBMEP:** escola, município e UF em 100% das linhas (nomes, **sem código INEP**; linkage = T2.3). `rede` (F/E/M/C/P) em ~100%: dá para filtrar escola pública. Anos presentes: [2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025].
- **OBI:** escola, cidade e UF em ~100%; **sem rede** (público/privada) e sem código INEP. Há linhas de modalidade Universitária (não são alunos de EF/EM) e Competição Feminina (CF-OBI) — decidir filtros na T2.x.
- **ONHB:** **0 linhas** (não há lista pública de equipes medalhistas coletável; ver `lacunas_olimpiadas.md`).
- Percentuais medem preenchimento, não qualidade do texto (grafias de escola/município variam entre fontes).

## Validação do parquet da OBMEP

- INFO OBMEP 2016: 1 linha(s) sem nome na fonte, descartada(s) de propósito
- OBMEP 2023: 59478 linhas no parquet x 85717 linhas <tr> no HTML bruto
- OBMEP 2024: 59498 linhas no parquet x 85850 linhas <tr> no HTML bruto
- INFO OBMEP 2025: 4 linha(s) sem nome na fonte, descartada(s) de propósito
- OBMEP 2025: 59648 linhas no parquet x 86562 linhas <tr> no HTML bruto
- OBMEP: 1 linha(s) duplicada(s) (mesmo ano/nível/medalha/nome/escola/município)
