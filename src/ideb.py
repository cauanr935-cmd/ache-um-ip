"""T1.7 - Ideb (INEP, divulgacao 2025) -> data/interim/ideb_escola.parquet e ideb_municipio.parquet.

Planilhas largas (uma coluna por indicador x ano) -> formato longo: uma linha por
(etapa, ano, escola|municipio, rede). Etapas: EF2 (anos finais, 6o-9o) e EM (ensino medio regular).
Tambem traz a taxa de aprovacao e o indicador de rendimento (parte da "Taxa de Rendimento").
'-' e 'ND', 'ND*', 'ND***' (sem dado/nao divulgado) viram nulo; virgula decimal e convertida;
asterisco em valor numerico (media por metodo alternativo, extravio de provas) e removido e mantido. Chaves: co_entidade 8 digitos, co_municipio 7 digitos (str).
"""
import re
from pathlib import Path

import pandas as pd

from caminhos import RAIZ  # noqa: E402  (ACHE_RAIZ configura a raiz)
BASE = RAIZ / "data/raw/inep/indicadores/ideb_2025"
INTERIM = RAIZ / "data/interim"

ARQUIVOS = {  # (nivel, etapa) -> pasta
    ("escola", "EF2"): "divulgacao_anos_finais_escolas_2025",
    ("escola", "EM"): "divulgacao_ensino_medio_escolas_2025",
    ("municipio", "EF2"): "divulgacao_anos_finais_municipios_2025",
    ("municipio", "EM"): "divulgacao_ensino_medio_municipios_2025",
}
METRICAS = {
    "APROVACAO_SI_4": "taxa_aprovacao", "APROVACAO_1": "taxa_aprovacao_s1", "APROVACAO_2": "taxa_aprovacao_s2",
    "APROVACAO_3": "taxa_aprovacao_s3", "APROVACAO_4": "taxa_aprovacao_s4",
    "INDICADOR_REND": "indicador_rendimento", "NOTA_MATEMATICA": "nota_saeb_mt",
    "NOTA_PORTUGUES": "nota_saeb_lp", "NOTA_MEDIA": "nota_saeb_padronizada",
    "OBSERVADO": "ideb", "PROJECAO": "ideb_projecao",
}
RE_COL = re.compile(r"^VL_(" + "|".join(METRICAS) + r")_(\d{4})$")
RE_COL_APROV = re.compile(r"^VL_APROVACAO_(\d{4})_(SI_4|[1-4])$")  # aprovacao: ano no meio do nome


def _casa(c: str):
    """(chave de METRICAS, ano) ou None."""
    m = RE_COL.match(c)
    if m:
        return m.groups()
    m = RE_COL_APROV.match(c)
    return (f"APROVACAO_{m.group(2)}", m.group(1)) if m else None
SEM_DADO = {"-", "--", "", "ND", "ND***"}  # ND = nao disponivel


def ler(nivel: str, etapa: str) -> pd.DataFrame:
    xlsx = next((BASE / ARQUIVOS[(nivel, etapa)]).rglob("*.xlsx"))
    df = pd.read_excel(xlsx, header=9, dtype=str)
    df = df.loc[:, [c for c in df.columns if not str(c).startswith("Unnamed")]]
    chave = ["CO_MUNICIPIO"] + (["ID_ESCOLA"] if nivel == "escola" else [])
    df = df[df[chave[-1]].fillna("").str.fullmatch(r"\d{7,8}")]  # descarta notas de rodape
    return df


def para_longo(df: pd.DataFrame, nivel: str, etapa: str, ocorrencias: dict) -> pd.DataFrame:
    ids = ["SG_UF", "CO_MUNICIPIO", "NO_MUNICIPIO", "REDE"] + (["ID_ESCOLA", "NO_ESCOLA"] if nivel == "escola" else [])
    cols = {c: _casa(c) for c in df.columns if _casa(c)}
    longo = df.melt(id_vars=ids, value_vars=list(cols), var_name="col", value_name="valor")
    longo["metrica"] = longo["col"].map(lambda c: METRICAS[cols[c][0]])
    longo["ano"] = longo["col"].map(lambda c: int(cols[c][1]))
    v = longo["valor"].str.strip()
    ocorrencias["valores_numericos_com_asterisco (calculo alternativo, mantidos)"] = (
        ocorrencias.get("valores_numericos_com_asterisco (calculo alternativo, mantidos)", 0)
        + int((v.str.fullmatch(r"[\d.,]+\*+")).sum()))
    v = v.str.rstrip("*").str.replace(",", ".", regex=False)  # asterisco = nota de rodape; virgula decimal
    num = pd.to_numeric(v, errors="coerce")
    estranhos = v[num.isna() & v.notna() & ~v.isin(SEM_DADO)].value_counts()
    for k, n in estranhos.items():
        ocorrencias[f"nao_numerico:{k}"] = ocorrencias.get(f"nao_numerico:{k}", 0) + int(n)
    longo["valor"] = num
    longo = longo.dropna(subset=["valor"])  # '-' = sem dado
    chave = ids + ["ano"]
    largo = longo.set_index(chave + ["metrica"])["valor"].unstack("metrica").reset_index()
    largo.columns.name = None
    largo = largo.rename(columns={"SG_UF": "uf", "CO_MUNICIPIO": "co_municipio", "NO_MUNICIPIO": "no_municipio",
                                  "REDE": "rede", "ID_ESCOLA": "co_entidade", "NO_ESCOLA": "no_escola"})
    largo.insert(0, "etapa", etapa)
    return largo


def main() -> None:
    ocorrencias: dict = {}
    for nivel in ("escola", "municipio"):
        partes = []
        for etapa in ("EF2", "EM"):
            print(f"lendo {nivel} {etapa} ...", flush=True)
            partes.append(para_longo(ler(nivel, etapa), nivel, etapa, ocorrencias))
        out = pd.concat(partes, ignore_index=True)
        out["co_municipio"] = out["co_municipio"].str.zfill(7)
        if nivel == "escola":
            out["co_entidade"] = out["co_entidade"].str.zfill(8)
        ordem = (["etapa", "ano", "co_entidade", "co_municipio", "uf", "rede", "no_escola", "no_municipio"]
                 if nivel == "escola" else ["etapa", "ano", "co_municipio", "uf", "rede", "no_municipio"])
        ordem += [m for m in METRICAS.values() if m in out.columns]
        out = out[ordem].sort_values(ordem[1:4 if nivel == "escola" else 3]).reset_index(drop=True)
        chave = ["etapa", "ano", "rede"] + (["co_entidade"] if nivel == "escola" else ["co_municipio"])
        assert not out.duplicated(chave).any(), f"chave duplicada em {nivel}"
        destino = INTERIM / f"ideb_{nivel}.parquet"
        out.to_parquet(destino, index=False)
        print(destino, out.shape)
    print("ocorrencias:", ocorrencias or "nenhuma")


if __name__ == "__main__":
    main()
