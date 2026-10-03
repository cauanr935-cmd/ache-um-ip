"""T2.5-T2.9 - Agregacoes por escola e municipio, com supressao estatistica. Entry point: python src/agregacoes.py

Saidas em data/interim/: agg_enem_municipio, agg_proficiencia_escola, agg_proficiencia_municipio,
agg_proficiencia_uf, agg_medalhas_municipio (.parquet). Docs: docs/agregacoes.md e docs/renda_proxy.md.
Chaves: co_municipio (7, str), co_entidade (8, str), ano (int). Nenhuma tabela contem nome de aluno.
"""
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import yaml

import chaves
import recortes
import renda
import rede

from caminhos import RAIZ  # noqa: E402  (ACHE_RAIZ configura a raiz)
INT = RAIZ / "data/interim"
DOCS = RAIZ / "docs"
SUP = yaml.safe_load((RAIZ / "config/supressao.yaml").read_text(encoding="utf-8"))
AREAS = ["cn", "ch", "lc", "mt", "redacao"]
STATS: dict = {}


def n_min(tabela: str) -> int:
    return int(SUP["n_min_por_tabela"].get(tabela, SUP["n_min_padrao"]))


def suprimir(df: pd.DataFrame, tabela: str, n_col: str, metricas: list[str]) -> pd.DataFrame:
    """n < n_min -> metricas nulas e suprimido=True (n mantido)."""
    m = n_min(tabela)
    out = df.copy()
    out["suprimido"] = out[n_col].fillna(0) < m
    for c in metricas:
        out.loc[out["suprimido"], c] = np.nan
    STATS[tabela] = {"linhas": len(out), "suprimidas": int(out["suprimido"].sum()), "n_min": m}
    return out


# ----------------------------------------------------------------------------- ENEM
def enem_municipio(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    ALL = f"'{INT / 'enem_all.parquet'}'"
    lim = renda.LIMITE
    # --- perfil (municipio da PROVA; microdados 2023 + participantes 2024+) -----------------
    perfil = con.sql(f"""
        WITH b AS (SELECT ano, co_municipio_prova AS co_municipio, tp_st_conclusao, tp_sexo, tp_escola, q005,
                          renda_familiar_faixa FROM {ALL}
                   WHERE origem IN ('microdados', 'participantes') AND co_municipio_prova IS NOT NULL),
        tot AS (SELECT co_municipio, ano, COUNT(*) AS n_inscritos_total FROM b GROUP BY 1, 2),
        em AS (SELECT b.*, fx.lim_inf, fx.lim_sup, fx.pm,
                      (b.q005 BETWEEN 1 AND 20 AND fx.pm IS NOT NULL) AS valido
               FROM b LEFT JOIN {renda.faixas_values_sql()} ON b.renda_familiar_faixa = fx.faixa
               WHERE {recortes.sql_enem_em('b.tp_st_conclusao')})
        SELECT 'perfil_prova' AS visao, em.co_municipio, em.ano, 'todas' AS rede_grupo,
               'EM_tp_st_conclusao' AS recorte, COUNT(*) AS n, ANY_VALUE(tot.n_inscritos_total) AS n_inscritos_total,
               COUNT(*) FILTER (WHERE valido) AS n_renda_valida,
               100.0 * AVG((pm / q005 <= {lim})::INT) FILTER (WHERE valido) AS pct_renda_pc_le_1_5_ponto_medio,
               100.0 * AVG(((lim_sup IS NOT NULL AND lim_sup / q005 <= {lim}))::INT) FILTER (WHERE valido) AS pct_certamente_le_1_5,
               100.0 * AVG((NOT (lim_sup IS NOT NULL AND lim_sup / q005 <= {lim}) AND lim_inf / q005 < {lim})::INT)
                     FILTER (WHERE valido) AS pct_possivelmente_le_1_5,
               100.0 * AVG((lim_inf / q005 >= {lim})::INT) FILTER (WHERE valido) AS pct_acima_1_5,
               MEDIAN(pm / q005) FILTER (WHERE valido) AS mediana_renda_pc_sm,
               COUNT(*) FILTER (WHERE tp_sexo = 'F') AS n_feminino, COUNT(*) FILTER (WHERE tp_sexo = 'M') AS n_masculino,
               COUNT(*) FILTER (WHERE tp_escola IN (2, 3)) AS n_tp_escola_valido,
               100.0 * AVG((tp_escola = 2)::INT) FILTER (WHERE tp_escola IN (2, 3)) AS pct_publica_tp_escola
        FROM em JOIN tot USING (co_municipio, ano) GROUP BY em.co_municipio, em.ano""").df()
    perfil["mediana_renda_pc_reais"] = perfil["mediana_renda_pc_sm"] * perfil["ano"].map(renda.CFG["salario_minimo_reais"])
    # --- desempenho (notas) ---------------------------------------------------------------
    g, d = rede.sql_rede_enem()
    con.sql(f"""CREATE OR REPLACE TEMP TABLE notas_base AS
        SELECT ano, origem, co_municipio_prova, co_municipio_esc, {g} AS rede_grupo, tp_st_conclusao,
          CASE WHEN nu_nota_cn > 0 AND nu_nota_cn <= 1000 THEN nu_nota_cn END AS cn,
          CASE WHEN nu_nota_ch > 0 AND nu_nota_ch <= 1000 THEN nu_nota_ch END AS ch,
          CASE WHEN nu_nota_lc > 0 AND nu_nota_lc <= 1000 THEN nu_nota_lc END AS lc,
          CASE WHEN nu_nota_mt > 0 AND nu_nota_mt <= 1000 THEN nu_nota_mt END AS mt,
          CASE WHEN nu_nota_redacao BETWEEN 0 AND 1000 THEN nu_nota_redacao END AS redacao,
          ((nu_nota_cn = 0)::INT + (nu_nota_ch = 0)::INT + (nu_nota_lc = 0)::INT + (nu_nota_mt = 0)::INT) AS zeros_obj
        FROM {ALL} WHERE origem IN ('microdados', 'resultados')
          AND (origem = 'resultados' OR {recortes.sql_enem_em('tp_st_conclusao')})""")
    cols = ", ".join(
        [f"COUNT({a}) AS n_{a}, AVG({a}) AS media_{a}" for a in AREAS]
        + ["100.0 * AVG((redacao = 0)::INT) FILTER (WHERE redacao IS NOT NULL) AS pct_redacao_zero",
           "SUM(zeros_obj) AS n_nota_zero_invalidada", "COUNT(*) AS n"])
    anyvalid = "(cn IS NOT NULL OR ch IS NOT NULL OR lc IS NOT NULL OR mt IS NOT NULL OR redacao IS NOT NULL)"
    # recorte: 2023 filtrado por tp_st_conclusao; 2024+ so ha EM garantido para quem tem escola (Censo)
    rec_todas = "CASE WHEN origem = 'microdados' THEN 'EM_tp_st_conclusao' ELSE 'sem_restricao_EM' END"
    rec_rede = "CASE WHEN origem = 'microdados' THEN 'EM_tp_st_conclusao' ELSE 'EM_via_escola_censo' END"
    partes = []
    for visao, mun in (("desempenho_prova", "co_municipio_prova"), ("desempenho_escola", "co_municipio_esc")):
        partes.append(f"""SELECT '{visao}' AS visao, {mun} AS co_municipio, ano, 'todas' AS rede_grupo, {rec_todas if visao == 'desempenho_prova' else rec_rede} AS recorte, {cols}
                          FROM notas_base WHERE {anyvalid} AND {mun} IS NOT NULL GROUP BY ALL""")
        partes.append(f"""SELECT '{visao}' AS visao, {mun} AS co_municipio, ano, rede_grupo, {rec_rede} AS recorte, {cols}
                          FROM notas_base WHERE {anyvalid} AND {mun} IS NOT NULL AND rede_grupo IS NOT NULL GROUP BY ALL""")
    notas = con.sql(" UNION ALL ".join(partes)).df()
    # para desempenho_escola 'todas' = linhas COM municipio da escola (ja garantido pelo filtro de mun); em 2024+ so resultados com escola
    out = pd.concat([perfil, notas], ignore_index=True)
    out["co_municipio"] = out["co_municipio"].map(chaves.co_municipio_7)
    out["ano"] = out["ano"].astype(int)
    return out


def enem_suprimir(df: pd.DataFrame) -> pd.DataFrame:
    m = n_min("agg_enem_municipio")
    df = df.copy()
    df["suprimido"] = df["n"].fillna(0) < m
    perfil_cols = ["pct_renda_pc_le_1_5_ponto_medio", "pct_certamente_le_1_5", "pct_possivelmente_le_1_5", "pct_acima_1_5",
                   "mediana_renda_pc_sm", "mediana_renda_pc_reais"]
    for c in perfil_cols:  # renda: base propria = n_renda_valida
        df.loc[df["n_renda_valida"].fillna(m) < m, c] = np.nan
    for c in ["n_feminino", "n_masculino"]:
        df.loc[df["suprimido"] & (df["visao"] == "perfil_prova"), c] = np.nan
    df.loc[df["n_tp_escola_valido"].fillna(m) < m, "pct_publica_tp_escola"] = np.nan
    for a in AREAS:  # media por area so com >= n_min notas validas dessa area
        df.loc[df[f"n_{a}"].fillna(m) < m, f"media_{a}"] = np.nan
    df.loc[df["visao"] != "perfil_prova", "pct_redacao_zero"] = df["pct_redacao_zero"].where(df["n_redacao"].fillna(0) >= m)
    df.loc[df["suprimido"], [c for c in df.columns if c.startswith("media_") or c.startswith("pct_")]] = np.nan
    STATS["agg_enem_municipio"] = {"linhas": len(df), "suprimidas": int(df["suprimido"].sum()), "n_min": m,
                                   "por_visao": df.groupby("visao")["suprimido"].agg(["size", "sum"]).to_dict("index")}
    return df


# ---------------------------------------------------------------------- Ideb / Saeb
def prof_escola() -> pd.DataFrame:
    d = pd.read_parquet(INT / "ideb_escola.parquet")
    d = rede.aplicar_rede(d, "ideb")
    d["co_entidade"] = d["co_entidade"].map(chaves.co_entidade_8)
    d["co_municipio"] = d["co_municipio"].map(chaves.co_municipio_7)
    keep = ["co_entidade", "etapa", "ano", "co_municipio", "uf", "rede", "rede_grupo", "rede_detalhe", "no_escola",
            "nota_saeb_lp", "nota_saeb_mt", "nota_saeb_padronizada", "ideb", "indicador_rendimento", "taxa_aprovacao"]
    d = d[keep].copy()
    d["n"] = pd.array([pd.NA] * len(d), dtype="Int64")  # Ideb nao informa n de alunos
    d["suprimido"] = d[["nota_saeb_lp", "nota_saeb_mt", "ideb"]].isna().all(axis=1)  # ND do INEP
    STATS["agg_proficiencia_escola"] = {"linhas": len(d), "suprimidas": int(d["suprimido"].sum()), "n_min": "heranca INEP (ND)"}
    return d


def prof_municipio() -> pd.DataFrame:
    d = pd.read_parquet(INT / "ideb_municipio.parquet")
    d = rede.aplicar_rede(d, "ideb")
    d["co_municipio"] = d["co_municipio"].map(chaves.co_municipio_7)
    keep = ["co_municipio", "etapa", "ano", "uf", "rede", "rede_grupo", "rede_detalhe", "nota_saeb_lp", "nota_saeb_mt",
            "nota_saeb_padronizada", "ideb", "indicador_rendimento", "taxa_aprovacao"]
    d = d[keep].copy()
    d["n"] = pd.array([pd.NA] * len(d), dtype="Int64")
    d["suprimido"] = d[["nota_saeb_lp", "nota_saeb_mt", "ideb"]].isna().all(axis=1)
    STATS["agg_proficiencia_municipio"] = {"linhas": len(d), "suprimidas": int(d["suprimido"].sum()), "n_min": "heranca INEP (ND)"}
    return d


def prof_uf() -> pd.DataFrame:
    s = rede.aplicar_rede(pd.read_parquet(INT / "saeb_escola.parquet"), "saeb")
    s = s.assign(w_lp=s["n_alunos"].where(s["proficiencia_lp"].notna()), w_inse=s["n_alunos_inse"])
    def agg(g):
        wl = g["w_lp"].fillna(0)
        wi = g["w_inse"].fillna(0)
        return pd.Series({
            "n_escolas": len(g), "n_escolas_com_proficiencia": int(g["proficiencia_lp"].notna().sum()),
            "n": int(g["n_alunos"].fillna(0).sum()),
            "proficiencia_lp_media": np.average(g["proficiencia_lp"].fillna(0), weights=wl) if wl.sum() else np.nan,
            "proficiencia_mt_media": np.average(g["proficiencia_mt"].fillna(0), weights=wl) if wl.sum() else np.nan,
            "inse_aluno_medio": np.average(g["inse_aluno_medio"].fillna(0), weights=wi) if wi.sum() else np.nan,
            "n_alunos_inse": int(wi.sum())})
    out = s.groupby(["uf", "etapa", "ano", "rede_grupo"], dropna=True).apply(agg, include_groups=False).reset_index()
    out["n"] = out["n"].astype("int64")
    return suprimir(out, "agg_proficiencia_uf", "n", ["proficiencia_lp_media", "proficiencia_mt_media", "inse_aluno_medio"])


# ----------------------------------------------------------------------- medalhas
def medalhas() -> tuple[pd.DataFrame, dict]:
    enr = INT / "medalhistas_enriquecido.parquet"
    exigidas = {"olimpiada", "ano", "nivel", "modalidade", "medalha", "rede", "co_municipio", "id_aluno"}
    usa_enr = False
    if enr.exists():
        e = pd.read_parquet(enr)
        usa_enr = exigidas <= set(e.columns)
    info = {"fonte": "medalhistas_enriquecido.parquet" if usa_enr else "medalhistas.parquet (nome+UF normalizados, exato + fuzzy de chaves.py)"}
    if usa_enr:
        m = e
        info["sem_municipio"] = int(m["co_municipio"].isna().sum())
    else:
        m = chaves.anexar_co_municipio(pd.read_parquet(INT / "medalhistas.parquet"), "municipio_nome", "uf")
        info["sem_municipio"] = int(m["co_municipio"].isna().sum())
        info["match"] = m["match_municipio"].value_counts().to_dict()
        m["id_aluno"] = pd.NA
    info["linhas_entrada"] = len(m)
    m = recortes.anexar_etapa(m)
    m = rede.aplicar_rede(m, "medalhistas")
    m = m[m["co_municipio"].notna()].copy()
    m["co_municipio"] = m["co_municipio"].map(chaves.co_municipio_7)
    m["etapa"] = m["etapa"].fillna("indefinida")
    m["rede_grupo"] = m["rede_grupo"].fillna("desconhecida")
    chave = ["co_municipio", "ano", "olimpiada", "medalha", "etapa", "rede_grupo"]
    g = m.groupby(chave).agg(n=("medalha", "size"), n_alunos_unicos=("id_aluno", "nunique"),
                              no_escopo_ef2_em=("no_escopo_ef2_em", "first")).reset_index()
    if not usa_enr:
        g["n_alunos_unicos"] = pd.array([pd.NA] * len(g), dtype="Int64")
    g["ano"] = g["ano"].astype(int)
    g = suprimir(g, "agg_medalhas_municipio", "n", ["n_alunos_unicos"])
    g["n_publicavel"] = g["n"].where(~g["suprimido"])  # n so e exposto quando >= n_min
    info["linhas_saida"] = len(g)
    return g, info


# --------------------------------------------------------------------------- asserts
CHAVES = {
    "agg_enem_municipio": ["visao", "co_municipio", "ano", "rede_grupo"],
    "agg_proficiencia_escola": ["co_entidade", "etapa", "ano"],
    "agg_proficiencia_municipio": ["co_municipio", "etapa", "ano", "rede"],
    "agg_proficiencia_uf": ["uf", "etapa", "ano", "rede_grupo"],
    "agg_medalhas_municipio": ["co_municipio", "ano", "olimpiada", "medalha", "etapa", "rede_grupo"],
}
PROIBIDAS = {"nome", "nome_norm", "nome_hash", "aluno", "escola_nome", "municipio_nome"}


def validar(nome: str, df: pd.DataFrame) -> dict:
    ch = CHAVES[nome]
    assert not df.duplicated(ch).any(), f"{nome}: chave duplicada {ch}"
    assert not (set(df.columns) & PROIBIDAS), f"{nome}: coluna com possivel nome de aluno"
    if "co_municipio" in df:
        assert df["co_municipio"].dropna().str.fullmatch(r"\d{7}").all(), f"{nome}: co_municipio fora de 7 digitos"
    if "co_entidade" in df:
        assert df["co_entidade"].dropna().str.fullmatch(r"\d{8}").all(), f"{nome}: co_entidade fora de 8 digitos"
    assert df["ano"].map(type).eq(int).all() or str(df["ano"].dtype).startswith("int")
    return {"linhas": len(df), "chave": ", ".join(ch), "nulos_pct": df.isna().mean().round(3).to_dict()}


def main() -> None:
    con = duckdb.connect()
    con.execute("SET preserve_insertion_order=false")
    tabelas = {}
    enem = enem_suprimir(enem_municipio(con))
    tabelas["agg_enem_municipio"] = enem
    tabelas["agg_proficiencia_escola"] = prof_escola()
    tabelas["agg_proficiencia_municipio"] = prof_municipio()
    tabelas["agg_proficiencia_uf"] = prof_uf()
    med, info_med = medalhas()
    tabelas["agg_medalhas_municipio"] = med
    schema = {}
    for nome, df in tabelas.items():
        schema[nome] = validar(nome, df)
        df.to_parquet(INT / f"{nome}.parquet", index=False)
        print(nome, schema[nome]["linhas"], "linhas |", STATS.get(nome))
    STATS["medalhas_info"] = info_med
    import docs_agregacoes
    docs_agregacoes.gerar(tabelas, schema, STATS, info_med)


if __name__ == "__main__":
    main()
