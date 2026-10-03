# Chaves e normalização de texto (T2.1–T2.2)

Código: `src/chaves.py` (`auditar_chaves()`, `normalizar_texto()`, `anexar_co_municipio()` …). Regenerar este documento: `python src/docs_a.py`.

## Regras de chave (ver também `convencoes.md`)
- **Município:** código IBGE de 7 dígitos, `string` (`co_municipio`; no ENEM `co_municipio_prova` e `co_municipio_esc`).
- **Escola:** `co_entidade` INEP de 8 dígitos, `string` (no ENEM, `co_escola`).
- **Ano:** inteiro.
- **Saeb:** `id_escola_saeb` e `id_municipio_saeb` são **máscaras** (códigos fictícios, dicionário oficial); só o *formato* é auditado — **não** são chaves INEP/IBGE e não entram em integridade referencial.
- Listas de olimpíadas **não têm código**: município é obtido por (nome normalizado + UF) contra `dim_municipio_base`.

## Auditoria das bases em `data/interim` (todas passam)
`auditar_chaves()` verifica tipo `VARCHAR`, formato por regex, nulos permitidos, unicidade das dimensões e integridade referencial (municípios do Ideb/ENEM/`dim_escola_base` ∈ `dim_municipio_base`; escolas do Ideb ∈ `dim_escola_base`).

| base | coluna | formato | linhas | nulos | fora_do_formato |
|---|---|---|---|---|---|
| enem_all | co_municipio_prova | \d{7} | 22221387 | 0 | 0 |
| enem_all | co_municipio_esc | \d{7} | 22221387 | 17958056 | 0 |
| enem_all | co_escola | \d{8} | 22221387 | 18916562 | 0 |
| saeb_escola | id_escola_saeb | \d{8} | 224270 | 0 | 0 |
| saeb_escola | id_municipio_saeb | \d{7} | 224270 | 0 | 0 |
| ideb_escola | co_entidade | \d{8} | 498814 | 0 | 0 |
| ideb_escola | co_municipio | \d{7} | 498814 | 0 | 0 |
| ideb_municipio | co_municipio | \d{7} | 206273 | 0 | 0 |
| dim_municipio_base | co_municipio | \d{7} | 5571 | 0 | 0 |
| dim_escola_base | co_entidade | \d{8} | 53773 | 0 | 0 |
| dim_escola_base | co_municipio | \d{7} | 53773 | 0 | 0 |

`co_municipio_esc` e `co_escola` do ENEM têm nulos por desenho (estudante sem escola recenseada; `co_escola` só em RESULTADOS 2024–25).

## Normalização de texto
Função `normalizar_texto`: caixa alta → remoção de acentos (`unidecode`) → pontuação vira espaço → junta letras soltas no início/fim (`E M E F` → `EMEF`, `E M` → `EM`) → expande siglas (token inteiro). `EM` só é expandido (Escola Municipal) **no início** do nome, por ser ambíguo com Ensino Médio. `nome_nucleo` remove palavras genéricas (tipo/rede/etapa/títulos) e serve de guarda no linkage. `normalizar_nome_municipio` remove preposições e `D` isolado (`D'OESTE`). `normalizar_nome_pessoa` remove acentos e partículas (DE/DA/DO/DAS/DOS/E).

Exemplos (nomes de escola, sem dados de aluno):

| original | normalizado | núcleo |
|---|---|---|
| E M E F INSTITUTO NOSSA SENHORA | ESCOLA MUNICIPAL ENSINO FUNDAMENTAL INSTITUTO NOSSA SENHORA | NOSSA SENHORA |
| EEEFM Prof. Joao da Silva | ESCOLA ESTADUAL ENSINO FUNDAMENTAL MEDIO PROFESSOR JOAO DA SILVA | JOAO SILVA |
| COL MILITAR TIRADENTES | COLEGIO MILITAR TIRADENTES | MILITAR TIRADENTES |
| EM Dr. Ana Neri | ESCOLA MUNICIPAL DOUTOR ANA NERI | ANA NERI |
| CIEP 123 Brizolao | CENTRO INTEGRADO EDUCACAO PUBLICA 123 BRIZOLAO | 123 BRIZOLAO |
| CEF 28 DE CEILANDIA | CENTRO ENSINO FUNDAMENTAL 28 DE CEILANDIA | 28 CEILANDIA |
| EREM Professor Ernesto Silva | ESCOLA REFERENCIA ENSINO MEDIO PROFESSOR ERNESTO SILVA | REFERENCIA ERNESTO SILVA |
| UNID ESCOLA ANISIO DE ABREU | UNIDADE ESCOLA ANISIO DE ABREU | ANISIO ABREU |

### Siglas expandidas
| sigla (token) | expansão |
|---|---|
| CE | COLEGIO ESTADUAL |
| CEF | CENTRO ENSINO FUNDAMENTAL |
| CEL | CORONEL |
| CEM | CENTRO ENSINO MEDIO |
| CETI | CENTRO ENSINO TEMPO INTEGRAL |
| CIEP | CENTRO INTEGRADO EDUCACAO PUBLICA |
| COL | COLEGIO |
| COLEG | COLEGIO |
| DEP | DEPUTADO |
| DESEMB | DESEMBARGADOR |
| DR | DOUTOR |
| DRA | DOUTORA |
| ECIT | ESCOLA CIDADA INTEGRAL TECNICA |
| EE | ESCOLA ESTADUAL |
| EEEF | ESCOLA ESTADUAL ENSINO FUNDAMENTAL |
| EEEFM | ESCOLA ESTADUAL ENSINO FUNDAMENTAL MEDIO |
| EEEM | ESCOLA ESTADUAL ENSINO MEDIO |
| EEF | ESCOLA ESTADUAL ENSINO FUNDAMENTAL |
| EEM | ESCOLA ESTADUAL ENSINO MEDIO |
| EF | ENSINO FUNDAMENTAL |
| EMEB | ESCOLA MUNICIPAL EDUCACAO BASICA |
| EMEF | ESCOLA MUNICIPAL ENSINO FUNDAMENTAL |
| EMEFM | ESCOLA MUNICIPAL ENSINO FUNDAMENTAL MEDIO |
| EMEI | ESCOLA MUNICIPAL EDUCACAO INFANTIL |
| EMEIEF | ESCOLA MUNICIPAL EDUCACAO INFANTIL ENSINO FUNDAMENTAL |
| EMI | ENSINO MEDIO INTEGRADO |
| ENG | ENGENHEIRO |
| ENS | ENSINO |
| EREM | ESCOLA REFERENCIA ENSINO MEDIO |
| ESC | ESCOLA |
| EST | ESTADUAL |
| ESTAD | ESTADUAL |
| EXERC | EXERCITO |
| FED | FEDERAL |
| FUN | FUNDAMENTAL |
| FUND | FUNDAMENTAL |
| GEN | GENERAL |
| GOV | GOVERNADOR |
| IF | INSTITUTO FEDERAL |
| INST | INSTITUTO |
| MUL | MUNICIPAL |
| MUN | MUNICIPAL |
| MUNIC | MUNICIPAL |
| NS | NOSSA SENHORA |
| PART | PARTICULAR |
| PRES | PRESIDENTE |
| PROF | PROFESSOR |
| PROFA | PROFESSORA |
| SEN | SENADOR |
| SR | SENHOR |
| SRA | SENHORA |
| STA | SANTA |
| STO | SANTO |
| UNID | UNIDADE |

## Match de município nas listas de olimpíadas
Exato por (nome normalizado, UF); fallback **fuzzy só na mesma UF** com dobra fonética (Z=S, J=G, Y=I, K=C, W=V, H mudo, letras dobradas), `fuzz.ratio ≥ 92.0` e margem ≥ 4.0 sobre o 2º candidato; na dúvida, `sem_match`.

| olimpiada | ano | linhas | exato | fuzzy | ambiguo | sem_match | % com município |
|---|---|---|---|---|---|---|---|
| OBI | 2016 | 503 | 503 | 0 | 0 | 0 | 100.0 |
| OBI | 2017 | 526 | 526 | 0 | 0 | 0 | 100.0 |
| OBI | 2019 | 701 | 697 | 0 | 0 | 4 | 99.43 |
| OBI | 2020 | 488 | 488 | 0 | 0 | 0 | 100.0 |
| OBI | 2021 | 560 | 560 | 0 | 0 | 0 | 100.0 |
| OBI | 2022 | 505 | 505 | 0 | 0 | 0 | 100.0 |
| OBI | 2023 | 596 | 596 | 0 | 0 | 0 | 100.0 |
| OBI | 2024 | 862 | 862 | 0 | 0 | 0 | 100.0 |
| OBI | 2025 | 744 | 744 | 0 | 0 | 0 | 100.0 |
| OBMEP | 2016 | 48981 | 48825 | 136 | 0 | 20 | 99.96 |
| OBMEP | 2017 | 51877 | 51764 | 100 | 0 | 13 | 99.97 |
| OBMEP | 2018 | 54121 | 53971 | 124 | 0 | 26 | 99.95 |
| OBMEP | 2019 | 55671 | 55528 | 107 | 0 | 36 | 99.94 |
| OBMEP | 2024 | 59498 | 59344 | 114 | 0 | 40 | 99.93 |
| OBMEP | 2025 | 59648 | 59488 | 126 | 0 | 34 | 99.94 |

Pares aplicados pelo fallback fuzzy (município da lista → município IBGE):

| municipio_norm | uf | co_municipio | municipio_dim | score | linhas |
|---|---|---|---|---|---|
| ARES | RN | 2401206 | Arez | 100.0 | 7 |
| BATAIPORA | MS | 5002001 | Batayporã | 100.0 | 7 |
| BRASOPOLIS | MG | 3108909 | Brazópolis | 100.0 | 104 |
| CHIAPETA | RS | 4305405 | Chiapetta | 100.0 | 12 |
| DONA EUSEBIA | MG | 3122900 | Dona Euzébia | 100.0 | 11 |
| GRACHO CARDOSO | SE | 2802601 | Graccho Cardoso | 100.0 | 4 |
| IGUARACI | PE | 2606903 | Iguaracy | 100.0 | 27 |
| ITAPAGE | CE | 2306306 | Itapajé | 100.0 | 195 |
| MIRASSOL DOESTE | MT | 5105622 | Mirassol d'Oeste | 96.3 | 34 |
| PARATI | RJ | 3303807 | Paraty | 100.0 | 31 |
| PAU DARCO PIAUI | PI | 2207793 | Pau D'Arco do Piauí | 96.6 | 5 |
| SANTA ISABEL PARA | PA | 1506500 | Santa Izabel do Pará | 100.0 | 8 |
| SANTA TERESINHA | BA | 2928505 | Santa Terezinha | 100.0 | 61 |
| SANTANA LIVRAMENTO | RS | 4317103 | Sant'Ana do Livramento | 97.3 | 78 |
| SAO JOAO PAU DALHO | SP | 3549300 | São João do Pau d'Alho | 97.0 | 2 |
| SAO LUIS PARAITINGA | SP | 3550001 | São Luiz do Paraitinga | 100.0 | 23 |
| SAO THOME LETRAS | MG | 3165206 | São Tomé das Letras | 100.0 | 37 |
| TOCOS MOGI | MG | 3169059 | Tocos do Moji | 100.0 | 38 |
| TRAJANO MORAIS | RJ | 3305901 | Trajano de Moraes | 92.9 | 23 |

**Resíduo sem match** (não inventado; em geral são municípios que mudaram de nome — ex.: Augusto Severo → Campo Grande-RN, Picarras → Balneário Piçarras — ou grafias distantes):

| municipio_norm | uf | match_municipio | linhas |
|---|---|---|---|
| PICARRAS | SC | sem_match | 71 |
| ITABIRINHA MANTENA | MG | sem_match | 17 |
| ACU | RN | sem_match | 16 |
| POXOREO | MT | sem_match | 15 |
| FLORINIA | SP | sem_match | 11 |
| ITAMARACA | PE | sem_match | 8 |
| AUGUSTO SEVERO | RN | sem_match | 7 |
| SAO LUIZ | RR | sem_match | 7 |
| SAO MIGUEL TOUROS | RN | sem_match | 6 |
| SAO VALERIO NATIVIDADE | TO | sem_match | 5 |
| PRESIDENTE JUSCELINO | RN | sem_match | 3 |
| SAO DOMINGOS POMBAL | PB | sem_match | 3 |
| FORTALEZA TABOCAO | TO | sem_match | 2 |
| GOVERNADOR LOMANTO JUNIOR | BA | sem_match | 1 |
| SANTAREM | PB | sem_match | 1 |
