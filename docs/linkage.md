# Record linkage medalhista → escola e deduplicação (T2.3–T2.4)

Código: `src/linkage.py`, `src/dedup.py`, `src/chaves.py`; parâmetros: `config/linkage.yaml`; este documento: `python src/docs_a.py`.
Saídas: `data/processed/linkage_resultado.parquet` (nível **string de escola**, sem aluno), `data/processed/linkage_revisao_manual.csv` (sem aluno), `data/interim/medalhistas_enriquecido.parquet` e `aluno_dedup.parquet` (interim, com nome; a T2.10 aplica o hash).

> **Limitação estrutural.** O catálogo de escolas disponível é o **`dim_escola_base` provisório, derivado do Ideb** (53,773 escolas; só **1,244 privadas**), porque o Censo Escolar não está disponível. Escolas privadas e escolas sem Ideb **não têm onde casar**: ficam `sem_match` por construção. A taxa de linkage deve ser lida **separadamente para rede pública**; para a privada ela é baixa por falta de catálogo, não por falha do método.

## Método
1. **Município:** (nome normalizado + UF) → `co_municipio` (`chaves.anexar_co_municipio`; exato + fuzzy conservador na mesma UF).
2. **Chave de linkage:** `(olimpiada, escola_norm, co_municipio, uf, rede_grp)` — o linkage é feito por **string única de escola** (41,044 strings para 335,281 linhas) e depois propagado às linhas.
3. **Blocking:** só escolas do **mesmo município**; se a rede do medalhista é conhecida (OBMEP: F/E/M → pública; P → privada; C e OBI: sem rede) restringe aos candidatos de rede compatível (`usar_rede`).
4. **Score:** `rapidfuzz.fuzz.token_set_ratio` entre nomes normalizados (siglas expandidas).
5. **Guardas contra falso positivo.** `token_set_ratio` dá 100 quando um nome é subconjunto do outro (ex.: *Parque X II* vs *Parque X*), e é alto quando só o final difere (*Santa Luzia* vs *Santa Fé*). Se qualquer guarda falhar, o score é limitado a 89.9 (**revisão, nunca automático**): (a) núcleos (sem palavras genéricas) com `token_sort_ratio ≥ 60`, `token_set_ratio ≥ 85` e razão de comprimento ≥ 0.5; (b) conjunto de números/algarismos romanos ≥ II igual (*CEF 24* ≠ *CEF 28*; *Campus II* ≠ *III*); (c) dependência explícita diferente (Estadual × Municipal × Federal).
6. **Decisão:** score ≥ 90 → `auto`; 80 ≤ score < 90 → `revisao`; abaixo → `sem_match`. **Empate** (outro candidato com score ≥ limiar dentro de 2.0 pontos e `fuzz.ratio` dentro de 5.0) → `revisao` (motivo `empate`).

Não há rótulo manual para calcular precisão: a validação foi por **amostragem visual** de vínculos automáticos nas faixas de score mais baixas (que revelou e corrigiu falsos positivos: número diferente, final diferente, subconjunto) — a precisão formal vem da amostra de ~200 registros da T4.1.

## Taxas de linkage (propagadas às linhas de medalhista)
Categorias: `auto`, `revisao`, `sem_match` (município ok) e `sem_municipio` (não casou município).

### Por olimpíada
| olimpiada | linhas | % auto | % revisao | % sem_match | % sem_municipio |
|---|---|---|---|---|---|
| OBI | 5485 | 22.6 | 17.3 | 60.1 | 0.1 |
| OBMEP | 329796 | 71.0 | 12.6 | 16.3 | 0.1 |

### Por olimpíada e rede (pública × privada)
| olimpiada | rede_grp | linhas | % auto | % revisao | % sem_match | % sem_municipio |
|---|---|---|---|---|---|---|
| OBI | desconhecida | 5485 | 22.6 | 17.3 | 60.1 | 0.1 |
| OBMEP | desconhecida | 530 | 24.9 | 11.5 | 63.6 | 0.0 |
| OBMEP | privada | 36092 | 17.7 | 10.2 | 72.1 | 0.0 |
| OBMEP | publica | 293174 | 77.6 | 12.9 | 9.4 | 0.1 |

### Por olimpíada e ano
| olimpiada | ano | linhas | % auto | % revisao | % sem_match | % sem_municipio |
|---|---|---|---|---|---|---|
| OBI | 2016 | 503 | 22.3 | 20.9 | 56.9 | 0.0 |
| OBI | 2017 | 526 | 19.4 | 19.6 | 61.0 | 0.0 |
| OBI | 2019 | 701 | 22.3 | 17.8 | 59.3 | 0.6 |
| OBI | 2020 | 488 | 18.6 | 25.0 | 56.4 | 0.0 |
| OBI | 2021 | 560 | 24.8 | 21.8 | 53.4 | 0.0 |
| OBI | 2022 | 505 | 25.0 | 17.8 | 57.2 | 0.0 |
| OBI | 2023 | 596 | 22.3 | 16.9 | 60.7 | 0.0 |
| OBI | 2024 | 862 | 22.4 | 11.9 | 65.7 | 0.0 |
| OBI | 2025 | 744 | 25.0 | 10.3 | 64.7 | 0.0 |
| OBMEP | 2016 | 48981 | 76.8 | 13.3 | 9.9 | 0.0 |
| OBMEP | 2017 | 51877 | 70.0 | 12.6 | 17.4 | 0.0 |
| OBMEP | 2018 | 54121 | 70.5 | 12.4 | 17.1 | 0.0 |
| OBMEP | 2019 | 55671 | 70.4 | 12.8 | 16.8 | 0.1 |
| OBMEP | 2024 | 59498 | 70.0 | 12.1 | 17.8 | 0.1 |
| OBMEP | 2025 | 59648 | 69.2 | 12.8 | 18.0 | 0.1 |

## Taxas em strings únicas de escola
### Por olimpíada
| olimpiada | strings | % auto | % revisao | % sem_match | % sem_municipio |
|---|---|---|---|---|---|
| OBI | 829 | 24.6 | 17.1 | 58.1 | 0.1 |
| OBMEP | 40215 | 65.4 | 13.3 | 21.1 | 0.1 |

### Por olimpíada e rede
| olimpiada | rede_grp | strings | % auto | % revisao | % sem_match | % sem_municipio |
|---|---|---|---|---|---|---|
| OBI | desconhecida | 829 | 24.6 | 17.1 | 58.1 | 0.1 |
| OBMEP | desconhecida | 62 | 25.8 | 6.5 | 67.7 | 0.0 |
| OBMEP | privada | 5656 | 11.5 | 8.4 | 80.1 | 0.1 |
| OBMEP | publica | 34497 | 74.3 | 14.2 | 11.4 | 0.1 |

## Fila de revisão manual
`data/processed/linkage_revisao_manual.csv`: **5,505 strings** de escola (cobrem 42,634 linhas de medalhista), ordenadas por nº de linhas; traz até 3 candidatas com score e a coluna `decisao_manual` para preencher. Fila por motivo:

| motivo | strings |
|---|---|
| empate | 56 |
| guarda | 877 |
| score_intermediario | 4572 |

Resultado por motivo (todas as strings):

| link_status | motivo | strings | linhas |
|---|---|---|---|
| auto |  | 26514 | 235345 |
| revisao | empate | 56 | 550 |
| revisao | guarda | 877 | 6923 |
| revisao | score_intermediario | 4572 | 35161 |
| sem_match | score_baixo | 7649 | 52602 |
| sem_match | sem_candidato_no_municipio | 1335 | 4527 |
| sem_match | sem_municipio | 41 | 173 |

## Exemplos (nomes de escola, sem dados de aluno)
| status | escola (lista) | candidata (Ideb) | score |
|---|---|---|---|
| auto | ESCOLA MUNICIPAL FRANCISCO ZEFERINO PESSOA | ESCOLA MUNICIPAL FRANCISCO ZEFERINO PESSOA | 100.0 |
| auto | AYRTON SENNA DA SILVA EEFM | EEMTI AYRTON SENNA DA SILVA | 94.3 |
| auto | ESCOLA ESTADUAL EURICO MOTA | ESCOLA ESTADUAL EURICO MOTA | 100.0 |
| revisao | ARY BARROSO C E E FUNDAMENTAL MEDIO | ARY BARROSO E EEF | 86.2 |
| revisao | ESCOLA ESTADUAL DE EDUCACAO BASICA PADRE FERNANDO | ESC EST ED BAS PADRE FERNANDO | 89.6 |
| revisao | IPIRANGA ESCOLA ESTADUAL ENSINO FUNDAMENTAL | VITAL BRASIL C EEF M | 88.3 |
| sem_match | ESCOLA JOAO PAULO I |  | 51.3 |
| sem_match | COLEGIO CORACAO MATERNO LTDA |  | 60.0 |
| sem_match | COLEGIO ESTADUAL JOSE MOREIRA CORDEIRO |  | 75.6 |

## Deduplicação de alunos (T2.4, RF 2.5)
**Identidade** = nome normalizado + `co_municipio` + escola (`co_entidade` se o vínculo é `auto`; senão `escola_norm`). `aluno_key` = blake2b determinístico dessa identidade (id **interno**; não é o hash de LGPD). Premiação distinta = (olimpíada, ano, modalidade, nível, medalha). Contagens por aluno: `n_premios`, `n_ouro`, `n_prata`, `n_bronze`, `n_mencao`, `n_medalhas` (ouro+prata+bronze, sem menção), `n_olimpiadas`, `n_anos`, `primeiro_ano`, `ultimo_ano`.

| métrica | valor |
|---|---|
| linhas de medalhista | 335,281 |
| alunos únicos (`aluno_key`) | 284,127 |
| alunos com mais de 1 premiação | 42,638 |
| alunos em mais de 1 ano | 42,501 |
| alunos em mais de 1 olimpíada (OBMEP e OBI) | 537 |
| máximo de premiações de um aluno | 8 |
| linhas duplicadas exatas | 0 |

| premiações distintas | alunos |
|---|---|
| 1 | 241489 |
| 2 | 35455 |
| 3 | 5943 |
| 4 | 1178 |
| 5 | 38 |
| 6 | 18 |
| 7 | 5 |
| 8 | 1 |

**Colisão provável (não fundida):** 9,537 grupos (nome + município) aparecem com **mais de uma escola** (19,570 identidades). Pode ser troca de escola entre anos, grafia diferente da mesma escola (quando o vínculo não é automático) ou homônimo. Em 10 grupos o mesmo nome aparece em escolas diferentes **no mesmo ano, olimpíada e nível** (homônimos quase certos). Esses casos **não são fundidos**: a contagem acumulada é conservadora (tende a subcontar quem mudou de escola) e a identidade só funde quando município e escola coincidem.

## Limitações
- Catálogo provisório (Ideb): privadas e escolas sem Ideb não vinculam; **retomar com o Censo Escolar** muda as taxas.
- Sem rótulos para precisão/recall: ver T4.1.
- Estudantes que mudam de escola ou cuja escola é grafada de modo muito diferente entre anos viram identidades distintas.
- Homônimos na mesma escola e município são fundidos (limite do método sem outros atributos).
- OBI não tem `rede`: candidatos de qualquer rede no município.
