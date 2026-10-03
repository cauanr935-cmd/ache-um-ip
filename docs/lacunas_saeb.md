# Lacunas — Saeb, Ideb, INSE, Taxa de Rendimento, Censo e Geo

## 1. Saeb: códigos de escola e município são máscaras (bloqueia o linkage)
O dicionário oficial (2017–2023) define `ID_ESCOLA` e `ID_MUNICIPIO` como *"Máscaras dos Códigos … (são códigos fictícios)"*. Verificado nos dados: 0% de sobreposição com `co_entidade` do Ideb/ENEM e 0 escolas em comum entre edições.
- `saeb_escola.parquet` usa `id_escola_saeb` / `id_municipio_saeb` (pseudônimos, só válidos dentro de uma edição) e `uf` (código IBGE real, convertido em sigla). **Não há `co_entidade` nem `co_municipio` IBGE no Saeb.** O pedido original previa essas chaves; não é possível obtê-las dos microdados.
- Não se tentou inferir escola real por similaridade de atributos (UF/rede/médias): seria especulação.
- **Alternativa adotada:** notas Saeb por escola e município **com código real** (2005–2025) vêm do Ideb (`ideb_escola`/`ideb_municipio`: `nota_saeb_lp`, `nota_saeb_mt`, `nota_saeb_padronizada`). Para os modelos (T3.x), usar o Ideb como fonte de proficiência por escola/município; usar `saeb_escola` apenas para perfil agregado por UF/etapa/rede, INSE de aluno e participação.
- Outra opção (não feita): `PLANILHAS DE RESULTADOS/TS_MUNICIPIO.xlsx` de cada edição, que traz resultados por município (verificar se com código IBGE).

## 2. INSE
- Não há arquivo local do indicador INSE por escola do INEP (página "Indicadores Educacionais"). Usado o que existe no Saeb: `inse_escola` (texto do `TS_ESCOLA`) e `inse_aluno_medio` (média de `INSE_ALUNO`, só 2021 e 2023).
- Escalas: 2017 = "Grupo 1–5"; 2019, 2021, 2023 = "Nível I–VII". **Não comparáveis** entre 2017 e os demais (coluna `inse_escala`).
- Como as escolas do Saeb são mascaradas, o INSE aqui **não** pode ser ligado a escolas reais. Para obter INSE por escola com código INEP: baixar o indicador INSE (INEP) — pendente, ver `decisoes_pendentes.md`.

## 3. Taxa de Rendimento
- Não há arquivo local da Taxa de Rendimento Escolar (aprovação/reprovação/abandono). Nem o Saeb nem o Censo (ausente) a trazem.
- **Parcialmente coberta pelas planilhas do Ideb**: `taxa_aprovacao` (total e por série, em %, 0–100) e `indicador_rendimento` (0–1) por escola e município, 2005–2025 (EF2) / 2017–2025 (EM). **Faltam reprovação e abandono** (só aprovação).
- Ideb: `ND`, `ND*`, `ND***` e `-` viram nulo; 594 valores numéricos com asterisco (média calculada por método alternativo por extravio de provas) foram mantidos como número.

## 4. Saeb 2025
Microdados do Saeb 2025 **não constam** na página oficial de microdados (consultada em 02/10/2026; última edição listada: 2023). As planilhas do Ideb 2025 já trazem as notas Saeb 2025 por escola e município. Ver `decisoes_pendentes.md`.

## 5. Censo Escolar 2025 / `dim_escola_base` (T1.13) — NÃO gerada
Não há `data/raw/inep/microdados_censo_escolar_2025*/` nem Catálogo de Escolas local. O link oficial existe
(`https://download.inep.gov.br/dados_abertos/microdados_censo_escolar_2025_.zip`, na página do Censo Escolar), mas o servidor `download.inep.gov.br` falha na verificação TLS (cadeia de certificados incompleta: `unable to get local issuer certificate`). Não se desativou a verificação sem autorização. Pendente: ver `decisoes_pendentes.md`.

## 6. Geo (T1.14)
- Baixados em `data/raw/ibge/`: `localidades_municipios.json` (API Localidades), `sidra_censo2022_pop_t4714.json` (Censo 2022, população residente), `sidra_estimativa_pop_t6579.json` (estimativa de **2026**, ano mais recente), `BR_Municipios_2025.zip` (malha municipal 2025, shapefile, 226 MB).
- `dim_municipio_base`: 5.571 municípios (inclui DF). **1 município sem população do Censo 2022** (`5101837`, Boa Esperança do Norte-MT, instalado depois do Censo); tem estimativa 2026. A API Localidades o entrega sem `microrregiao` (usado `regiao-imediata`).
- Chaves conferidas: todos os municípios de `ideb_*`, `enem_all` (prova e escola) estão em `dim_municipio_base`.
- Nomes de município de `dim_municipio_base` vêm do IBGE; os do Ideb (`no_municipio`) podem diferir em grafia.
