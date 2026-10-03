# Auditoria independente da sprint de dados "Ache um IP" — 2026-10-02

Método: quatro frentes somente-leitura (dados, tasks, LGPD/segurança, código), com DuckDB e leitura dos arquivos. Nada do projeto foi alterado. Relatórios de trabalho das frentes ficaram no scratchpad da sessão (fora do projeto).
"Verificada" significa que existência e consistência foram conferidas nos arquivos e dados. A corretude numérica de modelagem/EDA não foi reexecutada (ver NÃO VERIFICADO).

## 1. Resumo executivo

- **Tasks:** 23 de 49 (47%) concluídas e verificadas; 9 concluídas com problema; 7 parciais; 6 não iniciadas; 4 bloqueadas por humano.
- **Riscos principais:** (1) ENEM cobre 3 de 10 anos (RN 6 não atendida); (2) Fase 6 inexistente (notebook Colab, dicionário, linhagem, contrato, relatório de resultados, `processed/v1`); (3) `dim_*`/`fato_*` nunca geradas (T2.11); (4) linkage sem precisão medida (0/200 rotulados) e ~60–72% sem match em privadas/OBI; (5) índice de potencial com viés populacional no componente de talento (peso 0,50) e rankings que violam o contrato "uma métrica por município por recorte".
- **LGPD:** nenhum nome de aluno em `data/processed/`; sal fora do git. Mas `docs/lgpd.md` não existe.
- **Veredito para a próxima sprint: COM RESSALVAS** (tendendo a NÃO para entrega ao Instituto Ponte). Os dados intermediários e a modelagem exploratória existem e são consistentes; falta fechar a Fase 6 e a camada `processed`.

## 2. O que está CERTO (com evidência)

- Todos os 29 parquet/CSV de `interim` e `processed` abrem sem erro.
- Chaves: município 7 dígitos string e escola 8 dígitos string, 0 inválidos; PKs únicas; 0 duplicatas exatas.
- Plausibilidade: notas ENEM 0–1000; Ideb 0–10; índice em [0,1]; população > 0.
- Proxy de renda ≤ 1,5 SM recalculado do zero em `enem_all`: 90,52% / 90,91% / 91,17% (2023/24/25), igual ao documentado; código, `config/renda.yaml` e doc consistentes.
- Supressão cumprida em `agg_enem_municipio`, `agg_medalhas_municipio` e `rankings` (0 violações).
- Rankings: 0 duplicatas de (entidade, tipo, recorte, métrica).
- 18 dos 20 números conferidos em docs batem com os dados (ENEM por ano, ideb_municipio 206.273, medalhistas 335.281, linkage 26.514/5.505/9.025, rankings 196.956, etc.).
- LGPD: `data/processed` sem nomes de aluno; `data/raw` e `data/interim` no `.gitignore`; `config/lgpd.yaml` ignorado pelo git (perm 600); `.env` no histórico tinha 0 bytes.
- Nenhum dado do Instituto Ponte acessado; nenhuma credencial; nenhum caminho absoluto pessoal; sem dados inventados.
- Código: `ast.parse` ok em 26 arquivos; seeds fixas (`random_state=42`); linkage/dedup coerentes com `config/linkage.yaml` (teste sintético sem tocar em `data/`).
- Métricas de avaliação implementadas (silhouette, Davies-Bouldin, R², RMSE, MAE); `config/pesos.yaml` com justificativa.
- Lacunas principais declaradas explicitamente em `docs/lacunas_*.md`.

## 3. O que está ERRADO ou duvidoso

### CRÍTICO

**C1. ENEM só 2023–2025 (RN 6).** Evidência: `data/raw/inep/microdados_enem_{2023,2024,2025}`, `enem_all` 2023–2025. Impacto: sem série histórica; 7 anos faltando. Correção: baixar 2016–2022 (humano), rodar `src/enem.py` por ano (~60 min de processamento).

**C2. Fase 6 inexistente.** Evidência: `notebooks/` só com `.gitkeep`; sem `ache_um_ip_colab.ipynb`, `dicionario_dados.md`, `linhagem.md`, `contrato_dados.md`, `relatorio_resultados.md`, `processed/v1`, `.duckdb`, `CLAUDE.md`. Impacto: T5.1–T5.3, T5.5, T5.6 não entregues; progresso.md não informa. Correção: executar Fase 6 (Claude Code).

**C3. `dim_municipio`, `dim_escola`, `dim_aluno`, `fato_desempenho`, `fato_medalhas` não existem em `data/processed/`.** Evidência: `ls data/processed`; `src/processed.py` nunca executado. Impacto: asserts de unicidade e "zero nomes" não rodaram nessas tabelas; a modelagem lê de `interim`. Correção: rodar `processed.py` (atenção ao conflito entre a regra de colunas proibidas "nome*" e `dim_escola`).

**C4. T5.4 não atendida.** Só `run_fase4` e `run_fase5`; sem `run_fase2/3`; sem gerador de notebook (`src/caminhos.py:4`, `src/coleta_obmep.py:34` citam `pipeline.py` inexistente).

### ALTO

**A1. Linkage sem precisão medida e com baixa cobertura em privadas/OBI.** `amostra_rotulagem.csv` 0/200 rotulados; `linkage_revisao_manual.csv` 5.505 linhas, 0 decisões. Auto: OBMEP 70,5% (pública 77,6%, privada 17,7%); OBI 22,7%, 60,4% sem match. 30,1% dos medalhistas deduplicados sem `co_entidade`. Causa: `dim_escola_base` vem só do Ideb (1.244 privadas); sem Censo. Correção: rotulagem humana (30–40 min) e obter Censo/Catálogo.

**A2. `run_fase5` sobrescreve `amostra_rotulagem.csv`** (`src/avaliacao.py:31-51`, chamada em :408). Rodar após rotular apaga os rótulos. Correção: não regravar se existir (5 min).

**A3. Componente de talento invertido em municípios pequenos** (`src/modelagem.py:131-146`). `c_talento` médio 0,58 para 0 medalhas com pop ≤ ~3,8 mil vs 0,447 para 1 medalha; peso 0,50. Soma-se a `taxa_medalhas_100k` publicada para 2.659 municípios com n<10. Correção: tratar zeros explicitamente e aplicar supressão (30 min).

**A4. `dim_escola_base` provisória e sem Censo/Catálogo**; privadas quase ausentes; Ideb/Saeb 2023–2025 só rede pública, então a comparação público×privada está comprometida.

**A5. OBMEP 2020–2023, OBI 2018 e ONHB ausentes** (declarado, mas RF 2.5/RN 6 não atendidos). `config/obmep_anos.yaml` vazio.

**A6. `docs/lgpd.md` não existe** e é referenciado em `src/docs_processed.py`; `lgpd.assert_sem_nomes` citada no docstring mas inexistente (checagem inline em `processed.py::validar`).

**A7. `scipy` (usado em `avaliacao.py:12`) e `numpy` fora de `requirements.txt`** — quebra a reprodutibilidade no Colab.

**A8. Rankings não atendem o contrato "uma métrica por município por recorte"**: até 5 métricas em `recorte=geral`, até 3 em EF2/EM; sem coluna `ano`; empates massivos sem desempate (ex.: Ideb EF2 escola: 33.448 linhas, 80 ranks distintos); `rankings.parquet` defasado em relação ao código (sem `ano_ref`).

### MÉDIO

- M1. Documentos contraditórios: `relatorio_qualidade_viabilidade.md`, `decisoes_pendentes.md` (DP-2), `lacunas_saeb.md` §5 e `avaliacao.md` §0 dizem que `dim_escola_base` não existe e que o linkage não é possível; ambos existem.
- M2. `progresso.md` sem linhas para T2.1–T2.11 e T5.x, embora haja saídas reais de T2.1–T2.9.
- M3. Dados e docs possivelmente defasados: `src/*.py` modificados (14:49–14:50) após as saídas (12:00–13:48). Não reexecutado.
- M4. `enem_all` em 2024/25 é UNION ALL de participantes e resultados: `COUNT(*)` dobra o total (9,62 mi de linhas p/ 4,81 mi de inscritos).
- M5. `IN_TREINEIRO` não carregado: treineiros contaminam "EM concluinte".
- M6. Anos anteriores a 2016 em `interim` (agg_proficiencia 2005–2015: 197.223 linhas; ideb 2005–2025), fora da janela RN 6.
- M7. Renda do índice mistura duas definições (1.811 municípios por local de prova, 2.760 por escola); 1.000 municípios sem índice; renda ~saturada em 90%, baixo poder discriminante.
- M8. Rank 1 = maior renda (menos vulnerável): contradiz a leitura de "vulnerabilidade" no contrato.
- M9. INSE não é arquivo próprio e a Taxa de Rendimento só tem aprovação (T1.7); T3.4 usa renda do ENEM no lugar de INSE.
- M10. Quase tudo untracked no git (`src/`, `docs/`, `config/`, `data/processed`); sem commit desde `c58f3cd`; sem trava para `data/processed` no `.gitignore`.
- M11. Sensibilidade ±20%: 24 cenários distintos (doc diz 26); `warnings` globalmente desligados (`avaliacao.py:16`); `link_score` NaN (1.376) vira faixa "nan" (`avaliacao.py:36`).
- M12. Outlier ENEM RS 2024 (279 mil inscritos) sem explicação.
- M13. T2.7 sem mapeamento de nível das olimpíadas para EF2/EM; ENEM só EM; sexo só mensurável via ENEM 2023.

### BAIXO

- `src/coleta_obmep.py:31` contém e-mail pessoal no User-Agent.
- `saeb_escola` 2017: 1.936 escolas com n<10 e proficiência publicada; 59 linhas com proficiência 0; `n` 100% nulo em `agg_proficiencia_escola`.
- CSVs de `processed` lidos sem dtype perdem zeros à esquerda (no arquivo estão corretos).
- Divergências numéricas triviais: ideb_escola 498.814 (doc 498.809); OBMEP sem match 16,4% (doc 16,3%).
- `dedup.py:38,63,68`: chave "UF:"+uf colide com município e UF nulos; só K-Means (sem hierárquico); `run_fase5` anotada `-> None` mas devolve tupla; 1 município sem Censo 2022 (5101837); `q006` 2024/25 virou "possui renda?" (renda em Q007).
- `interim` contém nomes em claro (esperado, ignorado pelo git, política de retenção sem `docs/lgpd.md`).

## 4. Status T0.1–T5.6

Ver `docs/auditoria/status_tasks.csv` (49 linhas, com evidência e divergência com `progresso.md`).

| Status | Qtde |
|---|---|
| CONCLUÍDA-VERIFICADA | 23 |
| CONCLUÍDA-COM-PROBLEMA | 9 |
| PARCIAL | 7 |
| NÃO INICIADA | 6 |
| BLOQUEADA-POR-HUMANO | 4 |

## 5. Rastreabilidade RF/RN

Aviso: o plano não define RF/RN e `documentos/documento.md` está vazio (0 bytes). Os significados abaixo são inferidos de `docs/relatorio_qualidade_viabilidade.md` §3 e NÃO estão confirmados. RF 5.2 e RN 3 não são definidos em lugar nenhum: NÃO VERIFICADO.

| RF/RN | Significado inferido | Status | Task | Evidência |
|---|---|---|---|---|
| 2.1 | código da escola | parcial | T1.13, T2.3 | `dim_escola_base` provisória, 30% de medalhistas sem co_entidade |
| 2.2 | nome da escola | parcial | T1.13 | idem |
| 2.3 | população | atendido | T1.14 | 5.570/5.571 com população |
| 2.4 | ranking Saeb | parcial | T3.5 | via Ideb, ano mais recente |
| 2.5 | medalhistas | parcial | T1.8–T1.11, T2.3 | OBMEP 6/10, OBI 9/10, ONHB 0 |
| 3 / 3.1 | dados do IP | não atendido | T1.17, T1.18, T4.2 | só esqueleto |
| 4 / 4.1 | mapa de calor | parcial | T1.14, T3.5, T5.5 | insumos prontos, sem contrato |
| 5.1 | EF2/EM | parcial | T2.7 | ENEM só EM; olimpíadas sem mapeamento |
| 5.3 | sexo | parcial | T3.5, T4.4 | só ENEM 2023; medalhistas sem sexo |
| 5.4 | renda ≤ 1,5 SM | parcial | T2.5 | proxy por município, saturado ~90% |
| RN 6 | últimos 10 anos | não atendido | T1.1, T1.2, T1.8, T1.9 | ENEM 3/10, Saeb 4 edições |

## 6. Lacunas declaradas vs NÃO declaradas

**Declaradas:** ENEM 2016–2022, INSE, Taxa de Rendimento (parcial), OBMEP 2020–2023, OBI 2018, ONHB, Censo Escolar, Saeb 2025 e ids mascarados, IBGE (1 município), dados do IP, MEC/Secretarias.

**NÃO declaradas (ou declaradas errado):**
1. Fase 6 inteira ausente (sem aviso em `progresso.md`).
2. T2.11 nunca executada (asserts não rodaram).
3. Contradição sobre `dim_escola_base` (existe, docs dizem que não).
4. Precisão/recall do linkage nunca medidos.
5. Privadas e OBI com 60–72% sem match por falta de Censo (só em `linkage.md`).
6. Ausência do mapeamento EF2/EM para olimpíadas.
7. Outlier ENEM RS 2024.
8. Viés populacional do componente de talento; supressão não aplicada à taxa que alimenta o índice.
9. `docs/relatorio_resultados.md` não existe, então o impacto das lacunas no relatório final não está admitido.
10. Projeto não versionado.

## NÃO VERIFICADO

- Números de regressão/clusters/sensibilidade de `docs/avaliacao.md`: exigem reexecutar a modelagem, que grava em `data/` e `docs/`.
- Se as saídas atuais correspondem ao código atual (código editado depois).
- Lint (ruff/pyflakes não instalados).
- Execução do notebook/pipeline: notebook inexistente; pipeline não executado por gravar em `data/` e sobrescrever a amostra de rotulagem.
- Texto da política de retenção LGPD (T2.10).
- Se `data/raw/inep/indicadores` tem INSE/Taxa de Rendimento além do Ideb 2025.
- Definição oficial de RF/RN (ausente do repositório).
- Ano efetivo das métricas Ideb/Saeb em `rankings` e anos > 10 em `processed` (sem coluna de ano).
- Corretude numérica de EDA e agregações (existência e consistência apenas).

## 7. Correções priorizadas

| # | Correção | Esforço | Quem |
|---|---|---|---|
| 1 | Baixar ENEM 2016–2022 e Censo Escolar/Catálogo | 30–60 + processamento | Humano |
| 2 | Rotular `amostra_rotulagem.csv` (≥50, ideal 200) | 30–40 | Humano |
| 3 | Corrigir A2 (não sobrescrever rótulos) antes de rodar `run_fase5` | 5 | Claude Code |
| 4 | Fixar `scipy`/`numpy` em `requirements.txt` | 5 | Claude Code |
| 5 | Criar `CLAUDE.md` e `docs/lgpd.md`; implementar `assert_sem_nomes` | 20 | Claude Code |
| 6 | Corrigir componente de talento e supressão da taxa (A3) | 30 | Claude Code |
| 7 | Rodar T2.11 (`dim_*`/`fato_*`) com asserts; resolver conflito `dim_escola` × colunas proibidas | 40 | Claude Code |
| 8 | Rankings: uma métrica por município/recorte, coluna `ano`, desempate | 40 | Claude Code |
| 9 | `run_fase2..6` por ano + gerador do notebook Colab + execução com tempos | 60 | Claude Code |
| 10 | `docs/dicionario_dados`, `linhagem`, `contrato_dados`, `relatorio_resultados` | 60 | Claude Code |
| 11 | Reexecutar modelagem e atualizar docs defasados; atualizar `progresso.md` | 30 | Claude Code |
| 12 | OBMEP 2020–2023, OBI 2018, ONHB; definir RF/RN em documento | 60+ | Humano + Claude Code |
| 13 | Commitar o projeto (com trava de `data/processed` no `.gitignore`); remover e-mail do User-Agent | 10 | Humano decide / Claude Code |
