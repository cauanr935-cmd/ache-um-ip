# Progresso

| ID | Status | Arquivos gerados / observações |
|---|---|---|
| T0.1 | concluída | `data/{raw,interim,processed}`, `src/`, `notebooks/`, `docs/`, `config/`; `.gitignore` com `data/raw/`, `data/interim/`, `.venv/`. Os 6 notebooks nomeados no plano ainda não existem (gerados na T5.3). |
| T0.2 | concluída | `docs/convencoes.md` |
| T0.3 | concluída | `src/setup.py`, `requirements.txt` (versões fixadas; inclui `lxml` e `openpyxl`, usados pelo código, além da lista pedida). Ambiente: `.venv/` na raiz (o Python do sistema bloqueia `pip` por PEP 668). |
| T1.1 | concluída | `docs/lacunas_enem.md`: presentes 2023–2025; **ausentes 2016–2022** (7 de 10 anos) |
| T1.2 | concluída | `src/enem.py`, `data/interim/enem_{2023,2024,2025}.parquet`, `enem_all.parquet`; `docs/eda_enem.md` |
| T1.3 | concluída | `docs/dicionario_enem.md` (categorias lidas dos dicionários oficiais); `src/enem_docs.py` gera os 3 docs |
| T1.4 | concluída, com correção | `docs/lacunas_enem.md`. A premissa "sem código de escola nos anos recentes" é só parcialmente verdadeira: `RESULTADOS` 2024/2025 trazem `CO_ESCOLA` (mascarado p/ escolas <10 participantes), mas não há junção com perfil/renda. 2023 não tem código de escola. |
| T1.8 (OBMEP) | concluída, com lacunas | `src/coleta_obmep.py` → `data/interim/obmep_premiados.parquet` (329.796 linhas; 2016–2019, 2024, 2025); `docs/cobertura_obmep.md`; `docs/lacunas.md`. **2020–2023 ausentes**: as edições 16ª–18ª existem mas suas páginas não informam o ano (não inferido); `config/obmep_anos.yaml` aceita os anos confirmados. HTML bruto em `data/raw/olimpiadas/obmep/html/{ano}/`. 2016: só escolas públicas. |
| T1.5 | concluída, com ressalva | `src/saeb.py` → `data/interim/saeb_escola.parquet` (2017/2019/2021/2023 × EF2/EM, 224 mil linhas). **IDs de escola/município do Saeb são máscaras**: colunas `id_escola_saeb`/`id_municipio_saeb`, sem `co_entidade` (ver `lacunas_saeb.md` §1). `docs/eda_saeb.md` |
| T1.6 | concluída | Saeb 2025 não está na página oficial; não raspado. `docs/decisoes_pendentes.md` DP-1 |
| T1.7 | concluída, com lacunas | `src/ideb.py` → `ideb_escola.parquet` (498.809 linhas), `ideb_municipio.parquet` (206.273); chaves 8/7 dígitos. INSE: só o do Saeb; Taxa de Rendimento: só aprovação/indicador de rendimento via Ideb. `docs/lacunas_saeb.md` |
| T1.13 | **bloqueada** | Censo Escolar 2025 ausente; download do INEP falha em TLS. `dim_escola_base.parquet` NÃO gerada. DP-2 em `decisoes_pendentes.md` |
| T1.14 | concluída | `src/geo.py` → `dim_municipio_base.parquet` (5.571 municípios; população Censo 2022 + estimativa 2026); `data/raw/ibge/` com Localidades, SIDRA e malha 2025 |
| T1.8 (validação) | concluída | `src/medalhistas.py` valida o parquet da OBMEP contra o HTML bruto (contagem independente). Achado/correção: 2 linhas-placeholder (`---`) da OBMEP 2025 removidas no parser; 3 linhas sem nome na fonte (2016: 1, 2025: 2) descartadas de propósito |
| T1.9 (OBI) | concluída, com lacuna | `src/coleta_obi.py`; 5.485 linhas, 2016–2017 e 2019–2025. **2018 ausente**: a página da edição responde 404 na fonte. Raw em `data/raw/olimpiadas/obi/html/{ano}/` |
| T1.10 (ONHB) | **não coletada** | Sem lista pública por equipe (só notícias com totais; nominal em área logada/Google Drive). Não forçado. `docs/lacunas_olimpiadas.md` |
| T1.11 | concluída | `data/interim/medalhistas.parquet` (335.281 linhas: OBMEP + OBI), `docs/cobertura_olimpiadas.md` |
| T1.12 | concluída | `docs/backlog_olimpiadas.md` (OFMAT não identificada) |
| T1.15–T1.16 | concluída (pesquisa, sem raspagem) | `docs/mec_secretarias.md` |
| T1.17–T1.18 | esqueleto, pendente de dado e decisão | `docs/dados_internos_ip.md` (nenhum dado real acessado) |
| T1.19 | concluída | `docs/relatorio_qualidade_viabilidade.md` (matriz fonte × RF, 12 achados de qualidade, 12 lacunas, 10 riscos). RF 5.2 não consta na tabela de rastreabilidade e não foi avaliado. T1.13 segue bloqueada (DP-2) |
| T3.2 | concluída | `config/pesos.yaml` (pesos + justificativa), `src/modelagem.py` (índice por percentil/rank), `data/processed/municipio_features.parquet`. Entradas de `data/interim/` porque `processed/dim_*` não existe (T1.13/T2.11 pendentes). Índice só para municípios com os 3 componentes (4.571 de 5.571) |
| T3.3 | concluída | K-Means k=3..8, k=3 por silhouette (0,29, fraco); `docs/clusters.md` |
| T3.4 | concluída | `data/processed/residuos.parquet` (medalhas NB, Saeb e ENEM por município, Saeb por escola 2025). Sem INSE (ids Saeb mascarados): renda do ENEM como proxy |
| T3.5 | concluída | `data/processed/rankings.parquet` (formato longo, chave única entidade×tipo×recorte×métrica). Recortes sexo/renda só ENEM 2023 |
| T4.1 | parcial | métricas de cluster/regressão em `docs/avaliacao.md`; `data/processed/amostra_rotulagem.csv` (200 linhas) e `precisao_recall()` em `src/avaliacao.py`. **Pendente: rotulagem humana** |
| T4.2 | esqueleto, pendente de dado | `docs/validacao_negocio_template.md` |
| T4.3 | concluída | sensibilidade ±20% + stress + min-max em `docs/avaliacao.md` §6 |
| T4.4 | concluída | viés por região/porte/sexo em `docs/avaliacao.md` §7 (sexo dos medalhistas não mensurável) |
| T4.5 | esqueleto | `docs/ata_validacao_ip.md` |
