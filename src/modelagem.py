"""Fase 4 (T3.2-T3.5) - indice de potencial, clusterizacao, modelo de expectativa e rankings.

Entradas: data/interim/agg_*.parquet, dim_municipio_base.parquet, enem_all.parquet, medalhistas_enriquecido.parquet
(as tabelas dim_*/fato_* de data/processed ainda nao existem: T1.13 bloqueada e T2.11 nao rodada; ver docs/avaliacao.md §0).
Saidas: data/processed/{rankings,residuos,municipio_features}.parquet, docs/clusters.md.
Uso: python src/modelagem.py
"""
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import statsmodels.api as sm
import yaml
from sklearn.cluster import KMeans
from sklearn.metrics import davies_bouldin_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from caminhos import RAIZ  # noqa: E402  (ACHE_RAIZ configura a raiz)
INTERIM = RAIZ / "data/interim"
PROCESSED = RAIZ / "data/processed"
SEED = 42
MEDALHAS = ["Ouro", "Prata", "Bronze"]
N_MIN = yaml.safe_load((RAIZ / "config/supressao.yaml").read_text())["n_min_padrao"]
PESOS = yaml.safe_load((RAIZ / "config/pesos.yaml").read_text())
RENDA = yaml.safe_load((RAIZ / "config/renda.yaml").read_text())
# Anos de referencia (None = derivado dos dados em run_fase4): edicoes de qualidade da rede, ano das escolas e do recorte ENEM
PARAMS: dict = {"anos_qualidade": None, "ano_escola": None, "ano_recortes": None}
FEATS_CLUSTER = ["log_taxa_medalhas", "saeb_padr", "ideb", "renda_pc_sm", "log_pop"]


# ---------------------------------------------------------------- features
def _enem_municipio() -> pd.DataFrame:
    """Renda (todos os anos) e nota media geral, por municipio da prova, agregados direto do ENEM."""
    faixas = pd.DataFrame({"faixa": list(RENDA["faixas"]), "pm_sm": [v["ponto_medio"] for v in RENDA["faixas"].values()]})
    con = duckdb.connect()
    con.register("faixas", faixas)
    src = f"'{INTERIM / 'enem_all.parquet'}'"
    renda = con.sql(f"""
        select co_municipio_prova as co_municipio, count(*) as n_renda,
               avg(case when f.pm_sm / e.q005 <= {RENDA['limite_per_capita_sm']} then 1.0 else 0 end) * 100 as pct_renda_le_1_5,
               median(f.pm_sm / e.q005) as renda_pc_sm
        from {src} e join faixas f on e.renda_familiar_faixa = f.faixa
        where e.origem in ('microdados','participantes') and e.tp_st_conclusao in (1,2) and e.q005 > 0
              and e.co_municipio_prova is not null
        group by 1""").df()
    nota = """(case when nu_nota_cn>0 then nu_nota_cn end + case when nu_nota_ch>0 then nu_nota_ch end
             + case when nu_nota_lc>0 then nu_nota_lc end + case when nu_nota_mt>0 then nu_nota_mt end + nu_nota_redacao) / 5"""
    media = con.sql(f"""
        select co_municipio_prova as co_municipio, count(*) as n_enem, avg({nota}) as enem_media
        from {src}
        where (origem='resultados' or (origem='microdados' and tp_st_conclusao in (1,2)))
              and nu_nota_cn>0 and nu_nota_ch>0 and nu_nota_lc>0 and nu_nota_mt>0 and nu_nota_redacao is not null
              and co_municipio_prova is not null
        group by 1""").df()
    # O ENEM so tem local de prova em ~1.8 mil municipios. Para os demais, usa o municipio da ESCOLA (so 2023, unico ano com
    # escola e renda no mesmo registro), quando houver >= n_min participantes. `fonte_renda` marca a origem.
    renda_esc = con.sql(f"""
        select co_municipio_esc as co_municipio, count(*) as n_renda,
               avg(case when f.pm_sm / e.q005 <= {RENDA['limite_per_capita_sm']} then 1.0 else 0 end) * 100 as pct_renda_le_1_5,
               median(f.pm_sm / e.q005) as renda_pc_sm
        from {src} e join faixas f on e.renda_familiar_faixa = f.faixa
        where e.origem = 'microdados' and e.tp_st_conclusao in (1,2) and e.q005 > 0 and e.co_municipio_esc is not null
        group by 1""").df()
    renda["fonte_renda"] = "municipio_prova_2023_25"
    renda_esc = renda_esc[~renda_esc.co_municipio.isin(renda.loc[renda.n_renda >= N_MIN, "co_municipio"])]
    renda_esc["fonte_renda"] = "municipio_escola_2023"
    renda = pd.concat([renda, renda_esc], ignore_index=True)
    renda = renda[renda.n_renda >= N_MIN].drop_duplicates("co_municipio", keep="first")
    out = renda.merge(media, on="co_municipio", how="outer")
    out.loc[out.n_renda < N_MIN, ["pct_renda_le_1_5", "renda_pc_sm"]] = np.nan
    # encolhimento da mediana de renda per capita ao valor nacional (peso n/(n+k)): a fonte "escola" tem n pequeno (mediana ~27)
    k, bruto = PESOS["suavizacao_renda_n"], out.renda_pc_sm
    out["renda_pc_sm_bruta"] = bruto
    out["renda_pc_sm"] = (out.n_renda * bruto + k * bruto.mean()) / (out.n_renda + k)
    out.loc[out.n_enem < N_MIN, "enem_media"] = np.nan
    return out


def enem_recortes() -> pd.DataFrame:
    """Nota media por municipio x sexo e x faixa de renda. So o ano `ano_recortes` (2023 hoje): em 2024-25 sexo e renda ficam em arquivos sem nota."""
    con = duckdb.connect()
    src = f"'{INTERIM / 'enem_all.parquet'}'"
    nota = "(nu_nota_cn+nu_nota_ch+nu_nota_lc+nu_nota_mt+nu_nota_redacao)/5"
    base = f"""from {src} where ano={PARAMS["ano_recortes"]} and origem='microdados' and tp_st_conclusao in (1,2)
               and nu_nota_cn>0 and nu_nota_ch>0 and nu_nota_lc>0 and nu_nota_mt>0 and nu_nota_redacao is not null"""
    sexo = con.sql(f"""select co_municipio_prova as co_municipio, 'sexo=' || tp_sexo as recorte, count(*) n, avg({nota}) valor
                       {base} and tp_sexo in ('F','M') group by 1,2""").df()
    faixas = pd.DataFrame({"faixa": list(RENDA["faixas"]), "pm_sm": [v["ponto_medio"] for v in RENDA["faixas"].values()]})
    con.register("faixas", faixas)
    renda = con.sql(f"""select co_municipio_prova as co_municipio,
                        case when f.pm_sm / e.q005 <= {RENDA['limite_per_capita_sm']} then 'renda=ate_1_5sm' else 'renda=acima_1_5sm' end as recorte,
                        count(*) n, avg({nota}) valor
                        from {src} e join faixas f on e.renda_familiar_faixa=f.faixa
                        where e.ano={PARAMS['ano_recortes']} and e.origem='microdados' and e.tp_st_conclusao in (1,2) and e.q005>0
                        and e.nu_nota_cn>0 and e.nu_nota_ch>0 and e.nu_nota_lc>0 and e.nu_nota_mt>0 and e.nu_nota_redacao is not null
                        group by 1,2""").df()
    out = pd.concat([sexo, renda], ignore_index=True)
    return out[out.n >= N_MIN]


def _qualidade() -> pd.DataFrame:
    p = pd.read_parquet(INTERIM / "agg_proficiencia_municipio.parquet")
    p = p[(p.ano.isin(PARAMS["anos_qualidade"])) & (~p.suprimido) & p.etapa.isin(["EF2", "EM"])]
    g = p.groupby(["co_municipio", "etapa", "ano"], as_index=False)[["nota_saeb_padronizada", "ideb"]].mean()
    g = g.sort_values("ano").dropna(subset=["nota_saeb_padronizada", "ideb"], how="all")
    ult = g.groupby(["co_municipio", "etapa"], as_index=False).last()  # edicao mais recente disponivel
    w = ult.pivot(index="co_municipio", columns="etapa", values=["nota_saeb_padronizada", "ideb"])
    w.columns = [f"{'saeb_padr' if a.startswith('nota') else 'ideb'}_{b.lower()}" for a, b in w.columns]
    w["saeb_padr"] = w[["saeb_padr_ef2", "saeb_padr_em"]].mean(axis=1)
    w["ideb"] = w[["ideb_ef2", "ideb_em"]].mean(axis=1)
    return w.reset_index()


def _medalhas(pop: pd.Series) -> pd.DataFrame:
    m = pd.read_parquet(INTERIM / "agg_medalhas_municipio.parquet")
    m = m[m.no_escopo_ef2_em & m.medalha.isin(MEDALHAS)]
    tot = m.groupby("co_municipio").n.sum().rename("medalhas")
    et = m.pivot_table(index="co_municipio", columns="etapa", values="n", aggfunc="sum", fill_value=0)
    et = et.reindex(columns=["EF2", "EM"], fill_value=0).add_prefix("medalhas_").rename(columns=str.lower)
    return pd.concat([tot, et], axis=1).reset_index()


def construir_features() -> pd.DataFrame:
    dim = pd.read_parquet(INTERIM / "dim_municipio_base.parquet")
    dim = dim.rename(columns={"populacao": "pop"})[["co_municipio", "no_municipio", "uf", "regiao", "pop"]]
    df = dim.merge(_medalhas(dim["pop"]), on="co_municipio", how="left").merge(_qualidade(), on="co_municipio", how="left")
    df = df.merge(_enem_municipio(), on="co_municipio", how="left")
    for c in ["medalhas", "medalhas_ef2", "medalhas_em"]:
        df[c] = df[c].fillna(0).astype(int)
    a = PESOS["suavizacao_talento_pop"]
    r0 = df.medalhas.sum() / df["pop"].sum()
    df["taxa_medalhas_bruta_100k"] = df.medalhas / df["pop"] * 1e5
    df["taxa_medalhas_100k"] = (df.medalhas + a * r0) / (df["pop"] + a) * 1e5
    df["log_taxa_medalhas"] = np.log1p(df.taxa_medalhas_100k)
    df["pop"] = df["pop"].astype(float)
    df["log_pop"] = np.log(df["pop"].where(df["pop"] > 0))
    df["porte"] = pd.cut(df["pop"], [0, 20_000, 50_000, 100_000, 500_000, np.inf],
                         labels=["<=20k", "20-50k", "50-100k", "100-500k", ">500k"]).astype(str)
    return df


# ---------------------------------------------------------------- T3.2 indice
def _norm(s: pd.Series, how: str) -> pd.Series:
    if how == "rank":
        return s.rank(pct=True, method="average")
    return (s - s.min()) / (s.max() - s.min())


def componentes(df: pd.DataFrame, how: str | None = None) -> pd.DataFrame:
    how = how or PESOS["normalizacao"]
    c = PESOS["componentes"]
    out = pd.DataFrame(index=df.index)
    out["c_talento"] = _norm(df.taxa_medalhas_100k, how)
    out["c_qualidade"] = pd.concat([_norm(df.saeb_padr, how), _norm(df.ideb, how)], axis=1).mean(axis=1)
    out["c_vulnerabilidade"] = 1 - _norm(df.renda_pc_sm, how)  # menor renda per capita => maior vulnerabilidade
    for nome, col in [("talento", "c_talento"), ("qualidade_rede", "c_qualidade"), ("vulnerabilidade", "c_vulnerabilidade")]:
        if c[nome]["sinal"] < 0:
            out[col] = 1 - out[col]
    return out


def indice(df: pd.DataFrame, pesos: dict | None = None, how: str | None = None) -> pd.Series:
    """Soma ponderada dos componentes disponiveis (pesos renormalizados por linha); NaN se < min_componentes."""
    p = pesos or {k: v["peso"] for k, v in PESOS["componentes"].items()}
    comp = componentes(df, how)
    w = pd.Series({"c_talento": p["talento"], "c_qualidade": p["qualidade_rede"], "c_vulnerabilidade": p["vulnerabilidade"]})
    disp = comp.notna()
    soma_w = disp.mul(w, axis=1).sum(axis=1)
    idx = comp.fillna(0).mul(w, axis=1).sum(axis=1) / soma_w
    idx[disp.sum(axis=1) < PESOS["min_componentes"]] = np.nan
    return idx


# ---------------------------------------------------------------- T3.3 clusters
def clusterizar(df: pd.DataFrame):
    d = df.dropna(subset=FEATS_CLUSTER)
    X = StandardScaler().fit_transform(d[FEATS_CLUSTER])
    res = []
    for k in range(3, 9):
        lab = KMeans(n_clusters=k, n_init=10, random_state=SEED).fit_predict(X)
        res.append({"k": k, "silhouette": silhouette_score(X, lab), "davies_bouldin": davies_bouldin_score(X, lab)})
    res = pd.DataFrame(res)
    k = int(res.loc[res.silhouette.idxmax(), "k"])
    lab = KMeans(n_clusters=k, n_init=10, random_state=SEED).fit_predict(X)
    out = d[["co_municipio"]].copy()
    out["cluster"] = lab
    return out, res, k


_ROTULO = {"log_taxa_medalhas": "taxa de medalhas", "saeb_padr": "nota Saeb", "ideb": "Ideb", "renda_pc_sm": "renda per capita", "log_pop": "porte"}


def md_tabela(d: pd.DataFrame, index: bool = True) -> str:
    """Tabela markdown simples (evita depender de `tabulate`)."""
    d = d.reset_index() if index else d
    linhas = ["| " + " | ".join(map(str, d.columns)) + " |", "|" + "---|" * len(d.columns)]
    linhas += ["| " + " | ".join(map(str, r)) + " |" for r in d.itertuples(index=False)]
    return "\n".join(linhas)


def doc_clusters(df: pd.DataFrame, cl: pd.DataFrame, res: pd.DataFrame, k: int) -> None:
    d = df.merge(cl, on="co_municipio")
    z = d.groupby("cluster")[FEATS_CLUSTER].mean()
    z = (z - d[FEATS_CLUSTER].mean()) / d[FEATS_CLUSTER].std()
    def nome(r):
        t = [f"{_ROTULO[c]} {'acima' if v > 0 else 'abaixo'} da média" for c, v in r.items() if abs(v) >= 0.5]
        return ", ".join(t) if t else "perfil medio"
    perf = d.groupby("cluster").agg(
        municipios=("co_municipio", "size"), populacao_mediana=("pop", "median"), medalhas_total=("medalhas", "sum"),
        taxa_medalhas_100k=("taxa_medalhas_bruta_100k", "median"), saeb_padr=("saeb_padr", "mean"), ideb=("ideb", "mean"),
        renda_pc_sm=("renda_pc_sm", "mean"), pct_renda_le_1_5=("pct_renda_le_1_5", "mean"), indice=("indice", "mean"))
    perf["perfil_automatico"] = z.apply(nome, axis=1)
    reg = pd.crosstab(d.cluster, d.regiao)
    L = ["# Clusters de municípios (T3.3)", "",
         f"K-Means (`random_state={SEED}`, `n_init=10`) sobre {len(d)} municípios com as 5 variáveis completas, padronizadas (z-score): "
         "`log(1+taxa de medalhas suavizada)`, nota Saeb padronizada, Ideb, renda per capita mediana (SM, suavizada) e `log(população)`.",
         "Municípios sem alguma dessas variáveis (sem Saeb/Ideb publicado ou com < 10 participantes no ENEM) ficam **sem cluster**.", "",
         f"## Escolha de k (silhouette; k de 3 a 8) → **k = {k}**", "", md_tabela(res.round(4), index=False), "",
         "## Perfil dos clusters", "",
         "Médias por cluster (taxa de medalhas = mediana da taxa bruta por 100 mil hab.). `perfil_automatico` lista as variáveis "
         "cujo centróide está a ≥ 0,5 desvio-padrão da média geral.", "",
         md_tabela(perf.round(2)), "", "## Distribuição por região (nº de municípios)", "", md_tabela(reg), "",
         "## Cuidados de leitura", "",
         "- Silhouette baixo/moderado é esperado: os dados formam um contínuo, não grupos bem separados. Os clusters servem para "
         "agrupar municípios comparáveis, não para afirmar categorias naturais.",
         "- `porte` entra como variável de propósito: separa grandes centros de municípios pequenos, onde a taxa de medalhas é mais ruidosa.",
         "- Os rótulos automáticos são descritivos; nomeie os clusters com o IP antes de usar em apresentação."]
    (RAIZ / "docs/clusters.md").write_text("\n".join(L) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- T3.4 modelo de expectativa
def _metricas(y, yhat) -> dict:
    y, yhat = np.asarray(y, float), np.asarray(yhat, float)
    sse, sst = ((y - yhat) ** 2).sum(), ((y - y.mean()) ** 2).sum()
    return {"r2": 1 - sse / sst, "rmse": float(np.sqrt(((y - yhat) ** 2).mean())), "mae": float(np.abs(y - yhat).mean())}


def _cv_pred(fit_predict, n: int, k: int = 5) -> np.ndarray:
    idx = np.random.RandomState(SEED).permutation(n)
    pred = np.empty(n)
    for f in np.array_split(idx, k):
        tr = np.setdiff1d(idx, f)
        pred[f] = fit_predict(tr, f)
    return pred


def modelo_medalhas(df: pd.DataFrame):
    """Medalhas (contagem) ~ renda + porte, binomial negativa com exposicao = populacao."""
    d = df.dropna(subset=["renda_pc_sm"]).reset_index(drop=True)
    X = sm.add_constant(d[["renda_pc_sm", "log_pop"]])
    y, expo = d.medalhas.values, d["pop"].values / 1e5
    fit = sm.NegativeBinomial(y, X, exposure=expo).fit(disp=0, maxiter=200)
    mu = fit.predict(X, exposure=expo)
    alpha = float(fit.params["alpha"])
    d["esperado"], d["observado"] = mu, y
    d["residuo"] = y - mu
    d["residuo_padronizado"] = d.residuo / np.sqrt(mu + alpha * mu**2)  # residuo de Pearson da NB
    def fp(tr, te):
        f = sm.NegativeBinomial(y[tr], X.iloc[tr], exposure=expo[tr]).fit(disp=0, maxiter=200)
        return f.predict(X.iloc[te], exposure=expo[te])
    cv = _metricas(y, _cv_pred(fp, len(d)))
    info = {"modelo": "medalhas_municipio (NB, exposicao=pop)", "n": len(d), "alpha": alpha,
            "coef": fit.params.round(4).to_dict(), "pvalores": fit.pvalues.round(4).to_dict(),
            **{f"{k}_insample": v for k, v in _metricas(y, mu).items()}, **{f"{k}_cv5": v for k, v in cv.items()}}
    return d[["co_municipio", "observado", "esperado", "residuo", "residuo_padronizado"]], info


def _ols(d: pd.DataFrame, y: str, X: list[str], nome: str):
    d = d.dropna(subset=[y] + X).reset_index(drop=True)
    Xm = sm.add_constant(d[X].astype(float))
    fit = sm.OLS(d[y].values, Xm).fit()
    d["esperado"], d["observado"] = fit.fittedvalues.values, d[y].values
    d["residuo"] = d.observado - d.esperado
    d["residuo_padronizado"] = d.residuo / np.sqrt(fit.scale)
    cv = _metricas(d[y], _cv_pred(lambda tr, te: sm.OLS(d[y].values[tr], Xm.iloc[tr]).fit().predict(Xm.iloc[te]), len(d)))
    info = {"modelo": nome, "n": len(d), "coef": fit.params.round(4).to_dict(), "pvalores": fit.pvalues.round(4).to_dict(),
            **{f"{k}_insample": v for k, v in _metricas(d[y], fit.fittedvalues).items()}, **{f"{k}_cv5": v for k, v in cv.items()}}
    return d, info


def modelo_proficiencia_municipio(df: pd.DataFrame):
    d, info = _ols(df, "saeb_padr", ["renda_pc_sm", "log_pop"], "saeb_padr_municipio (OLS)")
    return d[["co_municipio", "observado", "esperado", "residuo", "residuo_padronizado"]], info


def modelo_enem_municipio(df: pd.DataFrame):
    d, info = _ols(df, "enem_media", ["renda_pc_sm", "log_pop"], "enem_media_municipio (OLS)")
    return d[["co_municipio", "observado", "esperado", "residuo", "residuo_padronizado"]], info


def modelo_escola(df: pd.DataFrame):
    """Nota Saeb padronizada da escola ~ renda e porte do MUNICIPIO + rede + etapa (INSE da escola nao liga ao codigo INEP)."""
    e = pd.read_parquet(INTERIM / "agg_proficiencia_escola.parquet")
    e = e[(e.ano == PARAMS["ano_escola"]) & e.etapa.isin(["EF2", "EM"]) & ~e.suprimido & e.nota_saeb_padronizada.notna()]
    e = e.merge(df[["co_municipio", "renda_pc_sm", "log_pop"]], on="co_municipio", how="left")
    e = pd.get_dummies(e, columns=["rede_detalhe", "etapa"], drop_first=True, dtype=float)
    X = ["renda_pc_sm", "log_pop"] + [c for c in e.columns if c.startswith(("rede_detalhe_", "etapa_"))]
    d, info = _ols(e, "nota_saeb_padronizada", X, f"saeb_padr_escola (OLS, {PARAMS['ano_escola']})")
    d["etapa"] = np.where(d.get("etapa_EM", 0) == 1, "EM", "EF2")
    return d[["co_entidade", "co_municipio", "etapa", "observado", "esperado", "residuo", "residuo_padronizado"]], info


def montar_residuos(df: pd.DataFrame):
    partes, infos = [], []
    for fn, metrica, ano in [(modelo_medalhas, "medalhas", None), (modelo_proficiencia_municipio, "saeb_padronizada", 2025),
                             (modelo_enem_municipio, "enem_media", 2025)]:
        r, i = fn(df)
        r.insert(0, "tipo", "municipio")
        r = r.rename(columns={"co_municipio": "entidade_id"})
        r["etapa"] = "todas"
        partes.append(r.assign(metrica=metrica, modelo=i["modelo"])); infos.append(i)
    r, i = modelo_escola(df)
    r = r.rename(columns={"co_entidade": "entidade_id"}).drop(columns="co_municipio")
    partes.append(r.assign(tipo="escola", metrica="saeb_padronizada", modelo=i["modelo"])); infos.append(i)
    out = pd.concat(partes, ignore_index=True)
    out["acima_do_esperado"] = out.residuo_padronizado > 1.0
    out["rank_residuo"] = out.groupby(["tipo", "metrica", "etapa"]).residuo_padronizado.rank(ascending=False, method="min").astype(int)
    cols = ["entidade_id", "tipo", "metrica", "etapa", "modelo", "observado", "esperado", "residuo", "residuo_padronizado",
            "acima_do_esperado", "rank_residuo"]
    return out[cols], infos


# ---------------------------------------------------------------- T3.5 rankings
def _rank(d: pd.DataFrame) -> pd.DataFrame:
    d = d.copy()
    d["rank"] = d.groupby(["tipo", "recorte", "metrica"]).valor.rank(ascending=False, method="min").astype(int)
    return d


def montar_rankings(df: pd.DataFrame, resid: pd.DataFrame) -> pd.DataFrame:
    R = []
    aq, ae, ar = PARAMS["anos_qualidade"][-1], PARAMS["ano_escola"], PARAMS["ano_recortes"]
    def add(ids, tipo, recorte, metrica, valor, n=None, ano=None):
        R.append(pd.DataFrame({"entidade_id": ids, "tipo": tipo, "recorte": recorte, "metrica": metrica,
                               "valor": valor, "n": n if n is not None else np.nan,
                               "ano_ref": pd.array([ano] * len(ids), dtype="Int64")}).dropna(subset=["valor"]))
    m = df
    add(m.co_municipio, "municipio", "geral", "indice_potencial", m.indice)
    pub = m.medalhas >= N_MIN  # supressao: taxa de medalhas so onde ha >= n_min medalhas
    add(m.co_municipio[pub], "municipio", "geral", "medalhas_por_100k", m.taxa_medalhas_bruta_100k[pub], m.medalhas[pub])
    add(m.co_municipio, "municipio", "geral", "pct_renda_pc_le_1_5", m.pct_renda_le_1_5, m.n_renda)
    add(m.co_municipio, "municipio", "geral", "renda_pc_mediana_sm", m.renda_pc_sm, m.n_renda)
    add(m.co_municipio, "municipio", "geral", "enem_media_geral", m.enem_media, m.n_enem)
    for et in ["ef2", "em"]:
        r = f"etapa={et.upper()}"
        add(m.co_municipio, "municipio", r, "saeb_padronizada", m[f"saeb_padr_{et}"], ano=aq)
        add(m.co_municipio, "municipio", r, "ideb", m[f"ideb_{et}"], ano=aq)
        p = m[f"medalhas_{et}"] >= N_MIN
        add(m.co_municipio[p], "municipio", r, "medalhas_por_100k", (m[f"medalhas_{et}"] / m["pop"] * 1e5)[p], m[f"medalhas_{et}"][p])
    rec = enem_recortes()
    add(rec.co_municipio, "municipio", rec.recorte, "enem_media_geral", rec.valor, rec.n, ano=ar)
    # escolas
    e = pd.read_parquet(INTERIM / "agg_proficiencia_escola.parquet")
    e = e[(e.ano == PARAMS["ano_escola"]) & e.etapa.isin(["EF2", "EM"]) & ~e.suprimido]
    for met, col in [("saeb_padronizada", "nota_saeb_padronizada"), ("ideb", "ideb")]:
        add(e.co_entidade, "escola", "etapa=" + e.etapa, met, e[col], ano=ae)
    re = resid[(resid.tipo == "escola")]
    add(re.entidade_id, "escola", "etapa=" + re.etapa, "residuo_saeb_padronizada", re.residuo_padronizado, ano=ae)
    me = pd.read_parquet(INTERIM / "medalhistas_enriquecido.parquet", columns=["co_entidade", "medalha", "link_status", "linha_duplicada"])
    me = me[(me.link_status == "auto") & ~me.linha_duplicada & me.medalha.isin(MEDALHAS)]
    cnt = me.groupby("co_entidade").size()
    cnt = cnt[cnt >= N_MIN]
    add(cnt.index, "escola", "geral", "n_medalhas", cnt.values.astype(float), cnt.values)
    out = _rank(pd.concat(R, ignore_index=True))
    out["valor"] = out.valor.astype(float)
    assert not out.duplicated(["entidade_id", "tipo", "recorte", "metrica"]).any(), "chave (entidade, tipo, recorte, metrica) duplicada"
    return out[["entidade_id", "tipo", "recorte", "metrica", "valor", "rank", "n", "ano_ref"]]


def _definir_anos(anos_qualidade=None, ano_escola=None, ano_recortes=None) -> None:
    """Preenche PARAMS: o que nao for informado vem dos dados (2 ultimas edicoes do Ideb, ultimo ano das escolas e do ENEM com sexo+renda+nota)."""
    p = pd.read_parquet(INTERIM / "agg_proficiencia_municipio.parquet", columns=["ano", "ideb"])
    anos_ideb = sorted(p.loc[p.ideb.notna(), "ano"].unique())
    e = duckdb.sql(f"select max(ano) from '{INTERIM / 'enem_all.parquet'}' where origem='microdados'").fetchone()[0]
    PARAMS["anos_qualidade"] = list(anos_qualidade or anos_ideb[-2:])
    PARAMS["ano_escola"] = int(ano_escola or anos_ideb[-1])
    PARAMS["ano_recortes"] = int(ano_recortes or e)


def run_fase4(anos_qualidade=None, ano_escola=None, ano_recortes=None) -> dict:
    _definir_anos(anos_qualidade, ano_escola, ano_recortes)
    df = construir_features()
    df["indice"] = indice(df)
    df = pd.concat([df, componentes(df)], axis=1)
    cl, sil, k = clusterizar(df)
    doc_clusters(df, cl, sil, k)
    df = df.merge(cl, on="co_municipio", how="left")
    resid, infos = montar_residuos(df)
    rank = montar_rankings(df, resid)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PROCESSED / "municipio_features.parquet", index=False)
    resid.to_parquet(PROCESSED / "residuos.parquet", index=False)
    rank.to_parquet(PROCESSED / "rankings.parquet", index=False)
    return {"df": df, "sil": sil, "k": k, "infos": infos, "resid": resid, "rank": rank}


if __name__ == "__main__":
    r = run_fase4()
    d = r["df"]
    print("municipios", len(d), "com indice", d.indice.notna().sum(), "com cluster", d.cluster.notna().sum(), "k", r["k"])
    print(r["sil"].round(3).to_string())
    for i in r["infos"]:
        print({k: v for k, v in i.items() if k not in ("pvalores",)})
    print(r["rank"].groupby(["tipo", "recorte", "metrica"]).size().to_string())
    print(r["resid"].groupby(["tipo", "metrica"]).acima_do_esperado.agg(["sum", "size"]))
