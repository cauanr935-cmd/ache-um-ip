"""Fase 5 (T4.1-T4.5) - avaliacao: metricas, amostra de rotulagem, sensibilidade, vies e templates.

Uso: python src/avaliacao.py          (roda a Fase 4 se necessario e gera docs/avaliacao.md + templates)
     python -c "from avaliacao import precisao_recall; print(precisao_recall())"   (depois de rotular a amostra)
"""
import itertools
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

import modelagem as M

warnings.filterwarnings("ignore")
RAIZ = M.RAIZ
DOCS = RAIZ / "docs"
AMOSTRA = M.PROCESSED / "amostra_rotulagem.csv"
LINKAGE = M.PROCESSED / "linkage_resultado.parquet"
N_AMOSTRA = 200
FAIXAS = [0, 60, 70, 80, 85, 90, 95, 100, 100.0001]  # bordas de link_score; 100 exato e uma faixa propria
ROT_FAIXA = ["<60", "60-70", "70-80", "80-85", "85-90", "90-95", "95-<100", "100"]


# ---------------------------------------------------------------- T4.1 matching: amostra e precisao/recall
def _faixa(score: pd.Series) -> pd.Series:
    return pd.cut(score, FAIXAS, labels=ROT_FAIXA, right=False).astype(str)


def gerar_amostra_rotulagem(n: int = N_AMOSTRA, seed: int = M.SEED) -> pd.DataFrame:
    """~n pares (escola da lista de medalhistas -> escola INEP proposta) estratificados por faixa de link_score."""
    if AMOSTRA.exists():  # nunca apagar rotulos humanos (T4.1)
        antiga = pd.read_csv(AMOSTRA, dtype=str, keep_default_na=False)
        if (antiga["correto"].str.strip() != "").any():
            print(f"amostra de rotulagem ja tem rotulos: {AMOSTRA.name} preservada")
            return antiga
    d = pd.read_parquet(LINKAGE)
    d["faixa_similaridade"] = _faixa(d.link_score)
    por = n // len(ROT_FAIXA)
    partes = [g.sample(min(len(g), por), random_state=seed) for _, g in d.groupby("faixa_similaridade")]
    s = pd.concat(partes)
    falta = n - len(s)
    if falta > 0:  # completa com as faixas que ainda tem sobra (preferindo a fila de revisao)
        sobra = d.drop(s.index)
        sobra = sobra[sobra.faixa_similaridade.isin(["80-85", "85-90", "90-95"])]
        s = pd.concat([s, sobra.sample(min(falta, len(sobra)), random_state=seed)])
    s = s.sample(frac=1, random_state=seed).reset_index(drop=True)
    s.insert(0, "id_amostra", np.arange(1, len(s) + 1))
    cols = ["id_amostra", "olimpiada", "escola_norm", "co_municipio", "uf", "rede_grp", "n_linhas", "ano_min", "ano_max",
            "link_status", "link_score", "faixa_similaridade", "co_entidade", "no_escola_cand",
            "cand2_co_entidade", "cand2_no_escola", "cand3_co_entidade", "cand3_no_escola"]
    out = s[cols].copy()
    out["correto"] = ""               # PREENCHER: 1 / 0 (ver docs/avaliacao.md §4)
    out["co_entidade_correta"] = ""   # opcional: codigo INEP certo quando correto=0 e voce o conhece
    out.to_csv(AMOSTRA, index=False, encoding="utf-8")
    return out


def precisao_recall(caminho: Path | str = AMOSTRA) -> dict:
    """Precisao/recall do record linkage a partir da amostra rotulada.

    Regras de rotulagem da coluna `correto` (so linhas preenchidas entram; as demais sao ignoradas):
      - link_status auto / revisao (ha candidato proposto): 1 = o candidato (co_entidade) e a escola certa; 0 = errado.
      - link_status sem_match (sem candidato): 1 = correto nao vincular (a escola nao esta na base / nao e identificavel);
        0 = existia escola correta na base (idealmente informe `co_entidade_correta`).
    Dois cenarios: `auto` (so vinculos automaticos, como hoje) e `auto+revisao` (aceita o 1o candidato da fila de revisao).
    Verdadeiro positivo (VP) = candidato proposto correto. Existe escola verdadeira na base = candidato correto OU
    (correto=0 e `co_entidade_correta` preenchido) OU (sem_match com correto=0).
    A amostra e estratificada por faixa de link_score; as metricas `*_ponderado` reponderam cada faixa por N_faixa/n_amostra_faixa
    (estimam o valor sobre as ~41 mil escolas distintas); `*_amostra` sao as brutas.
    """
    a = pd.read_csv(caminho, dtype=str, keep_default_na=False)
    a["correto"] = a.correto.str.strip()
    a = a[a.correto.isin(["0", "1"])].copy()
    if a.empty:
        raise ValueError("Nenhuma linha rotulada: preencha a coluna `correto` com 1 ou 0.")
    a["c"] = a.correto.astype(int)
    pop = pd.read_parquet(LINKAGE)
    N = _faixa(pop.link_score).value_counts()
    n = a.groupby("faixa_similaridade").size()
    a["peso"] = a.faixa_similaridade.map(lambda f: N[f] / n[f])
    tem_cand = a.link_status.isin(["auto", "revisao"])
    corrige = a.co_entidade_correta.str.strip() != ""
    # existe escola verdadeira na base?
    existe = np.where(tem_cand, (a.c == 1) | corrige, (a.c == 0))
    # candidato proposto e correto?
    vp_cand = tem_cand & (a.c == 1)
    out = {"n_rotuladas": len(a), "n_por_faixa": n.to_dict()}
    for nome, pred in [("auto", a.link_status == "auto"), ("auto+revisao", tem_cand)]:
        for tipo, w in [("amostra", np.ones(len(a))), ("ponderado", a.peso.values)]:
            vp = (w * (pred & vp_cand)).sum()
            fp = (w * (pred & ~vp_cand)).sum()
            fn = (w * (existe & ~(pred & vp_cand))).sum()
            out[f"precisao_{nome}_{tipo}"] = vp / (vp + fp) if vp + fp else np.nan
            out[f"recall_{nome}_{tipo}"] = vp / (vp + fn) if vp + fn else np.nan
    por = a.assign(vp=vp_cand & (a.link_status == "auto"), auto=a.link_status == "auto").groupby("faixa_similaridade")
    out["precisao_auto_por_faixa"] = {f: (g.vp.sum() / g.auto.sum() if g.auto.sum() else np.nan) for f, g in por}
    return out


# ---------------------------------------------------------------- T4.2 template de validacao de negocio
def doc_validacao_negocio(df: pd.DataFrame, resid: pd.DataFrame) -> None:
    d = df[df.indice.notna()].copy()
    cols = ["co_municipio", "no_municipio", "uf", "pop", "indice", "cluster", "medalhas", "pct_renda_le_1_5"]
    def tabela(x: pd.DataFrame) -> str:
        t = x[cols].copy()
        t["pop"] = t["pop"].astype(int)
        t["indice"] = t.indice.round(3)
        t["cluster"] = t.cluster.astype("Int64").astype(str).replace("<NA>", "-")
        t["pct_renda_le_1_5"] = t.pct_renda_le_1_5.round(1)
        t["medalhas"] = t.medalhas.where(t.medalhas >= M.N_MIN, other=np.nan).map(lambda v: "<10" if pd.isna(v) else int(v))
        t["alunos_ip (n)"] = ""
        t["observacao_ip"] = ""
        return M.md_tabela(t.rename(columns={"pct_renda_le_1_5": "% renda<=1,5SM", "medalhas": "medalhas (O+P+B)"}), index=False)
    grandes = d[d["pop"] >= 50_000]
    top = grandes.nlargest(15, "indice")
    rm = resid[(resid.tipo == "municipio") & (resid.metrica == "medalhas")].nlargest(10, "residuo_padronizado")
    acima = d[d.co_municipio.isin(rm.entidade_id)].merge(rm[["entidade_id", "residuo_padronizado"]], left_on="co_municipio", right_on="entidade_id")
    acima = acima.sort_values("residuo_padronizado", ascending=False)
    ctrl = grandes.nsmallest(10, "indice")
    caps = d[d.co_municipio.isin(["3550308", "3304557", "2927408", "2304400", "1302603", "5300108", "4106902", "4314902", "2611606", "1501402"])]
    L = ["# Validação de negócio com dados do IP — template (T4.2)", "",
         "**Status: pendente de dado.** Nenhum dado do Instituto Ponte foi acessado (`docs/dados_internos_ip.md`). "
         "Este documento lista as cidades a comparar e o que o IP precisa fornecer. Pergunta: *o ranking do índice bate com as cidades "
         "de onde o IP já recruta/aprova alunos?*", "",
         "## O que pedir ao IP (apenas agregado)", "",
         "- Tabela `co_municipio` (IBGE 7 dígitos) × `ano_ingresso` × `etapa_ingresso` × `n_alunos` (supressão n < 10; ver `config/supressao.yaml`).",
         "- Opcional: sexo e rede da escola de origem, já agregados. Nenhum dado individual é necessário.", "",
         "## Como comparar (preencher quando houver dado)", "",
         "1. **Aderência do top-N:** % dos municípios com alunos do IP que estão no top-N do índice (N = 50, 100, 200) vs. % esperado ao acaso.",
         "2. **Correlação:** Spearman entre `indice` e alunos do IP por 100 mil hab. (apenas municípios com ENEM/Saeb).",
         "3. **Lacunas nos dois sentidos:** cidades do IP fora do top-N (o índice perde algo?) e cidades top-N sem aluno do IP (oportunidade ou ruído?).",
         "4. Registrar a leitura do IP na coluna `observacao_ip` e as decisões em `docs/ata_validacao_ip.md`.", "",
         "Critério de aceite a combinar com o IP (sugestão, não validado): aderência do top-100 ≥ 2× o acaso e Spearman > 0.",
         "", "## A. Top 15 do índice entre municípios com ≥ 50 mil habitantes", "", tabela(top), "",
         "## B. Municípios com mais medalhas que o esperado (modelo de expectativa, T3.4)", "", tabela(acima), "",
         "## C. Grupo de controle: 10 menores índices entre municípios com ≥ 50 mil habitantes", "", tabela(ctrl), "",
         "## D. Capitais de referência (sugestão de comparação com grandes centros)", "", tabela(caps), "",
         "`medalhas (O+P+B)` aparece como `<10` onde a contagem é suprimida. Cidades onde o IP atua e que não estejam acima devem ser "
         "acrescentadas pelo IP; o script `src/avaliacao.py` regenera as tabelas."]
    (DOCS / "validacao_negocio_template.md").write_text("\n".join(L) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- T4.3 sensibilidade
def sensibilidade(df: pd.DataFrame, ns=(50, 100, 200)):
    base_w = {k: v["peso"] for k, v in M.PESOS["componentes"].items()}
    base = M.indice(df)
    ok = base.notna()
    chaves = list(base_w)
    cenarios = []
    for mult in itertools.product([0.8, 1.0, 1.2], repeat=3):
        if mult == (1.0, 1.0, 1.0):
            continue
        cenarios.append(("±20% " + "/".join(f"{m:g}" for m in mult), {k: base_w[k] * m for k, m in zip(chaves, mult)}))
    for k in chaves:
        cenarios.append((f"peso 0 em {k}", {**base_w, k: 0.0}))
    linhas = []
    for nome, w in cenarios:
        w = {k: v / sum(w.values()) for k, v in w.items()}
        alt = M.indice(df, pesos=w)
        r = {"cenario": nome, "spearman_geral": stats.spearmanr(base[ok], alt[ok]).statistic}
        rb, ra = base[ok].rank(ascending=False), alt[ok].rank(ascending=False)
        for n in ns:
            topb = rb.nsmallest(n).index
            topa = ra.nsmallest(n).index
            r[f"retencao_top{n}"] = len(set(topb) & set(topa)) / n
            r[f"spearman_top{n}"] = stats.spearmanr(rb[topb], ra[topb]).statistic
        linhas.append(r)
    t = pd.DataFrame(linhas)
    mm = M.indice(df, how="minmax")
    alt = {"cenario": "normalizacao min-max (pesos base)", "spearman_geral": stats.spearmanr(base[ok], mm[ok]).statistic}
    rb, ra = base[ok].rank(ascending=False), mm[ok].rank(ascending=False)
    for n in ns:
        topb, topa = rb.nsmallest(n).index, ra.nsmallest(n).index
        alt[f"retencao_top{n}"] = len(set(topb) & set(topa)) / n
        alt[f"spearman_top{n}"] = stats.spearmanr(rb[topb], ra[topb]).statistic
    return t, alt


# ---------------------------------------------------------------- T4.4 vies
def vies(df: pd.DataFrame, resid: pd.DataFrame) -> dict:
    d = df[df.indice.notna()].copy()
    out = {}
    d["top10"] = d.indice >= d.indice.quantile(0.9)
    d["tres_comp"] = d[["c_talento", "c_qualidade", "c_vulnerabilidade"]].notna().all(axis=1)
    d["fonte_renda"] = d.fonte_renda.fillna("sem_renda")
    for g in ["regiao", "porte"]:
        t = d.groupby(g).agg(municipios=("co_municipio", "size"), indice_medio=("indice", "mean"), pct_top10=("top10", "mean"),
                             pct_tres_componentes=("tres_comp", "mean"), pct_renda_escola=("fonte_renda", lambda s: (s == "municipio_escola_2023").mean()))
        t["pct_top10"] *= 100; t["pct_tres_componentes"] *= 100; t["pct_renda_escola"] *= 100
        grupos = [x.indice.values for _, x in d.groupby(g)]
        kw = stats.kruskal(*grupos)
        t["razao_top10_vs_esperado"] = t.pct_top10 / 10
        out[g] = (t, kw.statistic, kw.pvalue)
    out["spearman_indice_logpop"] = stats.spearmanr(d.indice, d.log_pop).statistic
    out["spearman_taxa_logpop"] = stats.spearmanr(d.taxa_medalhas_100k, d.log_pop).statistic
    out["spearman_taxa_bruta_logpop"] = stats.spearmanr(d.taxa_medalhas_bruta_100k, d.log_pop).statistic
    # residuos medios por grupo (vies sistematico do modelo de expectativa)
    r = resid[resid.tipo == "municipio"].merge(df[["co_municipio", "regiao", "porte"]], left_on="entidade_id", right_on="co_municipio")
    out["residuos"] = {g: r.pivot_table(index=g, columns="metrica", values="residuo_padronizado", aggfunc="mean") for g in ["regiao", "porte"]}
    rs = resid[resid.tipo == "escola"].merge(df[["co_municipio", "regiao"]].assign(), how="left", left_on="entidade_id", right_on="co_municipio")
    # sexo (somente 2023, unico ano com sexo e nota no mesmo registro)
    rec = M.enem_recortes()
    s = rec[rec.recorte.str.startswith("sexo=")].pivot(index="co_municipio", columns="recorte", values=["valor", "n"]).dropna()
    s.columns = ["_".join(c) for c in s.columns]
    w = s["n_sexo=F"] + s["n_sexo=M"]
    out["sexo"] = {"municipios": len(s), "media_F": float(np.average(s["valor_sexo=F"], weights=s["n_sexo=F"])),
                   "media_M": float(np.average(s["valor_sexo=M"], weights=s["n_sexo=M"])),
                   "dif_media_municipal_M_menos_F": float((s["valor_sexo=M"] - s["valor_sexo=F"]).mean()),
                   "pct_municipios_M_maior": float((s["valor_sexo=M"] > s["valor_sexo=F"]).mean() * 100),
                   "pct_feminino_participantes": float(s["n_sexo=F"].sum() / w.sum() * 100)}
    return out


# ---------------------------------------------------------------- documento consolidado
def _fmt(v, nd=3):
    return f"{v:.{nd}f}" if isinstance(v, (float, np.floating)) else str(v)


def doc_avaliacao(r: dict, sens: pd.DataFrame, mm: dict, vz: dict, am: pd.DataFrame) -> None:
    df, sil, k, infos = r["df"], r["sil"], r["k"], r["infos"]
    rank, resid = r["rank"], r["resid"]
    pesos = {n: v["peso"] for n, v in M.PESOS["componentes"].items()}
    ok = df.indice.notna()
    n3 = int(df[["c_talento", "c_qualidade", "c_vulnerabilidade"]].notna().all(axis=1).sum())
    met = pd.DataFrame([{ "modelo": i["modelo"], "n": i["n"], "R² (ajuste)": i["r2_insample"], "R² (CV-5)": i["r2_cv5"],
                          "RMSE (CV-5)": i["rmse_cv5"], "MAE (CV-5)": i["mae_cv5"]} for i in infos])
    coef = []
    for i in infos:
        for c, v in i["coef"].items():
            coef.append({"modelo": i["modelo"], "termo": c, "coef": v, "p": i["pvalores"].get(c, np.nan)})
    coef = pd.DataFrame(coef)
    best = sil.loc[sil.silhouette.idxmax()]
    cols_s = ["cenario", "spearman_geral", "retencao_top50", "retencao_top100", "retencao_top200", "spearman_top100"]
    pior = sens.loc[sens.retencao_top100.idxmin()]
    ac = resid.groupby(["tipo", "metrica"]).acima_do_esperado.agg(["sum", "size"]).reset_index()
    L = [
        "# Avaliação da modelagem (Fases 4 e 5: T3.2–T3.5 e T4.1–T4.5)", "",
        "Gerado por `python src/avaliacao.py` (que chama `src/modelagem.py`). Todos os números abaixo vêm da última execução.", "",
        "## 0. Escopo, entradas e desvios do pedido", "",
        "- **Entradas:** `data/processed/` hoje só contém `linkage_resultado.parquet` e `linkage_revisao_manual.csv`. As tabelas "
        "`dim_*`/`fato_*` (T2.11) **não existem**, porque T1.13 (escolas do Censo) está bloqueada (DP-2). Usei os agregados já validados de "
        "`data/interim/` (`agg_medalhas_municipio`, `agg_proficiencia_{municipio,escola}`, `dim_municipio_base`) e o `enem_all.parquet` "
        "(agregado por município, sem nome de aluno em nenhuma saída). Quando T2.11 sair, basta trocar as leituras em `modelagem.py`.",
        "- **INSE não entra no modelo:** os ids de escola/município do Saeb são máscaras e não ligam ao código INEP/IBGE (`docs/lacunas_saeb.md` §1). "
        "O papel de INSE/renda é feito pelo proxy de renda do ENEM (mediana da renda per capita em SM, suavizada; o % ≤ 1,5 SM do RF 5.4 é publicado mas **satura**: média de ~95%), por município.",
        "- **ENEM só tem município de *prova*** (≈ 1,8 mil municípios). Para os demais usei o município da *escola* (só 2023, único ano com escola e renda "
        f"no mesmo registro), quando há ≥ 10 participantes. Resultado: renda em **{int(df.pct_renda_le_1_5.notna().sum())}** de {len(df)} municípios; "
        f"**{n3}** têm os três componentes do índice.",
        "- **Só 2023 tem sexo e renda junto com nota** no ENEM; por isso os recortes de sexo e faixa de renda nos rankings são `enem_media_geral` (`ano_ref` = 2023).",
        "- **Medalhas:** OBMEP (2016–2019, 2024, 2025) e OBI (sem 2018); ONHB não coletada; OBMEP 2020–2023 ausente. Conta Ouro+Prata+Bronze em EF2/EM; Menção Honrosa fora.",
        "- **Escolas:** só Saeb/Ideb 2025 (nota padronizada e Ideb) e medalhas por escola vinculadas automaticamente (`link_status = auto`). "
        "O modelo de escolas usa renda e porte do **município** (não há INSE por escola), então é um ajuste ecológico.", "",
        "## 1. Índice de potencial (T3.2)", "",
        f"Componentes e pesos (`config/pesos.yaml`, com justificativa): talento {pesos['talento']}, qualidade da rede {pesos['qualidade_rede']}, "
        f"vulnerabilidade {pesos['vulnerabilidade']}. Normalização por **percentil (rank)**: as taxas de medalha são muito assimétricas e cheias de zeros, "
        "e min-max ficaria dominado por poucos outliers (o efeito da escolha é medido na §6). Taxa de medalhas com encolhimento bayesiano "
        f"(a = {M.PESOS['suavizacao_talento_pop']:,} hab.) para municípios pequenos não liderarem por acaso. Pesos renormalizados entre os componentes disponíveis "
        f"(mínimo {M.PESOS['min_componentes']} componentes: municípios sem renda no ENEM, ou sem Saeb/Ideb publicado, **ficam sem índice**; com mínimo 2 a renormalização "
        f"fazia municípios sem dado de renda liderarem o ranking, um viés de dado faltante visto no T4.4). Índice calculado para **{int(ok.sum())}** de {len(df)} municípios.",
        "", "**Decisão de negócio em aberto:** o sinal de `qualidade_rede` é +1 (rede forte = ambiente que forma candidatos aptos). Se o IP preferir priorizar redes fracas, mude para −1 em `pesos.yaml`.", "",
        "## 2. Clusterização (T3.3 / T4.1)", "",
        f"K-Means, k de 3 a 8, escolhido por silhouette: **k = {k}** (silhouette {best.silhouette:.3f}, Davies-Bouldin {best.davies_bouldin:.3f}). "
        "Perfis em `docs/clusters.md`.", "", M.md_tabela(sil.round(4), index=False), "",
        f"Leitura: silhouette de {best.silhouette:.2f} indica estrutura **fraca**; os municípios formam mais um contínuo que grupos separados. "
        "Use os clusters como agrupamento para comparar municípios parecidos, não como categorias naturais. "
        f"O Davies-Bouldin é menor em k = {int(sil.loc[sil.davies_bouldin.idxmin(), 'k'])} (diferença pequena entre os k), diferente do k do silhouette: "
        "os critérios não apontam um k claramente melhor. Escolhi k por silhouette conforme o pedido; k = 3 também é o mais fácil de explicar.", "",
        "## 3. Modelo de expectativa e métricas de regressão (T3.4 / T4.1)", "",
        "Resíduo > 0 = acima do esperado dado renda e porte. `acima_do_esperado` = resíduo padronizado > 1 (em `residuos.parquet`). "
        "R²/RMSE/MAE por validação cruzada de 5 dobras (as de ajuste estão no código).", "",
        M.md_tabela(met.round(3), index=False), "",
        "Coeficientes:", "", M.md_tabela(coef.round(4), index=False), "",
        "Contagem de entidades acima do esperado (resíduo padronizado > 1):", "", M.md_tabela(ac, index=False), "",
        "Leitura e cuidados:", "",
        f"- **Medalhas:** R² (CV) = {infos[0]['r2_cv5']:.2f} em escala de contagem; essa métrica é dominada pelas poucas cidades grandes (RMSE = {infos[0]['rmse_cv5']:.0f} "
        f"contra MAE = {infos[0]['mae_cv5']:.1f}). Use o resíduo **padronizado** (Pearson da binomial negativa; α = {infos[0]['alpha']:.2f}, forte superdispersão), não o absoluto, "
        "para achar municípios acima do esperado. O coeficiente de renda é positivo: municípios com maior renda per capita mediana têm mais medalhas por habitante, "
        "então o resíduo já desconta parte da vantagem de renda.",
        f"- **Proficiência:** renda + porte explicam pouco do Saeb (R² CV = {infos[1]['r2_cv5']:.2f} por município, {infos[3]['r2_cv5']:.2f} por escola) e bastante do ENEM por município "
        f"(R² CV = {infos[2]['r2_cv5']:.2f}). Há muita variação entre escolas/municípios de contexto parecido, e é ela que o resíduo captura; mas o modelo é um controle grosseiro: "
        "resíduo positivo pode refletir fatores omitidos (INSE real da escola, rede, localização), não só desempenho acima do esperado.",
        "- Modelos de escola usam renda e porte do município; escolas do mesmo município compartilham o mesmo contexto. `rede_detalhe_federal` tem coeficiente grande (escolas federais selecionam alunos).",
        "- Os erros do modelo variam por região e porte (ver §7): resíduos entre regiões diferentes não são diretamente comparáveis.", "",
        "## 3b. Formato de `rankings.parquet` e `residuos.parquet`", "",
        "`rankings.parquet`: `entidade_id` (município IBGE 7 / escola INEP 8, string), `tipo` (`municipio`/`escola`), `recorte` (`geral`, `etapa=EF2|EM`, `sexo=F|M`, "
        "`renda=ate_1_5sm|acima_1_5sm`), `metrica`, `valor`, `rank` (1 = maior valor dentro de `tipo`+`recorte`+`metrica`; inclusive em `pct_renda_pc_le_1_5` e `renda_pc_mediana_sm`, "
        "onde rank 1 = maior % / maior renda, ou seja, **não** é o mais vulnerável) e `n` (base da supressão) e `ano_ref` (ano da fonte quando único; nulo para agregados de vários anos). Chave única `(entidade_id, tipo, recorte, metrica)`: "
        "uma métrica por entidade por recorte. Contagens/taxas de medalha só aparecem onde há ≥ 10 medalhas; recortes de sexo e renda são só ENEM 2023 e com ≥ 10 participantes.",
        f"`rankings.parquet` tem {len(rank):,} linhas; métricas por recorte: " + "; ".join(f"{t}/{rc}: {', '.join(sorted(g.metrica.unique()))}" for (t, rc), g in rank.groupby(["tipo", "recorte"])) + ".",
        "`residuos.parquet`: `entidade_id`, `tipo`, `metrica`, `etapa`, `modelo`, `observado`, `esperado`, `residuo`, `residuo_padronizado`, `acima_do_esperado` (> 1 desvio), `rank_residuo`.",
        "`municipio_features.parquet` (extra): todas as features, componentes, índice e cluster por município.", "",
        "## 4. Qualidade do matching escola ↔ medalhista (T4.1)", "",
        f"`data/processed/amostra_rotulagem.csv`: **{len(am)}** pares (escola da lista de medalhistas → escola INEP proposta), estratificados por faixa de "
        "`link_score`, com coluna `correto` **vazia** para rotular. Unidade = escola distinta por (olimpíada, nome normalizado, município).", "",
        M.md_tabela(am.groupby("faixa_similaridade").size().reindex(ROT_FAIXA).rename("n_amostra").reset_index().assign(
            n_populacao=lambda t: t.faixa_similaridade.map(_faixa(pd.read_parquet(LINKAGE).link_score).value_counts())), index=False), "",
        "**Como rotular** (coluna `correto`):", "",
        "- Linhas `auto` ou `revisao` (há candidato em `co_entidade`/`no_escola_cand`): `1` se o candidato é a mesma escola; `0` se não é. "
        "Se for `0` e você souber a escola certa, informe o código em `co_entidade_correta`. Os candidatos 2 e 3 estão nas colunas `cand2_*`/`cand3_*`.",
        "- Linhas `sem_match` (sem candidato): `1` se é correto não vincular (a escola não existe na base / não dá para identificar); "
        "`0` se existia escola correta (informe `co_entidade_correta`).",
        "- Se rotular só parte (ex.: 50 linhas), as não rotuladas são ignoradas; documente quantas.", "",
        "**Cálculo:** `from avaliacao import precisao_recall; precisao_recall()` (`src/avaliacao.py`). Devolve precisão e recall em dois cenários (`auto` e `auto+revisao`), "
        "brutos e **ponderados** pelo tamanho de cada faixa (a amostra é estratificada, então a taxa bruta não estima a população), e a precisão do `auto` por faixa. "
        "Testada com rótulos sintéticos (`teste_precisao_recall()`); **os números reais aguardam sua rotulagem**.", "",
        "**Status:** pendente de rotulagem humana.", "",
        "## 5. Validação de negócio com o IP (T4.2 / T4.5)", "",
        "Sem dado do IP. Gerado `docs/validacao_negocio_template.md` (cidades a comparar + o que pedir ao IP) e `docs/ata_validacao_ip.md` (ata da reunião). **Status: pendente de dado e de reunião.**", "",
        "## 6. Sensibilidade dos pesos (T4.3)", "",
        "Cada peso variado em −20%, 0 e +20% (27 combinações, 26 diferentes da base), mais zerar cada componente (stress test) e a normalização min-max. "
        "Pesos renormalizados para somar 1. `retencao_topN` = fração do top-N do cenário base que continua no top-N; `spearman_topN` = correlação de rank dentro do top-N base.", "",
        M.md_tabela(sens[cols_s][sens.cenario.str.startswith("±20%")].describe().loc[["min", "mean", "max"]].round(3)), "",
        "Pior caso entre as variações de ±20%: " +
        f"`{sens[sens.cenario.str.startswith('±20%')].loc[sens[sens.cenario.str.startswith('±20%')].retencao_top100.idxmin(), 'cenario']}`.", "",
        "Stress tests (peso zero) e normalização alternativa:", "",
        M.md_tabela(pd.concat([sens[~sens.cenario.str.startswith("±20%")], pd.DataFrame([mm])])[cols_s].round(3), index=False), "",
        f"Leitura: nas variações de ±20% o ranking geral é estável (Spearman ≥ {sens[sens.cenario.str.startswith('±20%')].spearman_geral.min():.2f}) e o top-100 retém "
        f"{sens[sens.cenario.str.startswith('±20%')].retencao_top100.min():.0%}–100%. O top-N é mais sensível que o ranking inteiro. Nos stress tests, zerar talento ou vulnerabilidade "
        f"derruba a retenção do top-100 para {sens.loc[sens.cenario == 'peso 0 em talento', 'retencao_top100'].iloc[0]:.0%} e {sens.loc[sens.cenario == 'peso 0 em vulnerabilidade', 'retencao_top100'].iloc[0]:.0%}: "
        "o top depende desses dois componentes. **A escolha da normalização pesa mais que ±20% nos pesos:** com min-max o Spearman com o índice base cai para "
        f"{mm['spearman_geral']:.2f} (retenção do top-100: {mm['retencao_top100']:.0%}), porque a taxa de medalhas é muito assimétrica e o min-max a comprime. Por isso a normalização por rank é a escolhida.", "",
        "## 7. Checagem de viés (T4.4)", "",
    ]
    for g, nome in [("regiao", "região"), ("porte", "porte do município")]:
        t, kwh, kwp = vz[g]
        L += [f"### Por {nome}", "",
              M.md_tabela(t.round(2)), "",
              f"Kruskal-Wallis do índice entre grupos: H = {kwh:.1f}, p = {kwp:.2e}. `razao_top10_vs_esperado` = 1 significa participação no top-10% igual à proporção de municípios.",
              "Resíduo padronizado médio dos modelos (≠ 0 indica viés sistemático do modelo de expectativa):", "",
              M.md_tabela(vz["residuos"][g].round(3)), ""]
    s = vz["sexo"]
    L += ["### Por sexo", "",
          "- **Medalhistas: não mensurável.** As listas OBMEP/OBI não trazem sexo; não inferi sexo pelo nome. Pedir sexo à OBMEP/IP ou usar o dado agregado do IP.",
          f"- ENEM 2023 (concluintes, {s['municipios']} municípios com ≥ 10 de cada sexo): média geral F = {s['media_F']:.1f}, M = {s['media_M']:.1f}; "
          f"diferença média por município (M − F) = {s['dif_media_municipal_M_menos_F']:.1f} pontos; M > F em {s['pct_municipios_M_maior']:.0f}% dos municípios; "
          f"{s['pct_feminino_participantes']:.0f}% dos participantes são mulheres.",
          "- Implicação: o índice não usa sexo, mas o componente de talento (olimpíadas) pode herdar desigualdade de participação por sexo, que não conseguimos medir aqui.", "",
          "### Viés estrutural do índice", "",
          f"- Spearman(índice, log população) = {vz['spearman_indice_logpop']:.3f}. Spearman(taxa suavizada, log pop) = {vz['spearman_taxa_logpop']:.3f}; "
          f"taxa bruta = {vz['spearman_taxa_bruta_logpop']:.3f}.",
          f"- Participação no top-10% do índice difere por região (razão vs. esperado de {vz['regiao'][0].razao_top10_vs_esperado.min():.2f} a {vz['regiao'][0].razao_top10_vs_esperado.max():.2f}) "
          f"e por porte ({vz['porte'][0].razao_top10_vs_esperado.min():.2f} a {vz['porte'][0].razao_top10_vs_esperado.max():.2f}); NE e SE ficam acima de 1 e CO, N e S abaixo. Isso reflete os dados (medalhas e renda), mas é um efeito a explicar ao IP, não uma propriedade neutra.",
          "- Municípios sem ENEM suficiente (< 10 participantes) ou sem Saeb/Ideb ficam **sem índice** (`min_componentes: 3`). Em `pct_renda_escola`: a renda vem do município da escola (2023) "
          "em boa parte dos municípios pequenos (fonte menos comparável, suavizada); filtrar por `fonte_renda` em `municipio_features.parquet` para testar a robustez.",
          f"- Viés sistemático do modelo de expectativa: " + "; ".join(
              f"{m} — maior desvio na região {vz['residuos'][g][m].abs().idxmax()} ({vz['residuos'][g][m].loc[vz['residuos'][g][m].abs().idxmax()]:+.2f} desvios)"
              for g in ['regiao'] for m in vz['residuos'][g].columns) + ". Preferir comparar resíduos dentro da mesma região.",
          "- Medalhas OBMEP 2020–2023 e ONHB ausentes: subestima municípios cujo talento aparecia nesses anos.", "",
          "## 8. Lacunas e riscos dos resultados", "",
          "- INSE por município indisponível; renda é proxy por faixa declarada de quem presta ENEM (viés de seleção: só quem faz a prova).",
          "- Renda por município de prova (≈ 1,8 mil) ou de escola (2023): mistura de fontes sinalizada em `fonte_renda` (`municipio_features.parquet`).",
          "- Sem Saeb 2025 oficial; edições 2023/2025 do Ideb agregadas por município sem peso por matrícula (média simples das redes).",
          "- O modelo de expectativa é descritivo, não causal.",
          "- Matching e validação de negócio dependem de trabalho humano (§4, §5).", "",
          "## 9. Critério de aceite", "",
          "| Entregável | Status |", "|---|---|",
          "| `data/processed/rankings.parquet` | gerado |", "| `data/processed/residuos.parquet` | gerado |",
          "| `config/pesos.yaml` | gerado, com justificativa |", "| `docs/avaliacao.md` | este documento |",
          "| `data/processed/amostra_rotulagem.csv` | gerada (rotulagem pendente) |",
          "| `docs/clusters.md`, `docs/validacao_negocio_template.md`, `docs/ata_validacao_ip.md` | gerados |", ""]
    (DOCS / "avaliacao.md").write_text("\n".join(L), encoding="utf-8")


def doc_ata() -> None:
    L = ["# Ata da reunião de validação com o Instituto Ponte (T4.5) — template", "",
         "**Status: reunião ainda não realizada.** Preencher durante/depois da reunião.", "",
         "| Campo | Preenchimento |", "|---|---|",
         "| Data / horário | |", "| Local / link | |", "| Participantes (nome, cargo, instituição) | |", "| Responsável pela ata | |", "",
         "## 1. Pauta", "",
         "1. Objetivo do projeto e escopo da modelagem (índice de potencial, clusters, modelo de expectativa).",
         "2. Apresentação do ranking e dos clusters (`docs/avaliacao.md`, `rankings.parquet`).",
         "3. Comparação com as cidades do IP (`docs/validacao_negocio_template.md`).",
         "4. Decisões de modelagem em aberto (abaixo).", "5. Uso e publicação dos resultados; LGPD.", "6. Próximos passos.", "",
         "## 2. Decisões que precisam do IP", "",
         "| # | Pergunta | Opções | Decisão do IP |", "|---|---|---|---|",
         "| 1 | Sinal da qualidade da rede no índice | +1 (priorizar rede forte) / −1 (priorizar rede carente) | |",
         "| 2 | Pesos (talento 0,50 / rede 0,20 / vulnerabilidade 0,30) | manter / ajustar | |",
         "| 3 | Corte de vulnerabilidade | renda per capita ≤ 1,5 SM / outro | |",
         "| 4 | Granularidade exigida | município / escola | |",
         "| 5 | Uso de sexo no recorte | agregado do IP disponível? | |",
         "| 6 | Regra de supressão para contagens pequenas | n < 10 (padrão) / outra | |", "",
         "## 3. Resultados da comparação com dados do IP", "",
         "| Métrica | Valor | Observações |", "|---|---|---|",
         "| Aderência do top-50 / top-100 / top-200 | | |", "| Spearman índice × alunos do IP por 100 mil hab. | | |",
         "| Cidades do IP fora do top-N | | |", "| Cidades top-N sem aluno do IP | | |", "",
         "## 4. Feedback qualitativo", "", "| Tema | Comentário do IP | Ação |", "|---|---|---|", "| Cidades que surpreendem | | |",
         "| Variáveis que faltam | | |", "| Clareza dos clusters | | |", "",
         "## 5. Dados e LGPD", "",
         "- [ ] IP aceita entregar apenas tabela agregada (município × ano × etapa × n)? Prazo: ____",
         "- [ ] Regra de supressão acordada: ____", "- [ ] IP autoriza citar o nome do Instituto e mostrar cidades em materiais públicos? Nível de detalhe: ____", "",
         "## 6. Encaminhamentos", "", "| Ação | Responsável | Prazo |", "|---|---|---|", "| | | |", "",
         "## 7. Aprovação", "", "Validação do IP sobre os resultados: ( ) aprovado ( ) aprovado com ressalvas ( ) não aprovado. Ressalvas: ____", ""]
    (DOCS / "ata_validacao_ip.md").write_text("\n".join(L), encoding="utf-8")


def teste_precisao_recall() -> dict:
    """Roda precisao_recall com rotulos sinteticos (candidato correto se link_score >= 95) numa copia temporaria."""
    a = pd.read_csv(AMOSTRA, dtype=str, keep_default_na=False)
    a["correto"] = np.where(a.link_status.isin(["auto", "revisao"]), (a.link_score.astype(float) >= 95).astype(int).astype(str),
                            np.where(a.link_score.astype(float) < 60, "1", "0"))
    tmp = M.RAIZ / "data/interim/_amostra_teste.csv"
    a.to_csv(tmp, index=False)
    try:
        return precisao_recall(tmp)
    finally:
        tmp.unlink()


def run_fase5(r: dict | None = None, anos_qualidade=None, ano_escola=None, ano_recortes=None) -> tuple:
    """`r`: resultado de modelagem.run_fase4 (se None, roda a Fase 4 com os anos informados ou derivados dos dados)."""
    r = r or M.run_fase4(anos_qualidade, ano_escola, ano_recortes)
    am = gerar_amostra_rotulagem()
    sens, mm = sensibilidade(r["df"])
    vz = vies(r["df"], r["resid"])
    doc_validacao_negocio(r["df"], r["resid"])
    doc_ata()
    doc_avaliacao(r, sens, mm, vz, am)
    return r, sens, mm, vz, am


if __name__ == "__main__":
    r, sens, mm, vz, am = run_fase5()
    print(sens.round(3).to_string()); print(mm)
    for g in ["regiao", "porte"]:
        print(vz[g][0].round(2).to_string(), vz[g][1:])
        print(vz["residuos"][g].round(3))
    print({k: v for k, v in vz.items() if k not in ("regiao", "porte", "residuos")})
    print(am.faixa_similaridade.value_counts().to_string(), len(am))
    print(teste_precisao_recall())
