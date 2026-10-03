"""T2.10-T2.11 - Tabelas analiticas finais em data/processed/ + asserts + docs/qualidade_processed.md.

Tabelas: dim_municipio, dim_escola, dim_aluno, fato_desempenho (formato longo), fato_medalhas.
LGPD: nenhuma coluna de nome de aluno; ids por hash SHA-256 com sal (config/lgpd.yaml, fora do Git) - src/lgpd.py.
Entradas: data/interim/* (inclusive medalhistas_enriquecido/aluno_dedup, que TEM nomes e nao vai para processed).
Reexecutar: python src/processed.py   (depois de coleta, linkage, dedup e agregacoes).
"""
from pathlib import Path

import duckdb
import pandas as pd
import yaml

import lgpd
import recortes
import rede

from caminhos import RAIZ  # noqa: E402  (ACHE_RAIZ configura a raiz)
I = RAIZ / "data/interim"
P = RAIZ / "data/processed"
SUPR = yaml.safe_load((RAIZ / "config/supressao.yaml").read_text(encoding="utf-8"))
N_MIN = int(SUPR["n_min_por_tabela"].get("agg_medalhas_municipio", SUPR["n_min_padrao"]))

CHAVES = {
    "dim_municipio": ["co_municipio"],
    "dim_escola": ["co_entidade"],
    "dim_aluno": ["id_aluno_hash"],
    "fato_medalhas": ["id_registro_hash"],
    "fato_desempenho": ["nivel_geo", "entidade_id", "fonte", "etapa", "ano", "rede_grupo", "rede_detalhe", "recorte", "metrica"],
}


# ------------------------------------------------------------------ dimensoes
def dim_municipio() -> pd.DataFrame:
    return pd.read_parquet(I / "dim_municipio_base.parquet")


def dim_escola() -> pd.DataFrame:
    d = pd.read_parquet(I / "dim_escola_base.parquet")
    d = rede.aplicar_rede(d, "ideb")  # rede Federal/Estadual/Municipal/Privada -> rede_grupo / rede_detalhe
    d["provisoria"] = True  # vem do Ideb, nao do Censo Escolar (T1.13 pendente)
    return d.drop(columns=["rede_publica"])


# ------------------------------------------------------------------ medalhistas (LGPD)
def medalhistas_pseudonimizados() -> tuple[pd.DataFrame, pd.DataFrame]:
    sal = lgpd.carregar_sal()
    m = pd.read_parquet(I / "medalhistas_enriquecido.parquet")
    # hash pedido na T2.10 (nome normalizado + ano + olimpiada): NAO e unico (mesmo nome em niveis/modalidades diferentes)
    m["id_nome_ano_olimp_hash"] = lgpd.hash_registro(m["nome_norm"], m["ano"], m["olimpiada"], sal)
    # id unico e estavel do registro: campos do registro + indice de ocorrencia entre linhas identicas
    campos = ["nome_norm", "ano", "olimpiada", "modalidade", "nivel", "medalha", "posicao", "escola_norm", "municipio_nome", "uf"]
    ocorr = m.groupby(campos, dropna=False).cumcount()
    m["id_registro_hash"] = [lgpd.sha256(*vals, o, sal=sal) for vals, o in zip(
        m[campos].astype(object).where(m[campos].notna(), "").itertuples(index=False, name=None), ocorr)]
    m["id_aluno_hash"] = lgpd.hash_aluno(m["aluno_key"], sal)
    m = recortes.anexar_etapa(m)
    m = rede.aplicar_rede(m, "medalhistas")
    al = pd.read_parquet(I / "aluno_dedup.parquet")
    al["id_aluno_hash"] = lgpd.hash_aluno(al["aluno_key"], sal)
    return m, al


def dim_aluno(al: pd.DataFrame) -> pd.DataFrame:
    cols = ["id_aluno_hash", "co_municipio", "uf", "co_entidade", "escola_norm", "link_status", "n_premios", "n_olimpiadas",
            "n_anos", "primeiro_ano", "ultimo_ano", "n_ouro", "n_prata", "n_bronze", "n_mencao", "n_medalhas"]
    return al[cols].copy()  # sem nome, sem nome_norm, sem aluno_key


def fato_medalhas(m: pd.DataFrame) -> pd.DataFrame:
    cols = ["id_registro_hash", "id_nome_ano_olimp_hash", "id_aluno_hash", "olimpiada", "ano", "nivel", "modalidade", "medalha", "etapa", "no_escopo_ef2_em",
            "posicao", "rede", "rede_grupo", "rede_detalhe", "co_municipio", "match_municipio", "co_entidade", "link_status",
            "link_score", "escola_norm", "linha_duplicada"]
    out = m[cols].rename(columns={"rede": "rede_publicada"}).copy()
    out["ano"] = out["ano"].astype("int16")
    return out


# ------------------------------------------------------------------ fato_desempenho (longo)
def _longo(df: pd.DataFrame, chaves: list[str], metricas: list[str]) -> pd.DataFrame:
    l = df.melt(id_vars=chaves, value_vars=metricas, var_name="metrica", value_name="valor")
    return l[l["valor"].notna() | l["suprimido"]]  # mantem celulas suprimidas (valor nulo) para o consumidor saber


def fato_desempenho(m: pd.DataFrame) -> pd.DataFrame:
    partes = []
    esc = pd.read_parquet(I / "agg_proficiencia_escola.parquet")
    esc["nivel_geo"], esc["entidade_id"], esc["fonte"], esc["recorte"] = "escola", esc["co_entidade"], "ideb", ""
    prof = ["nota_saeb_lp", "nota_saeb_mt", "nota_saeb_padronizada", "ideb", "indicador_rendimento", "taxa_aprovacao"]
    ch = ["nivel_geo", "entidade_id", "fonte", "etapa", "ano", "rede_grupo", "rede_detalhe", "recorte", "n", "suprimido"]
    partes.append(_longo(esc, ch, prof))
    mun = pd.read_parquet(I / "agg_proficiencia_municipio.parquet")
    mun["nivel_geo"], mun["entidade_id"], mun["fonte"], mun["recorte"] = "municipio", mun["co_municipio"], "ideb", ""
    partes.append(_longo(mun, ch, prof))
    uf = pd.read_parquet(I / "agg_proficiencia_uf.parquet")
    uf["nivel_geo"], uf["entidade_id"], uf["fonte"], uf["recorte"], uf["rede_detalhe"] = "uf", uf["uf"], "saeb_microdados", "", None
    partes.append(_longo(uf, ch, ["proficiencia_lp_media", "proficiencia_mt_media", "inse_aluno_medio"]))
    en = pd.read_parquet(I / "agg_enem_municipio.parquet")
    en["nivel_geo"], en["entidade_id"], en["fonte"], en["etapa"], en["rede_detalhe"] = "municipio", en["co_municipio"], "enem", "EM", None
    en["recorte"] = en["visao"] + "|" + en["recorte"]
    skip = {"visao", "co_municipio", "ano", "rede_grupo", "recorte", "n", "suprimido", "nivel_geo", "entidade_id", "fonte", "etapa", "rede_detalhe"}
    partes.append(_longo(en, ch, [c for c in en.columns if c not in skip]))
    # medalhas: n_medalhas e n_alunos_unicos por municipio x ano x olimpiada x medalha x etapa x rede (supressao n < n_min)
    g = (m[m["co_municipio"].notna()].groupby(["co_municipio", "ano", "olimpiada", "medalha", "etapa", "rede_grupo"], dropna=False)
         .agg(n=("row_id", "size"), n_alunos_unicos=("id_aluno_hash", "nunique")).reset_index())
    g["suprimido"] = g["n"] < N_MIN
    g["n_medalhas"] = g["n"].where(~g["suprimido"])
    g["n_alunos_unicos"] = g["n_alunos_unicos"].where(~g["suprimido"])
    g["nivel_geo"], g["entidade_id"], g["fonte"] = "municipio", g["co_municipio"], g["olimpiada"].str.lower()
    g["recorte"], g["rede_detalhe"] = "medalha=" + g["medalha"], None
    g["etapa"] = g["etapa"].fillna("sem_etapa")
    partes.append(_longo(g, ch, ["n_medalhas", "n_alunos_unicos"]))
    f = pd.concat(partes, ignore_index=True)
    f["etapa"] = f["etapa"].fillna("sem_etapa")
    f["no_escopo_ef2_em"] = f["etapa"].isin(recortes.ESCOPO)
    f["ano"] = f["ano"].astype("int16")
    f["n"] = f["n"].astype("Int64")
    f["valor"] = f["valor"].astype("float64")
    return f[["nivel_geo", "entidade_id", "fonte", "etapa", "ano", "rede_grupo", "rede_detalhe", "recorte", "metrica", "valor",
              "n", "suprimido", "no_escopo_ef2_em"]]


# ------------------------------------------------------------------ validacoes
def _chave_str(df: pd.DataFrame, cols: list[str]) -> pd.Series:
    return df[cols].astype("string").fillna("<NA>").agg("|".join, axis=1)


def validar(t: dict[str, pd.DataFrame], nomes_norm: set[str]) -> dict:
    r = {}
    for nome, cols in CHAVES.items():
        d = t[nome]
        assert not d[cols].isna().all(axis=1).any(), f"{nome}: chave totalmente nula"
        dup = int(_chave_str(d, cols).duplicated().sum()) if len(cols) > 1 else int(d[cols[0]].duplicated().sum())
        assert dup == 0, f"{nome}: {dup} chaves duplicadas em {cols}"
        r[f"{nome}_dup"] = dup
    for nome in ("dim_municipio",):
        assert t[nome]["co_municipio"].str.fullmatch(r"\d{7}").all()
    assert t["dim_escola"]["co_entidade"].str.fullmatch(r"\d{8}").all()
    for nome in ("dim_aluno", "fato_medalhas"):
        d = t[nome]
        assert d["co_municipio"].dropna().str.fullmatch(r"\d{7}").all(), nome
        assert d["co_entidade"].dropna().str.fullmatch(r"\d{8}").all(), nome
    # integridade referencial
    mun, esc = set(t["dim_municipio"]["co_municipio"]), set(t["dim_escola"]["co_entidade"])
    for nome in ("dim_escola", "dim_aluno", "fato_medalhas"):
        fk = t[nome]["co_municipio"].dropna()
        assert fk.isin(mun).all(), f"{nome}: co_municipio fora de dim_municipio"
    for nome in ("dim_aluno", "fato_medalhas"):
        fk = t[nome]["co_entidade"].dropna()
        assert fk.isin(esc).all(), f"{nome}: co_entidade fora de dim_escola"
    assert t["fato_medalhas"]["id_aluno_hash"].isin(set(t["dim_aluno"]["id_aluno_hash"])).all(), "aluno sem dim_aluno"
    fd = t["fato_desempenho"]
    assert fd.loc[fd["nivel_geo"] == "municipio", "entidade_id"].isin(mun).all(), "fato_desempenho: municipio fora da dim"
    assert fd.loc[fd["nivel_geo"] == "escola", "entidade_id"].isin(esc).all(), "fato_desempenho: escola fora da dim"
    # supressao: celula suprimida nao pode ter valor
    assert fd.loc[fd["suprimido"], "valor"].isna().all(), "celula suprimida com valor"
    # LGPD: sem colunas de nome de pessoa e sem valor textual igual a algum nome normalizado conhecido
    for nome, d in t.items():
        proib = [c for c in d.columns if c.startswith("nome") or c in {"nome_norm", "aluno_key", "cpf"}]
        assert not proib, f"{nome}: colunas proibidas {proib}"
    hits = {}
    for nome, d in t.items():
        for c in d.columns:
            if str(d[c].dtype) in ("str", "string", "object") and nome != "fato_desempenho":
                if d[c].nunique() > 5_000_000:
                    continue
                vals = set(d[c].dropna().unique())
                h = vals & nomes_norm
                if h:
                    hits[f"{nome}.{c}"] = len(h)
    r["lgpd_hits_exatos"] = hits
    return r


def main() -> None:
    P.mkdir(parents=True, exist_ok=True)
    m, al = medalhistas_pseudonimizados()
    t = {"dim_municipio": dim_municipio(), "dim_escola": dim_escola(), "dim_aluno": dim_aluno(al),
         "fato_medalhas": fato_medalhas(m)}
    t["fato_desempenho"] = fato_desempenho(m)
    nomes = set(m["nome_norm"].dropna().unique())
    res = validar(t, nomes)
    for nome, d in t.items():
        d.to_parquet(P / f"{nome}.parquet", index=False)
        print(nome, d.shape)
    print("validacao:", res)
    import docs_processed
    docs_processed.gerar(t, res, m)


if __name__ == "__main__":
    main()
