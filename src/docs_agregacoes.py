"""Gera docs/agregacoes.md e docs/renda_proxy.md a partir dos resultados de src/agregacoes.py."""
from pathlib import Path

import pandas as pd

import renda

from caminhos import RAIZ  # noqa: E402
DOCS = RAIZ / "docs"


def md(df: pd.DataFrame) -> str:
    cab = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "|" + "|".join("---" for _ in df.columns) + "|"
    return "\n".join([cab, sep] + ["| " + " | ".join("" if pd.isna(v) else str(v) for v in r) + " |" for r in df.itertuples(index=False)])


def gerar(tabelas: dict, schema: dict, stats: dict, info_med: dict) -> None:
    sup = pd.DataFrame([{"tabela": t, "linhas": s["linhas"], "linhas_suprimidas (n < n_min)": s["suprimidas"],
                         "n_min": s["n_min"], "linhas_com_dado": s["linhas"] - s["suprimidas"]}
                        for t, s in stats.items() if t in tabelas])
    sch = pd.DataFrame([{"tabela": t, "chave única": v["chave"], "linhas": v["linhas"],
                         "colunas": len(tabelas[t].columns)} for t, v in schema.items()])
    colunas = "\n".join(f"- **{t}**: " + ", ".join(f"`{c}`" for c in df.columns) for t, df in tabelas.items())
    enem = tabelas["agg_enem_municipio"]
    porv = pd.DataFrame(stats["agg_enem_municipio"]["por_visao"]).T.reset_index()
    porv.columns = ["visao", "linhas", "suprimidas"]
    nul = []
    for t, v in schema.items():
        top = sorted(v["nulos_pct"].items(), key=lambda kv: -kv[1])[:6]
        nul.append(f"- **{t}**: " + ", ".join(f"`{c}` {100 * p:.0f}%" for c, p in top))
    med = tabelas["agg_medalhas_municipio"]
    pub = med.groupby("olimpiada").agg(linhas=("n", "size"), medalhas=("n", "sum"),
                                       celulas_publicaveis=("n_publicavel", "count")).reset_index()
    notas_ok = enem[enem["visao"] != "perfil_prova"]
    txt = f"""# Agregações por escola e município (T2.5–T2.9)

Gerado por `python src/agregacoes.py` (código em `src/agregacoes.py`, `rede.py`, `recortes.py`, `renda.py`).
Configs: `config/renda.yaml`, `config/recortes.yaml`, `config/supressao.yaml`. Saídas em `data/interim/agg_*.parquet`.
Chaves padronizadas: `co_municipio` (7 dígitos, str), `co_entidade` (8 dígitos, str), `ano` (int). **Nenhuma tabela contém nome de aluno** (assert no código).

## 1. Tabelas e chaves

{md(sch)}

Colunas:
{colunas}

Notas de desenho:
- **agg_enem_municipio** reúne três `visao`: `perfil_prova` (município da **prova**; renda, sexo, % escola pública autodeclarada), `desempenho_prova` (notas por município da **prova**) e `desempenho_escola` (notas por município da **escola**, só quem tem escola recenseada). `rede_grupo` ∈ {{`todas`, `publica`, `privada`}}.
- Em 2024–2025 **perfil e notas não se juntam** (bases independentes do INEP): renda/sexo só existem em `perfil_prova` e notas só em `desempenho_*`. Não há nota × renda por aluno nem por escola.
- **agg_proficiencia_escola / _municipio** vêm do **Ideb** (códigos reais). Os IDs do Saeb microdados são fictícios e **não** são usados para escola ou município. O Ideb não informa nº de alunos: `n` é nulo e `suprimido` = sem nenhuma nota/Ideb divulgado (`ND` do INEP).
- **agg_proficiencia_uf** vem do `saeb_escola` (UF real; média ponderada por alunos presentes; `n` = soma de alunos presentes).
- **agg_medalhas_municipio**: `n` = registros de medalha (não pessoas), fonte: {info_med['fonte']}. `n_alunos_unicos` só existe se `medalhistas_enriquecido.parquet` (dedup) tiver `id_aluno`; senão é nulo. `n_publicavel` = `n` quando ≥ n_min, senão nulo (**usar esta coluna para exposição**; `n` bruto é de uso interno).

## 2. Rede (T2.6) — `src/rede.py`
`rede_grupo` (publica/privada/None) e `rede_detalhe` (federal/estadual/municipal/privada/outra/None), mesma função para todas as bases (`aplicar_rede(df, base)`; versão SQL `sql_rede_enem`). `filtrar_publica(df)` mantém só escola pública.
- ENEM: `tp_dependencia_adm_esc` (1 federal, 2 estadual, 3 municipal, 4 privada; Censo) tem prioridade; senão `tp_escola` de 2023 (2 pública, 3 privada, 1 não respondeu = desconhecida), caso em que `rede_detalhe` é nulo. **A fonte da rede difere entre linhas** (Censo × autodeclarado em 2023).
- Saeb: `publica`/`privada`. Ideb: Federal/Estadual/Municipal/Privada; `Pública` (agregado municipal) → publica sem detalhe.
- OBMEP: F/E/M → pública; P → privada; **C (≈530 linhas) tem significado não documentado pela fonte** → `rede_grupo` nulo, `rede_detalhe='outra'`. OBI não publica rede → desconhecida (`rede_grupo='desconhecida'` nas agregações de medalhas).

## 3. Recortes EF2/EM (T2.7) — `config/recortes.yaml`, `src/recortes.py`
- Saeb e Ideb: `etapa` nativa (EF2 = 9º ano / anos finais; EM).
- **ENEM = EM**: perfil e notas de 2023 restringidos a `tp_st_conclusao` ∈ {{1, 2}} (concluiu / conclui no ano). Em 2024–2025 `RESULTADOS` não tem `tp_st_conclusao`: o recorte é `EM_via_escola_censo` para linhas com escola (o Censo seleciona prováveis concluintes de EM) e `sem_restricao_EM` para `rede_grupo='todas'` (inclui treineiros e quem não tem escola). **IN_TREINEIRO não está no parquet** — limitação.
- Medalhistas (função `anexar_etapa`), conforme regulamentos consultados em 02/10/2026 e **aplicados a todos os anos (premissa, não verificada para 2016–2019)**:
  - OBMEP: nível 1 = 6º–7º ano → EF2; nível 2 = 8º–9º → EF2; nível 3 = EM.
  - OBI Iniciação: Júnior = 4º–5º ano → **EF1** (fora do alvo); nível 1 = 6º–7º → EF2; nível 2 = 8º–9º → EF2.
  - OBI Programação: Júnior = 8º–9º → EF2; nível 1 (EF + 1º ano EM) e nível 2 (EF até 3º EM) → **EF2_EM** (misto); Sênior (4º ano técnico / 1º ano superior) → `tecnico_superior`; Universitária → `superior`.
  - CF-OBI (Competição Feminina): regulamento não define séries distintas; usa o mapeamento de Programação (premissa).
  - `no_escopo_ef2_em` = etapa ∈ {{EF2, EM, EF2_EM}}.

## 4. Nulos, outliers e supressão (T2.9)
**Regras (sem imputação de valores):**
- Notas de área (CN, CH, LC, MT) `== 0` ou `> 1000` → nulo (tratadas como prova zerada/eliminada; a escala TRI não gera 0). Contadas em `n_nota_zero_invalidada`.
- Redação `== 0` é **válida** (redação anulada/em branco) e permanece; reportada em `pct_redacao_zero`. Redação fora de [0, 1000] → nulo.
- Renda: só entra quem tem faixa A–Q e `q005` entre 1 e 20 (`n_renda_valida`); detalhes em `renda_proxy.md`. Mediana (robusta) em vez de média para o proxy; sem corte de extremos.
- Município nulo → linha fora das agregações; medalhistas sem município casado ficam de fora ({info_med['sem_municipio']} de {info_med['linhas_entrada']} linhas, nome+UF normalizados: {info_med.get('match', {})}).
- **Supressão** (`config/supressao.yaml`, n_min padrão **10**): `n < n_min` → `suprimido=True` e métricas nulas; `n` é mantido. Em `agg_enem_municipio`, médias por área, renda, % escola pública e sexo têm base própria (`n_cn`…, `n_renda_valida`, `n_tp_escola_valido`) e ficam nulas isoladamente quando a sua base < n_min, mesmo que a linha não seja suprimida.

**Contagens antes/depois da supressão:**

{md(sup)}

Por visão (agg_enem_municipio):

{md(porv)}

Medalhas (células com n ≥ 10 expõem `n_publicavel`):

{md(pub)}

**Nulos por coluna (as 6 mais nulas por tabela; completo em `data/interim/*.parquet`):**
{chr(10).join(nul)}

## 5. Limitações
- **Células pequenas de medalhas**: a contagem é a própria métrica; na granularidade fina (município × ano × olimpíada × medalha × etapa × rede) a maioria das células tem n < 10 e fica suprimida em `n_publicavel`. Para análises (índice de talento) agregue antes (ex.: município × olimpíada, vários anos) — a supressão deve ser reaplicada após o agrupamento. `n` bruto de células pequenas pode reidentificar menores se exposto.
- Ideb não traz nº de alunos: não é possível aplicar n_min por escola/município; vale a supressão do INEP (`ND`).
- ENEM 2023 × 2024+ não são totalmente comparáveis (rede por fonte diferente, recortes diferentes, cobertura de escola 24% × 36%).
- `agg_enem_municipio` só cobre 2023–2025 (ENEM 2016–2022 ausentes).
- Município dos medalhistas: casamento por nome+UF normalizados (exato, depois fuzzy do `chaves.py`, subagente A); o resíduo sem município fica fora das agregações (ver contagem na seção 4). Casamentos fuzzy não foram auditados por B.
"""
    (DOCS / "agregacoes.md").write_text(txt, encoding="utf-8")

    cfg = renda.CFG
    fx = pd.DataFrame([{"faixa": f, "lim_inf (SM)": v["lim_inf"], "lim_sup (SM)": "∞" if v["lim_sup"] is None else v["lim_sup"],
                        "ponto médio (SM)": v["ponto_medio"]} for f, v in cfg["faixas"].items()])
    sm = pd.DataFrame([{"ano": a, "SM de referência (R$)": v} for a, v in cfg["salario_minimo_reais"].items()])
    per = enem[enem["visao"] == "perfil_prova"]
    nac = per.groupby("ano").apply(lambda g: pd.Series({
        "municípios": len(g), "n (EM)": int(g["n"].sum()),
        "% ≤1,5 SM (ponto médio, pond. por n)": round((g["pct_renda_pc_le_1_5_ponto_medio"] * g["n_renda_valida"]).sum() / g.loc[g["pct_renda_pc_le_1_5_ponto_medio"].notna(), "n_renda_valida"].sum(), 1),
        "% certamente ≤1,5": round((g["pct_certamente_le_1_5"] * g["n_renda_valida"]).sum() / g.loc[g["pct_certamente_le_1_5"].notna(), "n_renda_valida"].sum(), 1),
        "% possivelmente": round((g["pct_possivelmente_le_1_5"] * g["n_renda_valida"]).sum() / g.loc[g["pct_possivelmente_le_1_5"].notna(), "n_renda_valida"].sum(), 1),
        "% acima": round((g["pct_acima_1_5"] * g["n_renda_valida"]).sum() / g.loc[g["pct_acima_1_5"].notna(), "n_renda_valida"].sum(), 1)}),
        include_groups=False).reset_index().astype({"municípios": int, "n (EM)": int})
    rtxt = f"""# Proxy de renda per capita ≤ 1,5 SM (T2.5)

**É uma faixa declarada, não o valor exato da renda.** Fonte: ENEM (questionário socioeconômico), origem `microdados` (2023) e `participantes` (2024–2025), recorte EM (`tp_st_conclusao` ∈ {{1, 2}}), agregado por **município da prova**. Configuração: `config/renda.yaml`; código: `src/renda.py`, `src/agregacoes.py`.

## Fórmula
Para cada inscrito com faixa `renda_familiar_faixa` (A–Q) e `q005` (moradores, incluindo o respondente; 1–20):

- `renda_pc_sm = ponto_médio_da_faixa(SM) ÷ q005`  (proxy central)
- Intervalo: `[lim_inf ÷ q005 , lim_sup ÷ q005]` (faixa = (lim_inf, lim_sup])
- **Flag central:** `renda_pc_sm ≤ {renda.LIMITE}`  → `pct_renda_pc_le_1_5_ponto_medio`
- **Classe pelo intervalo:** `certamente_le` se `lim_sup ÷ q005 ≤ {renda.LIMITE}`; `acima` se `lim_inf ÷ q005 ≥ {renda.LIMITE}`; caso contrário `possivelmente` → `pct_certamente_le_1_5`, `pct_possivelmente_le_1_5`, `pct_acima_1_5` (somam 100%). O número "verdadeiro" fica entre `pct_certamente_le_1_5` e `pct_certamente_le_1_5 + pct_possivelmente_le_1_5`.
- Agregação por município × ano: `n` (inscritos EM), `n_renda_valida`, mediana do proxy (`mediana_renda_pc_sm`, e em R$ com o SM do ano em `mediana_renda_pc_reais`).

## Faixas e salário mínimo de referência
As faixas A–Q do ENEM são **múltiplos do salário mínimo** do ano; as letras são as mesmas em 2023–2025 e os limites em SM também (conferido nos dicionários oficiais). Por isso o proxy em **SM per capita** é comparável entre anos; o SM só converte para R$.

{md(sm)}

{md(fx)}

- **Faixa A** (nenhuma renda) → 0 SM (certamente ≤ 1,5).
- **Faixa Q** (acima de 20 SM, aberta): ponto médio **arbitrado em 25 SM (1,25 × limite inferior)**; `lim_sup` = ∞. Só afeta o proxy central de quem declara >20 SM; com `q005 ≤ 20` o intervalo nunca é `certamente_le` (correto) e a classe é `acima` sempre que `20 ÷ q005 ≥ 1,5`.
- Colunas usadas: 2023 `Q006` (renda familiar); 2024–2025 `Q007` (já harmonizada em `renda_familiar_faixa`; `Q006` virou "possui renda?" e **não** deve ser usada).

## Resultado nacional (ponderado por inscritos com renda válida; só municípios não suprimidos)
{md(nac)}

## Limitações
- Faixa declarada: erro de classificação nas fronteiras (a classe `possivelmente` quantifica a incerteza).
- `q005` tem teto 20 (categoria "20" agrupa 20 ou mais) e o ponto médio supõe renda uniforme na faixa.
- Renda familiar é autodeclarada pelo estudante; EM concluintes/cursando 3ª série (2023: `tp_st_conclusao` 1 e 2; treineiros não identificáveis).
- Granularidade = **município da prova** (não da escola nem da residência). Em 2024–2025 não há ligação com notas ou escola.
- Participantes sem renda ou `q005` válidos ficam fora de `n_renda_valida`; células com `n_renda_valida` < n_min (10) têm renda nula.
- **Saeb:** não há conversão para renda. Usam-se apenas `inse_escola` e `inse_aluno_medio` já existentes, sem equivalência com renda per capita (escalas "Grupo" em 2017 e "Nível" depois; ids de escola fictícios).
"""
    (DOCS / "renda_proxy.md").write_text(rtxt, encoding="utf-8")
