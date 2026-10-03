# Lacunas — ENEM (T1.1 / T1.4)

## Inventário de anos (alvo 2016–2025, RN 6)

Fonte: `data/raw/inep/microdados_enem_AAAA/`.

| ano | status | arquivos |
|---|---|---|
| 2016 | AUSENTE | - |
| 2017 | AUSENTE | - |
| 2018 | AUSENTE | - |
| 2019 | AUSENTE | - |
| 2020 | AUSENTE | - |
| 2021 | AUSENTE | - |
| 2022 | AUSENTE | - |
| 2023 | presente | MICRODADOS_ENEM_2023.csv |
| 2024 | presente | PARTICIPANTES_2024.csv, RESULTADOS_2024.csv |
| 2025 | presente | PARTICIPANTES_2025.csv, RESULTADOS_2025.csv |

- **Presentes:** 2023, 2024, 2025.
- **Ausentes:** 2016, 2017, 2018, 2019, 2020, 2021, 2022 (7 de 10 anos). Nenhum ZIP desses anos foi encontrado no projeto nem em `~/Documentos/buildinpublic/` (que só repete 2023–2025). Os microdados antigos (2016–2022) precisam ser baixados da página oficial do INEP; o pipeline (`python src/enem.py`) só precisa que seus mapeamentos de colunas sejam acrescentados em `FONTES` (`src/enem.py`).
- Consequência: séries históricas (tendência 2016–2025) **não são possíveis** com os dados atuais; há só 3 anos consecutivos.

## T1.4 — Limitação de granularidade (código de escola)

1. **2023:** o arquivo único não tem código de escola (`CO_ESCOLA`); só município da escola (`CO_MUNICIPIO_ESC`, preenchido em ~24% das linhas) e `TP_ESCOLA`/`TP_DEPENDENCIA_ADM_ESC`. Granularidade: **município**.
2. **2024 e 2025:** o INEP separou a base em `PARTICIPANTES` (sexo, conclusão, Q005, renda, município da prova; **sem escola e sem notas**) e `RESULTADOS` (notas, **`CO_ESCOLA`**, município e dependência da escola; **sem sexo, renda ou Q005**).
   - O dicionário oficial afirma que `NU_SEQUENCIAL` ≠ `NU_INSCRICAO` e que **não é possível relacionar as duas bases**. Logo, nota × renda × sexo do mesmo aluno **não pode ser reconstruída** nesses anos.
   - `CO_ESCOLA` existe (obtido do Censo Escolar pelo CPF) para ~36% das linhas de resultados; é nulo para quem não concluiu/cursa o EM em escola recenseada. Escolas com < 10 participantes têm o código **mascarado** (prefixo `6`); sinalizadas em `co_escola_mascarado`.
   - Portanto, **nota por escola** é possível em 2024–2025 (via `RESULTADOS`), mas **renda/Q005 por escola não** — a renda só existe agregada por município da prova (participantes).
3. Para o restante do projeto: usar **município** como granularidade comum (`co_municipio_esc` para notas por escola-município; `co_municipio_prova` para perfil socioeconômico), e `co_escola` apenas como bônus em 2024–2025.
