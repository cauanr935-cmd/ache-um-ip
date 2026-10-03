# Agregações por escola e município (T2.5–T2.9)

Gerado por `python src/agregacoes.py` (código em `src/agregacoes.py`, `rede.py`, `recortes.py`, `renda.py`).
Configs: `config/renda.yaml`, `config/recortes.yaml`, `config/supressao.yaml`. Saídas em `data/interim/agg_*.parquet`.
Chaves padronizadas: `co_municipio` (7 dígitos, str), `co_entidade` (8 dígitos, str), `ano` (int). **Nenhuma tabela contém nome de aluno** (assert no código).

## 1. Tabelas e chaves

| tabela | chave única | linhas | colunas |
|---|---|---|---|
| agg_enem_municipio | visao, co_municipio, ano, rede_grupo | 58331 | 31 |
| agg_proficiencia_escola | co_entidade, etapa, ano | 498814 | 17 |
| agg_proficiencia_municipio | co_municipio, etapa, ano, rede | 206273 | 15 |
| agg_proficiencia_uf | uf, etapa, ano, rede_grupo | 243 | 12 |
| agg_medalhas_municipio | co_municipio, ano, olimpiada, medalha, etapa, rede_grupo | 64738 | 11 |

Colunas:
- **agg_enem_municipio**: `visao`, `co_municipio`, `ano`, `rede_grupo`, `recorte`, `n`, `n_inscritos_total`, `n_renda_valida`, `pct_renda_pc_le_1_5_ponto_medio`, `pct_certamente_le_1_5`, `pct_possivelmente_le_1_5`, `pct_acima_1_5`, `mediana_renda_pc_sm`, `n_feminino`, `n_masculino`, `n_tp_escola_valido`, `pct_publica_tp_escola`, `mediana_renda_pc_reais`, `n_cn`, `media_cn`, `n_ch`, `media_ch`, `n_lc`, `media_lc`, `n_mt`, `media_mt`, `n_redacao`, `media_redacao`, `pct_redacao_zero`, `n_nota_zero_invalidada`, `suprimido`
- **agg_proficiencia_escola**: `co_entidade`, `etapa`, `ano`, `co_municipio`, `uf`, `rede`, `rede_grupo`, `rede_detalhe`, `no_escola`, `nota_saeb_lp`, `nota_saeb_mt`, `nota_saeb_padronizada`, `ideb`, `indicador_rendimento`, `taxa_aprovacao`, `n`, `suprimido`
- **agg_proficiencia_municipio**: `co_municipio`, `etapa`, `ano`, `uf`, `rede`, `rede_grupo`, `rede_detalhe`, `nota_saeb_lp`, `nota_saeb_mt`, `nota_saeb_padronizada`, `ideb`, `indicador_rendimento`, `taxa_aprovacao`, `n`, `suprimido`
- **agg_proficiencia_uf**: `uf`, `etapa`, `ano`, `rede_grupo`, `n_escolas`, `n_escolas_com_proficiencia`, `n`, `proficiencia_lp_media`, `proficiencia_mt_media`, `inse_aluno_medio`, `n_alunos_inse`, `suprimido`
- **agg_medalhas_municipio**: `co_municipio`, `ano`, `olimpiada`, `medalha`, `etapa`, `rede_grupo`, `n`, `n_alunos_unicos`, `no_escopo_ef2_em`, `suprimido`, `n_publicavel`

Notas de desenho:
- **agg_enem_municipio** reúne três `visao`: `perfil_prova` (município da **prova**; renda, sexo, % escola pública autodeclarada), `desempenho_prova` (notas por município da **prova**) e `desempenho_escola` (notas por município da **escola**, só quem tem escola recenseada). `rede_grupo` ∈ {`todas`, `publica`, `privada`}.
- Em 2024–2025 **perfil e notas não se juntam** (bases independentes do INEP): renda/sexo só existem em `perfil_prova` e notas só em `desempenho_*`. Não há nota × renda por aluno nem por escola.
- **agg_proficiencia_escola / _municipio** vêm do **Ideb** (códigos reais). Os IDs do Saeb microdados são fictícios e **não** são usados para escola ou município. O Ideb não informa nº de alunos: `n` é nulo e `suprimido` = sem nenhuma nota/Ideb divulgado (`ND` do INEP).
- **agg_proficiencia_uf** vem do `saeb_escola` (UF real; média ponderada por alunos presentes; `n` = soma de alunos presentes).
- **agg_medalhas_municipio**: `n` = registros de medalha (não pessoas), fonte: medalhistas.parquet (nome+UF normalizados, exato + fuzzy de chaves.py). `n_alunos_unicos` só existe se `medalhistas_enriquecido.parquet` (dedup) tiver `id_aluno`; senão é nulo. `n_publicavel` = `n` quando ≥ n_min, senão nulo (**usar esta coluna para exposição**; `n` bruto é de uso interno).

## 2. Rede (T2.6) — `src/rede.py`
`rede_grupo` (publica/privada/None) e `rede_detalhe` (federal/estadual/municipal/privada/outra/None), mesma função para todas as bases (`aplicar_rede(df, base)`; versão SQL `sql_rede_enem`). `filtrar_publica(df)` mantém só escola pública.
- ENEM: `tp_dependencia_adm_esc` (1 federal, 2 estadual, 3 municipal, 4 privada; Censo) tem prioridade; senão `tp_escola` de 2023 (2 pública, 3 privada, 1 não respondeu = desconhecida), caso em que `rede_detalhe` é nulo. **A fonte da rede difere entre linhas** (Censo × autodeclarado em 2023).
- Saeb: `publica`/`privada`. Ideb: Federal/Estadual/Municipal/Privada; `Pública` (agregado municipal) → publica sem detalhe.
- OBMEP: F/E/M → pública; P → privada; **C (≈530 linhas) tem significado não documentado pela fonte** → `rede_grupo` nulo, `rede_detalhe='outra'`. OBI não publica rede → desconhecida (`rede_grupo='desconhecida'` nas agregações de medalhas).

## 3. Recortes EF2/EM (T2.7) — `config/recortes.yaml`, `src/recortes.py`
- Saeb e Ideb: `etapa` nativa (EF2 = 9º ano / anos finais; EM).
- **ENEM = EM**: perfil e notas de 2023 restringidos a `tp_st_conclusao` ∈ {1, 2} (concluiu / conclui no ano). Em 2024–2025 `RESULTADOS` não tem `tp_st_conclusao`: o recorte é `EM_via_escola_censo` para linhas com escola (o Censo seleciona prováveis concluintes de EM) e `sem_restricao_EM` para `rede_grupo='todas'` (inclui treineiros e quem não tem escola). **IN_TREINEIRO não está no parquet** — limitação.
- Medalhistas (função `anexar_etapa`), conforme regulamentos consultados em 02/10/2026 e **aplicados a todos os anos (premissa, não verificada para 2016–2019)**:
  - OBMEP: nível 1 = 6º–7º ano → EF2; nível 2 = 8º–9º → EF2; nível 3 = EM.
  - OBI Iniciação: Júnior = 4º–5º ano → **EF1** (fora do alvo); nível 1 = 6º–7º → EF2; nível 2 = 8º–9º → EF2.
  - OBI Programação: Júnior = 8º–9º → EF2; nível 1 (EF + 1º ano EM) e nível 2 (EF até 3º EM) → **EF2_EM** (misto); Sênior (4º ano técnico / 1º ano superior) → `tecnico_superior`; Universitária → `superior`.
  - CF-OBI (Competição Feminina): regulamento não define séries distintas; usa o mapeamento de Programação (premissa).
  - `no_escopo_ef2_em` = etapa ∈ {EF2, EM, EF2_EM}.

## 4. Nulos, outliers e supressão (T2.9)
**Regras (sem imputação de valores):**
- Notas de área (CN, CH, LC, MT) `== 0` ou `> 1000` → nulo (tratadas como prova zerada/eliminada; a escala TRI não gera 0). Contadas em `n_nota_zero_invalidada`.
- Redação `== 0` é **válida** (redação anulada/em branco) e permanece; reportada em `pct_redacao_zero`. Redação fora de [0, 1000] → nulo.
- Renda: só entra quem tem faixa A–Q e `q005` entre 1 e 20 (`n_renda_valida`); detalhes em `renda_proxy.md`. Mediana (robusta) em vez de média para o proxy; sem corte de extremos.
- Município nulo → linha fora das agregações; medalhistas sem município casado ficam de fora (173 de 335281 linhas, nome+UF normalizados: {'exato': 334401, 'fuzzy': 707, 'sem_match': 173}).
- **Supressão** (`config/supressao.yaml`, n_min padrão **10**): `n < n_min` → `suprimido=True` e métricas nulas; `n` é mantido. Em `agg_enem_municipio`, médias por área, renda, % escola pública e sexo têm base própria (`n_cn`…, `n_renda_valida`, `n_tp_escola_valido`) e ficam nulas isoladamente quando a sua base < n_min, mesmo que a linha não seja suprimida.

**Contagens antes/depois da supressão:**

| tabela | linhas | linhas_suprimidas (n < n_min) | n_min | linhas_com_dado |
|---|---|---|---|---|
| agg_enem_municipio | 58331 | 5823 | 10 | 52508 |
| agg_proficiencia_escola | 498814 | 126453 | heranca INEP (ND) | 372361 |
| agg_proficiencia_municipio | 206273 | 21169 | heranca INEP (ND) | 185104 |
| agg_proficiencia_uf | 243 | 0 | 10 | 243 |
| agg_medalhas_municipio | 64738 | 57758 | 10 | 6980 |

Por visão (agg_enem_municipio):

| visao | linhas | suprimidas |
|---|---|---|
| desempenho_escola | 37705 | 4663 |
| desempenho_prova | 15318 | 1160 |
| perfil_prova | 5308 | 0 |

Medalhas (células com n ≥ 10 expõem `n_publicavel`):

| olimpiada | linhas | medalhas | celulas_publicaveis |
|---|---|---|---|
| OBI | 2021 | 5481 | 96 |
| OBMEP | 62717 | 329627 | 6884 |

**Nulos por coluna (as 6 mais nulas por tabela; completo em `data/interim/*.parquet`):**
- **agg_enem_municipio**: `pct_publica_tp_escola` 97%, `n_inscritos_total` 91%, `n_renda_valida` 91%, `pct_renda_pc_le_1_5_ponto_medio` 91%, `pct_certamente_le_1_5` 91%, `pct_possivelmente_le_1_5` 91%
- **agg_proficiencia_escola**: `n` 100%, `nota_saeb_lp` 25%, `nota_saeb_mt` 25%, `nota_saeb_padronizada` 25%, `ideb` 25%, `indicador_rendimento` 10%
- **agg_proficiencia_municipio**: `n` 100%, `rede_detalhe` 43%, `nota_saeb_lp` 10%, `nota_saeb_mt` 10%, `nota_saeb_padronizada` 10%, `ideb` 10%
- **agg_proficiencia_uf**: `inse_aluno_medio` 56%, `proficiencia_lp_media` 1%, `proficiencia_mt_media` 1%, `uf` 0%, `etapa` 0%, `ano` 0%
- **agg_medalhas_municipio**: `n_alunos_unicos` 100%, `n_publicavel` 89%, `co_municipio` 0%, `ano` 0%, `olimpiada` 0%, `medalha` 0%

## 5. Limitações
- **Células pequenas de medalhas**: a contagem é a própria métrica; na granularidade fina (município × ano × olimpíada × medalha × etapa × rede) a maioria das células tem n < 10 e fica suprimida em `n_publicavel`. Para análises (índice de talento) agregue antes (ex.: município × olimpíada, vários anos) — a supressão deve ser reaplicada após o agrupamento. `n` bruto de células pequenas pode reidentificar menores se exposto.
- Ideb não traz nº de alunos: não é possível aplicar n_min por escola/município; vale a supressão do INEP (`ND`).
- ENEM 2023 × 2024+ não são totalmente comparáveis (rede por fonte diferente, recortes diferentes, cobertura de escola 24% × 36%).
- `agg_enem_municipio` só cobre 2023–2025 (ENEM 2016–2022 ausentes).
- Município dos medalhistas: casamento por nome+UF normalizados (exato, depois fuzzy do `chaves.py`, subagente A); o resíduo sem município fica fora das agregações (ver contagem na seção 4). Casamentos fuzzy não foram auditados por B.
