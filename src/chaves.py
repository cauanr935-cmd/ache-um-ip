"""T2.1/T2.2 - Chaves e normalizacao de texto compartilhadas pela Fase 3.

API estavel (usada por varios modulos):
  normalizar_texto(s)            -> caixa alta, sem acentos/pontuacao, siglas expandidas
  normalizar_nome_municipio(s)   -> igual, sem expansao de siglas escolares
  co_municipio_7(x), co_entidade_8(x) -> padroniza chaves como str com zeros a esquerda
  anexar_co_municipio(df, col_municipio, col_uf, dim=None, fuzzy=True) -> df + co_municipio (7 dig) + match_municipio
                                 ('exato' | 'fuzzy' | 'ambiguo' | 'sem_match'); pares fuzzy em df.attrs["pares_fuzzy"]
  nome_nucleo(s)                 -> nome da escola sem palavras genericas (para guarda anti-falso-positivo)
  normalizar_nome_pessoa(s)      -> nome de aluno normalizado (sem acentos, sem particulas)
  auditar_chaves()               -> audita formato das chaves em data/interim (levanta AssertionError)
"""
import re
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process
from unidecode import unidecode

from caminhos import RAIZ  # noqa: E402  (ACHE_RAIZ configura a raiz)
DIM_MUN = RAIZ / "data/interim/dim_municipio_base.parquet"

# siglas (token inteiro) -> expansao. "EM" so e expandido no INICIO do nome (ambiguo com Ensino Medio).
SIGLAS = {
    "EE": "ESCOLA ESTADUAL", "EEEF": "ESCOLA ESTADUAL ENSINO FUNDAMENTAL",
    "EEEFM": "ESCOLA ESTADUAL ENSINO FUNDAMENTAL MEDIO", "EEEM": "ESCOLA ESTADUAL ENSINO MEDIO",
    "EEF": "ESCOLA ESTADUAL ENSINO FUNDAMENTAL", "EEM": "ESCOLA ESTADUAL ENSINO MEDIO",
    "EMEF": "ESCOLA MUNICIPAL ENSINO FUNDAMENTAL", "EMEI": "ESCOLA MUNICIPAL EDUCACAO INFANTIL",
    "EMEIEF": "ESCOLA MUNICIPAL EDUCACAO INFANTIL ENSINO FUNDAMENTAL",
    "EMEB": "ESCOLA MUNICIPAL EDUCACAO BASICA", "EMEFM": "ESCOLA MUNICIPAL ENSINO FUNDAMENTAL MEDIO",
    "CIEP": "CENTRO INTEGRADO EDUCACAO PUBLICA", "CEF": "CENTRO ENSINO FUNDAMENTAL",
    "CEM": "CENTRO ENSINO MEDIO", "CETI": "CENTRO ENSINO TEMPO INTEGRAL",
    "COL": "COLEGIO", "COLEG": "COLEGIO", "ESC": "ESCOLA", "EST": "ESTADUAL", "ESTAD": "ESTADUAL",
    "MUN": "MUNICIPAL", "MUNIC": "MUNICIPAL", "FED": "FEDERAL", "PART": "PARTICULAR",
    "PROF": "PROFESSOR", "PROFA": "PROFESSORA", "DR": "DOUTOR", "DRA": "DOUTORA", "CEL": "CORONEL",
    "STA": "SANTA", "STO": "SANTO", "INST": "INSTITUTO", "IF": "INSTITUTO FEDERAL",
    "EF": "ENSINO FUNDAMENTAL", "EMI": "ENSINO MEDIO INTEGRADO", "FUND": "FUNDAMENTAL",
    "EREM": "ESCOLA REFERENCIA ENSINO MEDIO", "ECIT": "ESCOLA CIDADA INTEGRAL TECNICA", "CE": "COLEGIO ESTADUAL",
    "MUL": "MUNICIPAL", "ENG": "ENGENHEIRO", "UNID": "UNIDADE", "GEN": "GENERAL", "EXERC": "EXERCITO",
    "SEN": "SENADOR", "GOV": "GOVERNADOR", "DEP": "DEPUTADO", "PRES": "PRESIDENTE", "DESEMB": "DESEMBARGADOR",
    "ENS": "ENSINO", "FUN": "FUNDAMENTAL", "NS": "NOSSA SENHORA", "SRA": "SENHORA", "SR": "SENHOR",
}
_SIGLAS_INICIO = {"EM": "ESCOLA MUNICIPAL"}
_PREPOSICOES = {"DE", "DA", "DO", "DAS", "DOS", "E"}


def _basico(s) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)) or s is pd.NA:
        return ""
    t = unidecode(str(s)).upper()
    t = re.sub(r"[^A-Z0-9 ]+", " ", t)  # pontuacao vira espaco
    return re.sub(r"\s+", " ", t).strip()


def _juntar_letras_soltas(tokens: list[str]) -> list[str]:
    """'E M E F INSTITUTO' -> ['EMEF', 'INSTITUTO'] (sequencias de 2+ letras isoladas no INICIO do nome)."""
    i = 0
    while i < len(tokens) and len(tokens[i]) == 1 and tokens[i].isalpha():
        i += 1
    return (["".join(tokens[:i])] + tokens[i:]) if i >= 2 else tokens


def _juntar_letras_finais(tokens: list[str]) -> list[str]:
    """'... PROF E M' -> [..., 'PROF', 'EM'] (2+ letras isoladas no FIM; nao expande: EM e ambiguo)."""
    j = len(tokens)
    while j > 0 and len(tokens[j - 1]) == 1 and tokens[j - 1].isalpha():
        j -= 1
    return (tokens[:j] + ["".join(tokens[j:])]) if len(tokens) - j >= 2 and j > 0 else tokens


def normalizar_texto(s) -> str:
    """Normalizacao para matching de nomes de escola/aluno."""
    toks = _juntar_letras_finais(_juntar_letras_soltas(_basico(s).split()))
    out = []
    for i, t in enumerate(toks):
        if i == 0 and t in _SIGLAS_INICIO:
            out.append(_SIGLAS_INICIO[t])
        else:
            out.append(SIGLAS.get(t, t))
    return re.sub(r"\s+", " ", " ".join(out)).strip()


def normalizar_nome_municipio(s) -> str:
    t = _basico(s)
    return re.sub(r"\s+", " ", re.sub(r"\b(DE|DA|DO|DAS|DOS|D)\b", " ", t)).strip() if t else ""


def co_municipio_7(x) -> str | None:
    if x is None or pd.isna(x):
        return None
    d = re.sub(r"\D", "", str(x).split(".")[0])
    return d.zfill(7) if d and len(d) <= 7 else None


def co_entidade_8(x) -> str | None:
    if x is None or pd.isna(x):
        return None
    d = re.sub(r"\D", "", str(x).split(".")[0])
    return d.zfill(8) if d and len(d) <= 8 else None


def chave_municipio(dim: pd.DataFrame | None = None) -> pd.DataFrame:
    dim = pd.read_parquet(DIM_MUN) if dim is None else dim
    d = dim[["co_municipio", "no_municipio", "uf"]].copy()
    d["_k"] = d["no_municipio"].map(normalizar_nome_municipio)
    return d


def anexar_co_municipio(df: pd.DataFrame, col_municipio: str, col_uf: str, dim: pd.DataFrame | None = None,
                        fuzzy: bool = True) -> pd.DataFrame:
    """Casa (nome do municipio normalizado, UF) com dim_municipio_base. Devolve co_municipio e match_municipio:
    'exato' | 'fuzzy' (mesma UF, limiar alto + margem; pares em df.attrs['pares_fuzzy']) | 'ambiguo' | 'sem_match'."""
    d = chave_municipio(dim)
    dup = d.duplicated(["_k", "uf"], keep=False)
    unico = d[~dup].set_index(["_k", "uf"])["co_municipio"]
    out = df.copy()
    ks = pd.MultiIndex.from_arrays([out[col_municipio].map(normalizar_nome_municipio), out[col_uf].astype("string").str.upper().str.strip()])
    out["co_municipio"] = pd.Series(unico.reindex(ks).to_numpy(), index=out.index, dtype="string")
    amb = set(map(tuple, d.loc[dup, ["_k", "uf"]].to_numpy()))
    sem = out["co_municipio"].isna().to_numpy()
    out["match_municipio"] = "exato"
    out.loc[sem, "match_municipio"] = ["ambiguo" if k in amb else "sem_match" for k in ks[sem]]
    pares = []
    if fuzzy and sem.any():
        pend = {k for k in ks[sem] if k not in amb}
        achados = _fuzzy_municipio(sorted(pend), d)
        for (k, uf), (co, nome_dim, sc) in achados.items():
            pares.append({"municipio_norm": k, "uf": uf, "co_municipio": co, "municipio_dim": nome_dim, "score": sc})
        if achados:
            cod = pd.Series([achados.get(k, (None,))[0] for k in ks], index=out.index, dtype="string")
            hit = out["co_municipio"].isna() & cod.notna() & out["match_municipio"].eq("sem_match")
            out.loc[hit, "co_municipio"] = cod[hit]
            out.loc[hit, "match_municipio"] = "fuzzy"
    out.attrs["pares_fuzzy"] = pd.DataFrame(pares, columns=["municipio_norm", "uf", "co_municipio", "municipio_dim", "score"])
    return out


# ----------------------------------------------------------------- nucleo / pessoa
_GENERICOS = {
    "ESCOLA", "ESTADUAL", "MUNICIPAL", "FEDERAL", "PARTICULAR", "PRIVADA", "PUBLICA", "ENSINO", "FUNDAMENTAL", "MEDIO",
    "INFANTIL", "EDUCACAO", "BASICA", "COLEGIO", "CENTRO", "INTEGRADO", "INSTITUTO", "TECNICO", "PROFISSIONAL",
    "PROFESSOR", "PROFESSORA", "DOUTOR", "DOUTORA", "E", "DE", "DA", "DO", "DAS", "DOS", "EM", "EF", "EEF", "EEM", "EMEF",
    "EE", "CE", "CM", "EB", "ESC", "UNIDADE", "UNIDADE", "ANEXO", "TEMPO", "INTEGRAL", "NIVEL", "GRAU", "1O", "2O", "CAMPUS", "NA", "O", "A",
}


def nome_nucleo(s) -> str:
    """Nome da escola sem palavras genericas (tipo/rede/etapa); se sobrar nada, devolve o nome normalizado."""
    toks = normalizar_texto(s).split()
    core = [t for t in toks if t not in _GENERICOS and not (len(t) == 1 and t.isalpha())]
    return " ".join(core) if core else " ".join(toks)


def normalizar_nome_pessoa(s) -> str:
    t = _basico(s)
    return re.sub(r"\s+", " ", re.sub(r"\b(DE|DA|DO|DAS|DOS|E)\b", " ", t)).strip()


# ------------------------------------------------------- municipio: fallback fuzzy
_FOLD = str.maketrans({"Z": "S", "J": "G", "Y": "I", "K": "C", "W": "V", "H": ""})


def _dobrar(s: str) -> str:
    """Dobra grafias foneticas para comparar nomes de municipio (BRAZOPOLIS ~ BRASOPOLIS, ITAPAJE ~ ITAPAGE)."""
    t = s.translate(_FOLD)
    t = t.replace("PH", "F").replace("LL", "L")
    return re.sub(r"(.)\1+", r"\1", t)


FUZZY_MIN = 92.0     # similaridade minima (rapidfuzz.fuzz.ratio) apos dobra fonetica
FUZZY_MARGEM = 4.0   # distancia minima para o 2o melhor candidato (senao fica sem_match)


def _fuzzy_municipio(pares_sem_match, d: pd.DataFrame) -> dict:
    """{(k, uf): (co_municipio, nome_dim, score)} para pares sem match exato; so mesma UF, alto limiar e margem."""
    achados = {}
    por_uf = {uf: g for uf, g in d.groupby("uf")}
    for k, uf in pares_sem_match:
        g = por_uf.get(uf)
        if g is None or not k:
            continue
        alvos = [_dobrar(x) for x in g["_k"]]
        res = process.extract(_dobrar(k), alvos, scorer=fuzz.ratio, limit=2)
        if not res:
            continue
        best = res[0]
        segundo = res[1][1] if len(res) > 1 else 0.0
        if best[1] >= FUZZY_MIN and best[1] - segundo >= FUZZY_MARGEM:
            row = g.iloc[best[2]]
            achados[(k, uf)] = (row["co_municipio"], row["no_municipio"], round(float(best[1]), 1))
    return achados


# ------------------------------------------------------------------- auditoria
def auditar_chaves(interim: Path | None = None) -> pd.DataFrame:
    """Audita o formato das chaves reais nas bases de data/interim; levanta AssertionError se algo estiver errado.
    Saeb: id_escola_saeb/id_municipio_saeb sao MASCARAS (nao sao chaves INEP/IBGE) e so tem o formato checado."""
    import duckdb

    interim = interim or (RAIZ / "data/interim")
    esperado = {  # arquivo -> {coluna: (regex, nulo_permitido)}
        "enem_all": {"co_municipio_prova": (r"\d{7}", False), "co_municipio_esc": (r"\d{7}", True), "co_escola": (r"\d{8}", True)},
        "saeb_escola": {"id_escola_saeb": (r"\d{8}", False), "id_municipio_saeb": (r"\d{7}", False)},
        "ideb_escola": {"co_entidade": (r"\d{8}", False), "co_municipio": (r"\d{7}", False)},
        "ideb_municipio": {"co_municipio": (r"\d{7}", False)},
        "dim_municipio_base": {"co_municipio": (r"\d{7}", False)},
        "dim_escola_base": {"co_entidade": (r"\d{8}", False), "co_municipio": (r"\d{7}", False)},
    }
    linhas = []
    for arq, cols in esperado.items():
        f = f"'{interim / (arq + '.parquet')}'"
        tipos = dict(duckdb.sql(f"SELECT column_name, column_type FROM (DESCRIBE SELECT * FROM {f})").fetchall())
        for col, (rx, nulo_ok) in cols.items():
            assert tipos[col] == "VARCHAR", f"{arq}.{col} deveria ser string, e {tipos[col]}"
            n, nulos, ruins = duckdb.sql(
                f"SELECT COUNT(*), COUNT(*) FILTER (WHERE {col} IS NULL), "
                f"COUNT(*) FILTER (WHERE {col} IS NOT NULL AND NOT regexp_full_match({col}, '{rx}')) FROM {f}").fetchone()
            assert ruins == 0, f"{arq}.{col}: {ruins} valores fora do formato {rx}"
            assert nulo_ok or nulos == 0, f"{arq}.{col}: {nulos} nulos"
            linhas.append({"base": arq, "coluna": col, "formato": rx, "linhas": n, "nulos": nulos, "fora_do_formato": ruins})
    for arq in ("enem_all", "saeb_escola", "ideb_escola", "ideb_municipio", "medalhistas"):
        f = f"'{interim / (arq + '.parquet')}'"
        tipos = dict(duckdb.sql(f"SELECT column_name, column_type FROM (DESCRIBE SELECT * FROM {f})").fetchall())
        assert tipos["ano"] in ("INTEGER", "BIGINT", "SMALLINT"), f"{arq}.ano deveria ser inteiro"
    # unicidade das dimensoes
    for arq, col in (("dim_municipio_base", "co_municipio"), ("dim_escola_base", "co_entidade")):
        n, k = duckdb.sql(f"SELECT COUNT(*), COUNT(DISTINCT {col}) FROM '{interim / (arq + '.parquet')}'").fetchone()
        assert n == k, f"{arq}.{col} nao e unico"
    # integridade referencial (municipios e escolas reais presentes nas dimensoes)
    ref = [("ideb_escola.co_municipio", "ideb_escola", "co_municipio", "dim_municipio_base", "co_municipio"),
           ("dim_escola_base.co_municipio", "dim_escola_base", "co_municipio", "dim_municipio_base", "co_municipio"),
           ("ideb_municipio.co_municipio", "ideb_municipio", "co_municipio", "dim_municipio_base", "co_municipio"),
           ("enem_all.co_municipio_prova", "enem_all", "co_municipio_prova", "dim_municipio_base", "co_municipio"),
           ("enem_all.co_municipio_esc", "enem_all", "co_municipio_esc", "dim_municipio_base", "co_municipio"),
           ("ideb_escola.co_entidade", "ideb_escola", "co_entidade", "dim_escola_base", "co_entidade")]
    for nome, a, ca, b, cb in ref:
        orf = duckdb.sql(f"SELECT COUNT(DISTINCT {ca}) FROM '{interim / (a + '.parquet')}' WHERE {ca} IS NOT NULL AND {ca} NOT IN "
                         f"(SELECT {cb} FROM '{interim / (b + '.parquet')}')").fetchone()[0]
        assert orf == 0, f"{nome}: {orf} chaves sem correspondente em {b}.{cb}"
    return pd.DataFrame(linhas)
