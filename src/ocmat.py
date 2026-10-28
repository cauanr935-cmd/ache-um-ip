"""OCMAT no formato das tabelas de medalhistas: linhas por premiado (lista) e contagem por município (mapa).

Entrada: data/interim/ocmat_premiados.parquet (src/coleta_ocmat.py). O município é casado pelo nome (UF = ES) e a escola
pelo mesmo linkage das demais olimpíadas (src/linkage.py, escolas públicas do município).
"""
import hashlib

import pandas as pd

import chaves
import linkage
import recortes
from caminhos import RAIZ

ENTRADA = RAIZ / "data/interim/ocmat_premiados.parquet"
FONTE = "https://matematicanarede.sedu.es.gov.br/ocmat/{ano}"
# Níveis que misturam séries dentro e fora do perfil do IP (7º ano ao 2º ano do médio). A tela mostra este aviso.
AVISO_NIVEL = {
    "1": "OCMAT nível 1 reúne 6º e 7º ano: pode ser aluno do 6º ano (abaixo do perfil do IP).",
    "4": "OCMAT nível 4 reúne 2ª e 3ª série do ensino médio: pode ser aluno do 3º ano (acima do perfil do IP).",
}


def carregar():
    """Devolve (medalhistas, contagem): medalhistas com as colunas do enriquecido; contagem no formato de agg_medalhas_municipio."""
    m = pd.read_parquet(ENTRADA).reset_index(drop=True)
    cfg = linkage.carregar_config()
    m = chaves.anexar_co_municipio(m, "municipio_nome", "uf")
    m["escola_norm"] = m["escola_nome"].map(chaves.normalizar_texto)
    m["rede_grp"] = "publica"
    chave = ["olimpiada", "escola_norm", "co_municipio", "uf", "rede_grp"]
    ks = m.drop_duplicates(chave)[chave]
    res = linkage.vincular(ks, pd.read_parquet(linkage.DIM_ESCOLA), cfg)
    m = m.merge(res[chave + ["link_status", "co_entidade"]], on=chave, how="left")
    m["co_entidade"] = m["co_entidade"].where(m["link_status"] == "auto")  # só vínculo automático vira INEP
    m["aluno_key"] = [hashlib.sha1(f"OCMAT|{n}|{c}|{a}".encode()).hexdigest()[:16]
                      for n, c, a in zip(m["nome"].map(chaves.normalizar_nome_pessoa), m["co_municipio"], m["ano"])]
    m["linha_duplicada"] = False
    m["fonte"] = [FONTE.format(ano=a) for a in m["ano"]]
    m["aviso"] = m["nivel"].map(AVISO_NIVEL)
    m = recortes.anexar_etapa(m)
    sem_mun = int(m["co_municipio"].isna().sum())
    print(f"OCMAT: {len(m)} premiados, {sem_mun} sem município, {int(m['co_entidade'].notna().sum())} com escola vinculada")
    m = m[m["co_municipio"].notna()].copy()
    cont = (m.groupby(["co_municipio", "ano", "olimpiada", "medalha", "etapa", "rede_grp"]).size().rename("n").reset_index()
            .rename(columns={"rede_grp": "rede_grupo"}))
    return m, cont
