"""T2.4 - Deduplicacao de alunos entre anos/olimpiadas e contagem de medalhas acumuladas (RF 2.5).

Identidade = nome normalizado + co_municipio + escola (co_entidade se vinculada 'auto'; senao escola_norm).
Nao funde homonimos/grafias divergentes: so conta e documenta a colisao provavel.
Saidas (INTERIM; contem nomes, a T2.10 aplica o hash): data/interim/medalhistas_enriquecido.parquet (todas as linhas)
e data/interim/aluno_dedup.parquet (uma linha por aluno_key). Pre-requisito: python src/linkage.py
Uso: python src/dedup.py
"""
import hashlib
from pathlib import Path

import pandas as pd

import linkage

from caminhos import RAIZ  # noqa: E402  (ACHE_RAIZ configura a raiz)
RESULTADO = RAIZ / "data/processed/linkage_resultado.parquet"
SAIDA_LINHAS = RAIZ / "data/interim/medalhistas_enriquecido.parquet"
SAIDA_ALUNOS = RAIZ / "data/interim/aluno_dedup.parquet"
CHAVE_STR = ["olimpiada", "escola_norm", "co_municipio", "uf", "rede_grp"]
PREMIO = ["olimpiada", "ano", "modalidade", "nivel", "medalha"]  # unidade de premiacao
MEDALHA_COL = {"Ouro": "n_ouro", "Prata": "n_prata", "Bronze": "n_bronze", "Menção Honrosa": "n_mencao"}


def _id(txt: str) -> str:
    return hashlib.blake2b(txt.encode("utf-8"), digest_size=8).hexdigest()  # id deterministico (NAO e o hash da T2.10)


def enriquecer() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    m = linkage.preparar_medalhistas()
    res = pd.read_parquet(RESULTADO)[CHAVE_STR + ["link_status", "link_score", "co_entidade", "motivo"]]
    n0 = len(m)
    m = m.merge(res, on=CHAVE_STR, how="left")
    assert len(m) == n0 and m["row_id"].is_unique, "merge com linkage alterou o numero de linhas"
    assert m["link_status"].isin(linkage.STATUS).all(), "link_status fora do dominio"
    m.loc[m["link_status"] != "auto", "co_entidade"] = None  # revisao/sem_match: candidatos ficam so na fila de revisao
    m["escola_ref"] = m["co_entidade"].where(m["co_entidade"].notna(), "N:" + m["escola_norm"])
    base = m["nome_norm"] + "|" + m["co_municipio"].fillna("UF:" + m["uf"].fillna("")) + "|" + m["escola_ref"]
    m["aluno_key"] = base.map(_id)
    m["linha_duplicada"] = m.duplicated(["aluno_key"] + PREMIO, keep="first")

    # premiacoes distintas por aluno
    prem = m[~m["linha_duplicada"]]
    cont = prem.pivot_table(index="aluno_key", columns="medalha", values="row_id", aggfunc="count", fill_value=0)
    cont = cont.rename(columns=MEDALHA_COL)
    for c in MEDALHA_COL.values():
        if c not in cont:
            cont[c] = 0
    g = prem.groupby("aluno_key")
    resumo = pd.DataFrame({"n_premios": g.size(), "n_olimpiadas": g["olimpiada"].nunique(), "n_anos": g["ano"].nunique(),
                           "primeiro_ano": g["ano"].min(), "ultimo_ano": g["ano"].max()}).join(cont[list(MEDALHA_COL.values())])
    resumo["n_medalhas"] = resumo[["n_ouro", "n_prata", "n_bronze"]].sum(axis=1)  # exclui mencao honrosa
    m = m.merge(resumo.reset_index(), on="aluno_key", how="left")

    alunos = (m.sort_values(["ano", "row_id"]).groupby("aluno_key", as_index=False)
              .agg(nome_norm=("nome_norm", "first"), co_municipio=("co_municipio", "first"), uf=("uf", "first"),
                   escola_norm=("escola_norm", "first"), escola_ref=("escola_ref", "first"),
                   co_entidade=("co_entidade", "first"), link_status=("link_status", "first"))
              .merge(resumo.reset_index(), on="aluno_key", how="left"))
    assert alunos["aluno_key"].is_unique

    # colisao provavel: mesmo nome+municipio com mais de uma escola_ref
    gm = alunos.assign(_m=alunos["co_municipio"].fillna("UF:" + alunos["uf"].fillna(""))).groupby(["nome_norm", "_m"])
    n_ref = gm["aluno_key"].transform("size")
    colide = alunos[n_ref > 1][["aluno_key", "nome_norm", "co_municipio", "uf"]].copy()
    # mesmo ano + mesma olimpiada (+ modalidade/nivel) em escolas diferentes => homonimo quase certo
    chaves_col = set(colide["aluno_key"])
    sub = m[m["aluno_key"].isin(chaves_col)].assign(_m=lambda d: d["co_municipio"].fillna("UF:" + d["uf"].fillna("")))
    mesmo_ano = sub.groupby(["nome_norm", "_m", "olimpiada", "ano", "modalidade", "nivel"], dropna=False)["aluno_key"].nunique()
    n_homonimo_certo = int((mesmo_ano > 1).groupby(level=[0, 1]).any().sum())
    stats = {
        "linhas": len(m), "alunos_unicos": len(alunos), "linhas_duplicadas_exatas": int(m["linha_duplicada"].sum()),
        "alunos_com_mais_de_1_premio": int((alunos["n_premios"] > 1).sum()),
        "alunos_em_mais_de_1_ano": int((alunos["n_anos"] > 1).sum()),
        "alunos_em_mais_de_1_olimpiada": int((alunos["n_olimpiadas"] > 1).sum()),
        "grupos_nome_municipio_com_varias_escolas": int((gm["aluno_key"].size() > 1).sum()),
        "alunos_nesses_grupos": int(len(colide)),
        "grupos_com_homonimo_certo_mesmo_ano": n_homonimo_certo,
        "max_premios_um_aluno": int(alunos["n_premios"].max()),
        "nome_norm_vazio": int((m["nome_norm"] == "").sum()),
    }
    return m, alunos, stats


def main() -> None:
    m, alunos, stats = enriquecer()
    m.to_parquet(SAIDA_LINHAS, index=False)
    alunos.to_parquet(SAIDA_ALUNOS, index=False)
    for k, v in stats.items():
        print(f"{k}: {v}")
    print(alunos["n_premios"].value_counts().sort_index().head(8).to_dict())


if __name__ == "__main__":
    main()

