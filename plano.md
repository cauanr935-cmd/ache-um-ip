# Plano de Execução — Sprint de Dados (CRISP-DM) · Ache um IP
Meta: concluir em **2 horas** com o Claude Code. Baseado na "Divisão de Tasks" (Cauan, 24/09/2026).

---

## PARTE A — O que VOCÊ precisa fazer antes (≈ 15 min)

O Claude Code não deve baixar os arquivos grandes do INEP no meio da execução: é lento e os links mudam a cada publicação. **Baixe você, em paralelo, enquanto configura o resto.**

### A1. Downloads (todos na página oficial de Microdados do INEP)
Página raiz: https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados

| # | Base | Página | O que baixar |
|---|------|--------|--------------|
| 1 | **ENEM** (RN 6: últimos 10 anos) | https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/enem | Edições **2016 a 2025** (a página lista até 2025). Cada ZIP já traz o dicionário. Padrão de link: `https://download.inep.gov.br/microdados/microdados_enem_AAAA.zip` |
| 2 | **Saeb** | https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/saeb | **Saeb 2023** (aluno + escola). A página não mostrava a edição 2025 quando consultei; confira se saiu (T1.5). Padrão: `https://download.inep.gov.br/microdados/microdados_saeb_2023.zip` |
| 3 | **Censo Escolar** (catálogo de escolas, tabela-ponte) | https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-escolar | **Censo Escolar 2025** (só precisa do arquivo de escolas) |
| 4 | **Catálogo de Escolas** (alternativa leve ao Censo) | https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/inep-data/catalogo-de-escolas | Planilha/CSV completa |
| 5 | **Ideb / indicadores** | https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/indicadores-educacionais | Ideb por escola e município, **INSE** e **Taxa de Rendimento** (decisão T1.7: INEP direto como fonte canônica) |

Dicas:
- **Se o tempo apertar, priorize:** Saeb 2023, Censo Escolar 2025, Ideb, e ENEM 2025 → 2023 → 2021 → 2019 → 2016 (nessa ordem). Os demais anos entram se baixarem a tempo.
- Os arquivos de ENEM têm vários GB cada. Deixe os downloads rodando em segundo plano e **não os descompacte à mão**: o Claude Code lê direto do ZIP/CSV com DuckDB.
- Coloque tudo em `Ache-um-IP/data/raw/inep/` (crie a pasta). Mantenha os nomes originais dos ZIPs.

### A2. Listas de medalhistas (a parte menos garantida)
Não verifiquei as URLs de OBMEP / OBI / ONHB. Faça uma destas opções:
1. **Melhor para 2h:** baixe manualmente as listas de premiados dos últimos anos de cada olimpíada (PDF/XLSX/HTML) e salve em `data/raw/olimpiadas/{obmep,obi,onhb}/`.
2. Ou deixe o Claude Code tentar localizar e raspar (T1.8–T1.10) com limite de 10 min por olimpíada; se falhar, ele registra a lacuna e segue.

### A3. IBGE (o Claude Code consegue baixar, são arquivos pequenos)
Se o ambiente dele tiver internet: API de localidades, população (estimativas/Censo 2022 via SIDRA) e malha municipal em `geoftp.ibge.gov.br`. Se não tiver, baixe você a **malha municipal** e a **população por município** e salve em `data/raw/ibge/`.

### A4. Preparar o Claude Code
1. Crie o repositório e copie este arquivo para a raiz como `PLANO.md`.
2. Instale/abra o Claude Code na pasta do repositório (`claude`).
3. Crie o `CLAUDE.md` com o bloco da seção **E** deste arquivo.
4. Instale dependências (ou peça para ele): `pip install pandas pyarrow duckdb rapidfuzz unidecode requests beautifulsoup4 scikit-learn statsmodels nbformat jupytext`.
5. Para rodar sem interrupções, libere as permissões de edição de arquivos e execução de `python`/`pip`/`duckdb` nas configurações do Claude Code. Faça isso só dentro da pasta do projeto.
6. **Para paralelizar, peça explicitamente subagentes** ("use um subagente por frente"). O Claude Code só abre subagentes quando você pede.

### A5. Coisas que só você (ou o IP) resolvem
- **T1.17 / T1.18:** acesso e anonimização da base interna do Instituto Ponte. Sem isso, T4.2 fica como "pendente de dado".
- **T3.1:** decidir em 5 min o escopo da modelagem (proposta já pré-aprovada abaixo).
- **T4.5:** reunião de validação com o IP (fora das 2h).
- **T2.10 (LGPD):** confirmar a política de retenção sugerida.

---

## PARTE B — Decisões já tomadas para caber em 2h

1. **Governança:** o Claude Code escreve `.py` modulares em `src/` e **gera** o notebook Colab único a partir deles (jupytext/nbformat). Nada de lógica solta em célula.
2. **Motor de dados:** DuckDB lendo CSV/ZIP direto, selecionando só as colunas necessárias, gravando Parquet particionado por ano. Nunca carregar o ENEM inteiro em pandas.
3. **ENEM:** granularidade **município** (sem código de escola pós-2015 — T1.4).
4. **Olimpíadas:** apenas OBMEP, OBI e ONHB. Demais olimpíadas → `docs/backlog_olimpiadas.md` (T1.12).
5. **Modelagem (T3.1 fechado):** índice composto + K-Means/hierárquico + regressão de resíduos. Sem modelos mais complexos.
6. **LGPD (T2.10, padrão):** `dim_aluno` guarda **hash do nome + ano + olimpíada + medalha + escola/município**; nome em claro só em arquivo de trabalho em `/interim`, fora do versionamento (`.gitignore`), com política de retenção documentada.
7. **Tasks dependentes de humano** viram **entregáveis-esqueleto** (documento com perguntas e o que falta): T1.15, T1.16, T1.17, T1.18, T4.2, T4.5.

---

## PARTE C — Cronograma de 2 horas

| Janela | Fase | Quem faz | Saída |
|--------|------|----------|-------|
| 0:00–0:15 | Fase 0 + downloads | Você (downloads) + Claude Code (T0.1–T0.3) | Repo, convenções, setup |
| 0:15–0:50 | Fase 2 — coleta e EDA | **5 subagentes em paralelo** | EDA por frente, dicionários, `interim/*.parquet` |
| 0:50–1:20 | Fase 3 — pré-processamento | 2 subagentes (A: chaves/linkage/medalhistas; B: agregações/renda/EF2-EM) | `processed/dim_*`, `fato_*` |
| 1:20–1:40 | Fase 4 — modelagem | 1 agente | Índice, clusters, resíduos, rankings |
| 1:40–1:55 | Fases 5 e 6 | 1 agente | Métricas, notebook, dicionário, linhagem, contrato |
| 1:55–2:00 | Buffer / checagem | Você | Executar o notebook, conferir checklist da Parte D |

Regra: se uma task passar de 150% do tempo, o Claude Code **registra a lacuna em `docs/lacunas.md` e segue**. Nunca bloquear a sprint por uma fonte.

---

## PARTE D — Tasks por fase, com critério de aceite

### Fase 0 (Claude Code, sozinho)
- **T0.1** Criar `data/{raw,interim,processed}`, `src/`, `notebooks/` (`00_setup`, `02_coleta`, `03_prep`, `04_modelagem`, `05_avaliacao`, `06_deploy`), `docs/`. *Aceite: árvore criada, `.gitignore` com `data/raw` e `data/interim`.*
- **T0.2** `docs/convencoes.md`: UTF-8, `snake_case` minúsculo, município = IBGE 7 dígitos (string), escola = `co_entidade` INEP 8 dígitos (string), ano como int.
- **T0.3** `src/setup.py` + célula de setup reproduzível (requirements.txt fixado).

### Fase 2 — um subagente por frente (rodar em paralelo)
**Frente ENEM** — T1.1–T1.4
- Inventariar ZIPs em `data/raw/inep/`; listar quais dos 10 anos estão presentes e quais faltam.
- Dicionário de variáveis (`docs/dicionario_enem.md`): `CO_MUNICIPIO_ESC`, `CO_MUNICIPIO_PROVA`, `TP_ESCOLA`, `TP_SEXO`, `TP_ST_CONCLUSAO`, notas por área, `Q005`, `Q006`. Atenção: o layout das colunas muda entre anos; mapear por ano.
- Gerar `interim/enem_{ano}.parquet` só com essas colunas.
- EDA: volumetria por ano/UF, % nulos, distribuição de notas, cobertura de escola pública.
- Registrar a limitação T1.4 em `docs/lacunas.md`.
- *Aceite: Parquet por ano + `eda_enem.md` com tabelas.*

**Frente Saeb/indicadores** — T1.5–T1.7
- Ler Saeb 2023 (aluno 9EF e 3EM + escola). Registrar se a edição 2025 foi publicada; se só houver via site, **não raspar**: abrir item em `docs/decisoes_pendentes.md`.
- EDA: proficiência LP/MT por escola, cobertura por município, recortes 9º EF2 e 3ª série EM.
- Definir fonte canônica (INEP direto) para Ideb, INSE e Taxa de Rendimento e converter para Parquet.
- *Aceite: `interim/saeb_escola.parquet`, `interim/ideb.parquet`, `interim/inse.parquet`, `interim/taxa_rendimento.parquet`.*

**Frente Olimpíadas** — T1.8–T1.12
- Parsers por olimpíada/ano a partir de `data/raw/olimpiadas/` (ou scraping com timeout, se autorizado).
- Esquema comum: `olimpiada, ano, medalha, nome, escola_nome, municipio_nome, uf`.
- T1.11: relatório de quais listas trazem escola/município (quanto cobre cada uma).
- T1.12: `docs/backlog_olimpiadas.md` com OBF, OBQ, OBA, OBM, OFMAT, Maratona Cactus, MANDACARU.
- *Aceite: `interim/medalhistas.parquet` + matriz de cobertura por olimpíada/ano.*

**Frente Chaves e Geo** — T1.13–T1.14
- Tabela-ponte de escolas (código INEP ↔ nome, município, UF, rede, localização) a partir do Censo Escolar/Catálogo.
- Municípios IBGE (código 7 dígitos, nome, UF, população) + malha territorial guardada para o mapa da próxima sprint.
- *Aceite: `interim/dim_escola_base.parquet`, `interim/dim_municipio_base.parquet`, malha em `data/raw/ibge/`.*

**Frente MEC/Secretarias + Interno IP** — T1.15–T1.18 (docs)
- T1.15/T1.16: levantamento web curto (≤15 min) do que MEC/Secretarias publicam e sobreposição com INEP.
- T1.17/T1.18: **não acessar dados reais.** Gerar `docs/dados_internos_ip.md` com o esquema esperado (perfil, escola de origem, cidade, ano de ingresso), perguntas para a coordenação e proposta de anonimização.
- *Aceite: dois documentos curtos com lacunas explícitas.*

**Consolidação — T1.19** (após as frentes)
- `docs/relatorio_qualidade_viabilidade.md`: matriz fonte × RF, lacunas, riscos.

### Fase 3 — Pré-processamento
- **Subagente A (chaves e matching):** T2.1 padronização de chaves · T2.2 normalização de texto (caixa alta, `unidecode`, expansão EE/EM/EEEF/CIEP) · **T2.3 record linkage** medalhista → escola INEP: blocking por município, `rapidfuzz` (token_set_ratio), limiar configurável (ex.: ≥90 auto, 80–90 fila de revisão), saída `processed/linkage_revisao_manual.csv` · T2.4 deduplicação entre anos e olimpíadas com contagem de medalhas.
- **Subagente B (indicadores):** T2.5 proxy de renda ≤ 1,5 SM a partir de `Q006`/`Q005` (faixa declarada, usar o ponto médio da faixa e dividir por moradores; documentar a fórmula) · T2.6 flag de rede + filtro de escola pública · T2.7 recortes EF2/EM · T2.8 agregações por escola e município · T2.9 nulos, outliers e **supressão estatística** (limite mínimo de participantes configurável, padrão n<10).
- **Depois dos dois:** T2.10 LGPD (aplicar política da Parte B) · T2.11 montar `dim_municipio`, `dim_escola`, `dim_aluno`, `fato_desempenho`, `fato_medalhas`.
- *Aceite: chaves únicas verificadas por asserts; taxa de linkage reportada; zero nomes em claro em `processed/`.*

### Fase 4 — Modelagem (T3.1 já fechado)
- **T3.2** Índice de potencial por município: talento (medalhas per capita) + qualidade da rede (Saeb/Ideb) + vulnerabilidade (INSE/renda). Normalização min-max ou rank (documentar), pesos em `config/pesos.yaml` com justificativa.
- **T3.3** Clusterização (K-Means; testar k=3..8 e escolher por silhouette).
- **T3.4** Regressão de medalhistas e proficiência contra INSE e porte; resíduos positivos = escolas "acima do esperado".
- **T3.5** Rankings por município e escola, por recorte (etapa, sexo, renda), em formato longo: `entidade_id, recorte, metrica, valor, rank`.

### Fase 5 — Avaliação
- **T4.1** Silhouette, Davies-Bouldin; R², RMSE, MAE; precisão/recall do matching com **amostra de ~200 registros**. Claude Code gera a amostra em `processed/amostra_rotulagem.csv`; **você rotula** (30–40 min fora do caminho crítico, ou rotule 50 se faltar tempo e documente).
- **T4.2** Esqueleto de validação com cidades do IP (pendente de dado).
- **T4.3** Sensibilidade dos pesos (variar ±20% e medir estabilidade do top-N, Spearman).
- **T4.4** Viés por sexo, região e porte.
- **T4.5** Template de ata da reunião de validação.

### Fase 6 — Deploy
- **T5.1** Exportar Parquet + CSV versionados (`processed/v1/`); avaliar DuckDB único (`ache_um_ip.duckdb`) e recomendar.
- **T5.2** `docs/dicionario_dados.md` e `docs/linhagem.md`.
- **T5.3** Gerar `notebooks/ache_um_ip_colab.ipynb` a partir de `src/`, com tempo de execução por etapa. Células leem do Drive (`/content/drive/...`) e o download é opcional.
- **T5.4** Todas as etapas em funções (`run_fase2()`, `run_fase3()`...), parametrizadas por ano.
- **T5.5** `docs/contrato_dados.md`: schema estável, **uma métrica por município por recorte**, tipos e chaves (RF 4, 5, 6).
- **T5.6** `docs/relatorio_resultados.md` + roteiro de apresentação.

---

## PARTE E — Prompts prontos (cole no Claude Code)

### E0. `CLAUDE.md` (colocar na raiz)
```
# Projeto Ache um IP — Sprint de Dados (CRISP-DM)
- Fonte da verdade: PLANO.md. Siga as tasks T0.x–T5.x e os critérios de aceite.
- Prazo total: 2h. Se uma task estourar 150% do tempo, registre em docs/lacunas.md e siga.
- Código em src/ (módulos), notebook Colab é GERADO a partir de src/.
- Dados grandes: DuckDB + Parquet, nunca ler o ENEM inteiro no pandas.
- Chaves: município = IBGE 7 dígitos (str); escola = co_entidade INEP 8 dígitos (str).
- LGPD: nunca gravar nome de aluno em claro em data/processed.
- Nunca inventar dados. Fonte indisponível = registrar lacuna.
- Não acessar dados internos reais do Instituto Ponte.
- Ao concluir uma task, atualize docs/progresso.md (ID, status, arquivos gerados).
```

### E1. Prompt de partida
```
Leia PLANO.md e CLAUDE.md. Execute a Fase 0 agora. Depois, rode a Fase 2 usando
um subagente por frente (ENEM, Saeb/indicadores, Olimpíadas, Chaves e Geo,
MEC+Interno IP), em paralelo. Os microdados do INEP já estão em data/raw/inep/;
as listas de olimpíadas, se existirem, em data/raw/olimpiadas/. Ao terminar,
rode T1.19 e me mostre o relatório de lacunas antes de seguir para a Fase 3.
```

### E2. Fase 3
```
Fase 3 do PLANO.md. Use dois subagentes em paralelo: (A) T2.1–T2.4 e (B) T2.5–T2.9.
Depois una tudo em T2.10–T2.11. Valide chaves únicas com asserts e me reporte
a taxa de linkage dos medalhistas e o tamanho da fila de revisão manual.
```

### E3. Fases 4 a 6
```
Execute as Fases 4, 5 e 6 do PLANO.md em sequência. Use os pesos de config/pesos.yaml.
Gere a amostra de ~200 registros para eu rotular o matching. Ao final, gere o
notebook Colab único e rode-o de ponta a ponta localmente para registrar o tempo.
```

---

## PARTE F — Checklist final (últimos 5 min)

- [ ] `ache_um_ip_colab.ipynb` roda de ponta a ponta
- [ ] `processed/v1/` com Parquet + CSV das 5 tabelas (`dim_municipio`, `dim_escola`, `dim_aluno`, `fato_desempenho`, `fato_medalhas`)
- [ ] Nenhum nome de aluno em claro em `processed/`
- [ ] `docs/` com dicionário, linhagem, contrato de dados, relatório de qualidade e relatório de resultados
- [ ] `docs/lacunas.md` e `docs/decisoes_pendentes.md` lidos por você
- [ ] Pendências humanas anotadas: base do IP (T1.17/18/T4.2), reunião (T4.5), rotulagem (T4.1)

## Riscos (leia antes de começar)
1. **Download do ENEM** é o gargalo real; sem os arquivos locais, 10 anos não cabem em 2h. Por isso a ordem de prioridade na A1.
2. **Record linkage** é o maior risco técnico; o plano prevê fila de revisão manual em vez de perfeição.
3. **Listas de medalhistas** podem vir em PDF sem escola/município. Se vier assim, o vínculo aluno→território fica parcial e isso entra no relatório de viabilidade.
4. Links de download do INEP **mudam a cada publicação**; use a página oficial como referência, não os padrões de URL.