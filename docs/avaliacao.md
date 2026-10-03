# Avaliação da modelagem (Fases 4 e 5: T3.2–T3.5 e T4.1–T4.5)

Gerado por `python src/avaliacao.py` (que chama `src/modelagem.py`). Todos os números abaixo vêm da última execução.

## 0. Escopo, entradas e desvios do pedido

- **Entradas:** `data/processed/` hoje só contém `linkage_resultado.parquet` e `linkage_revisao_manual.csv`. As tabelas `dim_*`/`fato_*` (T2.11) **não existem**, porque T1.13 (escolas do Censo) está bloqueada (DP-2). Usei os agregados já validados de `data/interim/` (`agg_medalhas_municipio`, `agg_proficiencia_{municipio,escola}`, `dim_municipio_base`) e o `enem_all.parquet` (agregado por município, sem nome de aluno em nenhuma saída). Quando T2.11 sair, basta trocar as leituras em `modelagem.py`.
- **INSE não entra no modelo:** os ids de escola/município do Saeb são máscaras e não ligam ao código INEP/IBGE (`docs/lacunas_saeb.md` §1). O papel de INSE/renda é feito pelo proxy de renda do ENEM (mediana da renda per capita em SM, suavizada; o % ≤ 1,5 SM do RF 5.4 é publicado mas **satura**: média de ~95%), por município.
- **ENEM só tem município de *prova*** (≈ 1,8 mil municípios). Para os demais usei o município da *escola* (só 2023, único ano com escola e renda no mesmo registro), quando há ≥ 10 participantes. Resultado: renda em **4571** de 5571 municípios; **4571** têm os três componentes do índice.
- **Só 2023 tem sexo e renda junto com nota** no ENEM; por isso os recortes de sexo e faixa de renda nos rankings são `enem_media_geral_2023`.
- **Medalhas:** OBMEP (2016–2019, 2024, 2025) e OBI (sem 2018); ONHB não coletada; OBMEP 2020–2023 ausente. Conta Ouro+Prata+Bronze em EF2/EM; Menção Honrosa fora.
- **Escolas:** só Saeb/Ideb 2025 (nota padronizada e Ideb) e medalhas por escola vinculadas automaticamente (`link_status = auto`). O modelo de escolas usa renda e porte do **município** (não há INSE por escola), então é um ajuste ecológico.

## 1. Índice de potencial (T3.2)

Componentes e pesos (`config/pesos.yaml`, com justificativa): talento 0.5, qualidade da rede 0.2, vulnerabilidade 0.3. Normalização por **percentil (rank)**: as taxas de medalha são muito assimétricas e cheias de zeros, e min-max ficaria dominado por poucos outliers (o efeito da escolha é medido na §6). Taxa de medalhas com encolhimento bayesiano (a = 20,000 hab.) para municípios pequenos não liderarem por acaso. Pesos renormalizados entre os componentes disponíveis (mínimo 3 componentes: municípios sem renda no ENEM, ou sem Saeb/Ideb publicado, **ficam sem índice**; com mínimo 2 a renormalização fazia municípios sem dado de renda liderarem o ranking, um viés de dado faltante visto no T4.4). Índice calculado para **4571** de 5571 municípios.

**Decisão de negócio em aberto:** o sinal de `qualidade_rede` é +1 (rede forte = ambiente que forma candidatos aptos). Se o IP preferir priorizar redes fracas, mude para −1 em `pesos.yaml`.

## 2. Clusterização (T3.3 / T4.1)

K-Means, k de 3 a 8, escolhido por silhouette: **k = 3** (silhouette 0.290, Davies-Bouldin 1.330). Perfis em `docs/clusters.md`.

| k | silhouette | davies_bouldin |
|---|---|---|
| 3 | 0.2902 | 1.3303 |
| 4 | 0.231 | 1.307 |
| 5 | 0.2285 | 1.2996 |
| 6 | 0.2244 | 1.2947 |
| 7 | 0.2239 | 1.279 |
| 8 | 0.2306 | 1.2695 |

Leitura: silhouette de 0.29 indica estrutura **fraca**; os municípios formam mais um contínuo que grupos separados. Use os clusters como agrupamento para comparar municípios parecidos, não como categorias naturais. O Davies-Bouldin é menor em k = 8 (diferença pequena entre os k), diferente do k do silhouette: os critérios não apontam um k claramente melhor. Escolhi k por silhouette conforme o pedido; k = 3 também é o mais fácil de explicar.

## 3. Modelo de expectativa e métricas de regressão (T3.4 / T4.1)

Resíduo > 0 = acima do esperado dado renda e porte. `acima_do_esperado` = resíduo padronizado > 1 (em `residuos.parquet`). R²/RMSE/MAE por validação cruzada de 5 dobras (as de ajuste estão no código).

| modelo | n | R² (ajuste) | R² (CV-5) | RMSE (CV-5) | MAE (CV-5) |
|---|---|---|---|---|---|
| medalhas_municipio (NB, exposicao=pop) | 4571 | 0.587 | 0.585 | 45.901 | 7.336 |
| saeb_padr_municipio (OLS) | 4571 | 0.177 | 0.177 | 0.489 | 0.371 |
| enem_media_municipio (OLS) | 1811 | 0.691 | 0.69 | 18.252 | 14.642 |
| saeb_padr_escola (OLS, 2025) | 48625 | 0.232 | 0.232 | 0.695 | 0.512 |

Coeficientes:

| modelo | termo | coef | p |
|---|---|---|---|
| medalhas_municipio (NB, exposicao=pop) | const | 4.001 | 0.0 |
| medalhas_municipio (NB, exposicao=pop) | renda_pc_sm | 2.4652 | 0.0 |
| medalhas_municipio (NB, exposicao=pop) | log_pop | -0.1726 | 0.0 |
| medalhas_municipio (NB, exposicao=pop) | alpha | 1.5566 | 0.0 |
| saeb_padr_municipio (OLS) | const | 4.8387 | 0.0 |
| saeb_padr_municipio (OLS) | renda_pc_sm | 1.5807 | 0.0 |
| saeb_padr_municipio (OLS) | log_pop | -0.0395 | 0.0 |
| enem_media_municipio (OLS) | const | 400.6091 | 0.0 |
| enem_media_municipio (OLS) | renda_pc_sm | 127.0777 | 0.0 |
| enem_media_municipio (OLS) | log_pop | 7.3011 | 0.0 |
| saeb_padr_escola (OLS, 2025) | const | 5.3353 | 0.0 |
| saeb_padr_escola (OLS, 2025) | renda_pc_sm | 1.5198 | 0.0 |
| saeb_padr_escola (OLS, 2025) | log_pop | -0.0573 | 0.0 |
| saeb_padr_escola (OLS, 2025) | rede_detalhe_federal | 1.1889 | 0.0 |
| saeb_padr_escola (OLS, 2025) | rede_detalhe_municipal | -0.07 | 0.0 |
| saeb_padr_escola (OLS, 2025) | etapa_EM | -0.6302 | 0.0 |

Contagem de entidades acima do esperado (resíduo padronizado > 1):

| tipo | metrica | sum | size |
|---|---|---|---|
| escola | saeb_padronizada | 6009 | 48625 |
| municipio | enem_media | 290 | 1811 |
| municipio | medalhas | 458 | 4571 |
| municipio | saeb_padronizada | 611 | 4571 |

Leitura e cuidados:

- **Medalhas:** R² (CV) = 0.59 em escala de contagem; essa métrica é dominada pelas poucas cidades grandes (RMSE = 46 contra MAE = 7.3). Use o resíduo **padronizado** (Pearson da binomial negativa; α = 1.56, forte superdispersão), não o absoluto, para achar municípios acima do esperado. O coeficiente de renda é positivo: municípios com maior renda per capita mediana têm mais medalhas por habitante, então o resíduo já desconta parte da vantagem de renda.
- **Proficiência:** renda + porte explicam pouco do Saeb (R² CV = 0.18 por município, 0.23 por escola) e bastante do ENEM por município (R² CV = 0.69). Há muita variação entre escolas/municípios de contexto parecido, e é ela que o resíduo captura; mas o modelo é um controle grosseiro: resíduo positivo pode refletir fatores omitidos (INSE real da escola, rede, localização), não só desempenho acima do esperado.
- Modelos de escola usam renda e porte do município; escolas do mesmo município compartilham o mesmo contexto. `rede_detalhe_federal` tem coeficiente grande (escolas federais selecionam alunos).
- Os erros do modelo variam por região e porte (ver §7): resíduos entre regiões diferentes não são diretamente comparáveis.

## 3b. Formato de `rankings.parquet` e `residuos.parquet`

`rankings.parquet`: `entidade_id` (município IBGE 7 / escola INEP 8, string), `tipo` (`municipio`/`escola`), `recorte` (`geral`, `etapa=EF2|EM`, `sexo=F|M`, `renda=ate_1_5sm|acima_1_5sm`), `metrica`, `valor`, `rank` (1 = maior valor dentro de `tipo`+`recorte`+`metrica`; inclusive em `pct_renda_pc_le_1_5` e `renda_pc_mediana_sm`, onde rank 1 = maior % / maior renda, ou seja, **não** é o mais vulnerável) e `n` (base da supressão). Chave única `(entidade_id, tipo, recorte, metrica)`: uma métrica por entidade por recorte. Contagens/taxas de medalha só aparecem onde há ≥ 10 medalhas; recortes de sexo e renda são só ENEM 2023 e com ≥ 10 participantes.
`rankings.parquet` tem 196,956 linhas; métricas por recorte: escola/etapa=EF2: ideb, residuo_saeb_padronizada, saeb_padronizada; escola/etapa=EM: ideb, residuo_saeb_padronizada, saeb_padronizada; escola/geral: n_medalhas; municipio/etapa=EF2: ideb, medalhas_por_100k, saeb_padronizada; municipio/etapa=EM: ideb, medalhas_por_100k, saeb_padronizada; municipio/geral: enem_media_geral, indice_potencial, medalhas_por_100k, pct_renda_pc_le_1_5, renda_pc_mediana_sm; municipio/renda=acima_1_5sm: enem_media_geral_2023; municipio/renda=ate_1_5sm: enem_media_geral_2023; municipio/sexo=F: enem_media_geral_2023; municipio/sexo=M: enem_media_geral_2023.
`residuos.parquet`: `entidade_id`, `tipo`, `metrica`, `etapa`, `modelo`, `observado`, `esperado`, `residuo`, `residuo_padronizado`, `acima_do_esperado` (> 1 desvio), `rank_residuo`.
`municipio_features.parquet` (extra): todas as features, componentes, índice e cluster por município.

## 4. Qualidade do matching escola ↔ medalhista (T4.1)

`data/processed/amostra_rotulagem.csv`: **200** pares (escola da lista de medalhistas → escola INEP proposta), estratificados por faixa de `link_score`, com coluna `correto` **vazia** para rotular. Unidade = escola distinta por (olimpíada, nome normalizado, município).

| faixa_similaridade | n_amostra | n_populacao |
|---|---|---|
| <60 | 25 | 2886 |
| 60-70 | 25 | 1784 |
| 70-80 | 25 | 2979 |
| 80-85 | 25 | 1943 |
| 85-90 | 25 | 3506 |
| 90-95 | 25 | 1925 |
| 95-<100 | 25 | 2074 |
| 100 | 25 | 22571 |

**Como rotular** (coluna `correto`):

- Linhas `auto` ou `revisao` (há candidato em `co_entidade`/`no_escola_cand`): `1` se o candidato é a mesma escola; `0` se não é. Se for `0` e você souber a escola certa, informe o código em `co_entidade_correta`. Os candidatos 2 e 3 estão nas colunas `cand2_*`/`cand3_*`.
- Linhas `sem_match` (sem candidato): `1` se é correto não vincular (a escola não existe na base / não dá para identificar); `0` se existia escola correta (informe `co_entidade_correta`).
- Se rotular só parte (ex.: 50 linhas), as não rotuladas são ignoradas; documente quantas.

**Cálculo:** `from avaliacao import precisao_recall; precisao_recall()` (`src/avaliacao.py`). Devolve precisão e recall em dois cenários (`auto` e `auto+revisao`), brutos e **ponderados** pelo tamanho de cada faixa (a amostra é estratificada, então a taxa bruta não estima a população), e a precisão do `auto` por faixa. Testada com rótulos sintéticos (`teste_precisao_recall()`); **os números reais aguardam sua rotulagem**.

**Status:** pendente de rotulagem humana.

## 5. Validação de negócio com o IP (T4.2 / T4.5)

Sem dado do IP. Gerado `docs/validacao_negocio_template.md` (cidades a comparar + o que pedir ao IP) e `docs/ata_validacao_ip.md` (ata da reunião). **Status: pendente de dado e de reunião.**

## 6. Sensibilidade dos pesos (T4.3)

Cada peso variado em −20%, 0 e +20% (27 combinações, 26 diferentes da base), mais zerar cada componente (stress test) e a normalização min-max. Pesos renormalizados para somar 1. `retencao_topN` = fração do top-N do cenário base que continua no top-N; `spearman_topN` = correlação de rank dentro do top-N base.

| index | spearman_geral | retencao_top50 | retencao_top100 | retencao_top200 | spearman_top100 |
|---|---|---|---|---|---|
| min | 0.968 | 0.82 | 0.88 | 0.82 | 0.881 |
| mean | 0.992 | 0.937 | 0.933 | 0.914 | 0.961 |
| max | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |

Pior caso entre as variações de ±20%: `±20% 0.8/0.8/1.2`.

Stress tests (peso zero) e normalização alternativa:

| cenario | spearman_geral | retencao_top50 | retencao_top100 | retencao_top200 | spearman_top100 |
|---|---|---|---|---|---|
| peso 0 em talento | 0.376 | 0.5 | 0.46 | 0.445 | 0.633 |
| peso 0 em qualidade_rede | 0.942 | 0.58 | 0.61 | 0.73 | 0.702 |
| peso 0 em vulnerabilidade | 0.892 | 0.22 | 0.22 | 0.31 | 0.475 |
| normalizacao min-max (pesos base) | 0.495 | 0.54 | 0.62 | 0.665 | 0.73 |

Leitura: nas variações de ±20% o ranking geral é estável (Spearman ≥ 0.97) e o top-100 retém 88%–100%. O top-N é mais sensível que o ranking inteiro. Nos stress tests, zerar talento ou vulnerabilidade derruba a retenção do top-100 para 46% e 22%: o top depende desses dois componentes. **A escolha da normalização pesa mais que ±20% nos pesos:** com min-max o Spearman com o índice base cai para 0.49 (retenção do top-100: 62%), porque a taxa de medalhas é muito assimétrica e o min-max a comprime. Por isso a normalização por rank é a escolhida.

## 7. Checagem de viés (T4.4)

### Por região

| regiao | municipios | indice_medio | pct_top10 | pct_tres_componentes | pct_renda_escola | razao_top10_vs_esperado |
|---|---|---|---|---|---|---|
| CO | 414 | 0.44 | 2.42 | 100.0 | 60.87 | 0.24 |
| N | 403 | 0.43 | 4.47 | 100.0 | 39.45 | 0.45 |
| NE | 1620 | 0.49 | 12.9 | 100.0 | 59.26 | 1.29 |
| S | 883 | 0.49 | 6.23 | 100.0 | 71.46 | 0.62 |
| SE | 1251 | 0.51 | 13.27 | 100.0 | 60.59 | 1.33 |

Kruskal-Wallis do índice entre grupos: H = 138.9, p = 4.86e-29. `razao_top10_vs_esperado` = 1 significa participação no top-10% igual à proporção de municípios.
Resíduo padronizado médio dos modelos (≠ 0 indica viés sistemático do modelo de expectativa):

| regiao | enem_media | medalhas | saeb_padronizada |
|---|---|---|---|
| CO | -0.588 | -0.38 | -0.019 |
| N | -1.135 | -0.197 | -0.736 |
| NE | 0.298 | -0.061 | -0.048 |
| S | -0.439 | -0.114 | 0.343 |
| SE | 0.58 | 0.354 | 0.064 |

### Por porte do município

| porte | municipios | indice_medio | pct_top10 | pct_tres_componentes | pct_renda_escola | razao_top10_vs_esperado |
|---|---|---|---|---|---|---|
| 100-500k | 278 | 0.4 | 3.6 | 100.0 | 0.0 | 0.36 |
| 20-50k | 1050 | 0.45 | 10.67 | 100.0 | 24.29 | 1.07 |
| 50-100k | 338 | 0.44 | 7.99 | 100.0 | 0.89 | 0.8 |
| <=20k | 2864 | 0.51 | 10.68 | 100.0 | 87.36 | 1.07 |
| >500k | 41 | 0.48 | 7.32 | 100.0 | 0.0 | 0.73 |

Kruskal-Wallis do índice entre grupos: H = 230.7, p = 9.28e-49. `razao_top10_vs_esperado` = 1 significa participação no top-10% igual à proporção de municípios.
Resíduo padronizado médio dos modelos (≠ 0 indica viés sistemático do modelo de expectativa):

| porte | enem_media | medalhas | saeb_padronizada |
|---|---|---|---|
| 100-500k | -0.071 | -0.029 | 0.025 |
| 20-50k | 0.069 | -0.059 | 0.034 |
| 50-100k | 0.087 | -0.046 | 0.102 |
| <=20k | -0.146 | 0.022 | -0.029 |
| >500k | -0.281 | 0.691 | 0.131 |

### Por sexo

- **Medalhistas: não mensurável.** As listas OBMEP/OBI não trazem sexo; não inferi sexo pelo nome. Pedir sexo à OBMEP/IP ou usar o dado agregado do IP.
- ENEM 2023 (concluintes, 1746 municípios com ≥ 10 de cada sexo): média geral F = 539.6, M = 546.7; diferença média por município (M − F) = 3.7 pontos; M > F em 67% dos municípios; 61% dos participantes são mulheres.
- Implicação: o índice não usa sexo, mas o componente de talento (olimpíadas) pode herdar desigualdade de participação por sexo, que não conseguimos medir aqui.

### Viés estrutural do índice

- Spearman(índice, log população) = -0.290. Spearman(taxa suavizada, log pop) = -0.307; taxa bruta = 0.142.
- Participação no top-10% do índice difere por região (razão vs. esperado de 0.24 a 1.33) e por porte (0.36 a 1.07); NE e SE ficam acima de 1 e CO, N e S abaixo. Isso reflete os dados (medalhas e renda), mas é um efeito a explicar ao IP, não uma propriedade neutra.
- Municípios sem ENEM suficiente (< 10 participantes) ou sem Saeb/Ideb ficam **sem índice** (`min_componentes: 3`). Em `pct_renda_escola`: a renda vem do município da escola (2023) em boa parte dos municípios pequenos (fonte menos comparável, suavizada); filtrar por `fonte_renda` em `municipio_features.parquet` para testar a robustez.
- Viés sistemático do modelo de expectativa: enem_media — maior desvio na região N (-1.13 desvios); medalhas — maior desvio na região CO (-0.38 desvios); saeb_padronizada — maior desvio na região N (-0.74 desvios). Preferir comparar resíduos dentro da mesma região.
- Medalhas OBMEP 2020–2023 e ONHB ausentes: subestima municípios cujo talento aparecia nesses anos.

## 8. Lacunas e riscos dos resultados

- INSE por município indisponível; renda é proxy por faixa declarada de quem presta ENEM (viés de seleção: só quem faz a prova).
- Renda por município de prova (≈ 1,8 mil) ou de escola (2023): mistura de fontes sinalizada em `fonte_renda` (`municipio_features.parquet`).
- Sem Saeb 2025 oficial; edições 2023/2025 do Ideb agregadas por município sem peso por matrícula (média simples das redes).
- O modelo de expectativa é descritivo, não causal.
- Matching e validação de negócio dependem de trabalho humano (§4, §5).

## 9. Critério de aceite

| Entregável | Status |
|---|---|
| `data/processed/rankings.parquet` | gerado |
| `data/processed/residuos.parquet` | gerado |
| `config/pesos.yaml` | gerado, com justificativa |
| `docs/avaliacao.md` | este documento |
| `data/processed/amostra_rotulagem.csv` | gerada (rotulagem pendente) |
| `docs/clusters.md`, `docs/validacao_negocio_template.md`, `docs/ata_validacao_ip.md` | gerados |
