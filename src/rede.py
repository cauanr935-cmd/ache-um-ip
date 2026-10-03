"""T2.6 - Flag de rede e filtro de escola publica, unico para todas as bases.

rede_grupo   : 'publica' | 'privada' | None (desconhecida)
rede_detalhe : 'federal' | 'estadual' | 'municipal' | 'privada' | 'outra' | None
Mapeamentos (MAPAS) servem tanto para pandas (aplicar_rede) quanto para SQL/DuckDB (sql_rede_enem).
"""
import pandas as pd

# (grupo, detalhe)
MAPAS = {
    # ENEM tp_dependencia_adm_esc (Censo Escolar)
    "enem_dependencia": {1: ("publica", "federal"), 2: ("publica", "estadual"), 3: ("publica", "municipal"),
                         4: ("privada", "privada")},
    # ENEM 2023 tp_escola (autodeclarado; 1 = nao respondeu). Detalhe da rede publica e desconhecido.
    "enem_tp_escola": {2: ("publica", None), 3: ("privada", "privada")},
    "saeb": {"publica": ("publica", None), "privada": ("privada", "privada")},
    "ideb": {"Federal": ("publica", "federal"), "Estadual": ("publica", "estadual"),
             "Municipal": ("publica", "municipal"), "Pública": ("publica", None),
             "Privada": ("privada", "privada")},
    # OBMEP: F federal, E estadual, M municipal, P privada. C = "como publicado" (significado nao documentado
    # pela fonte; ~530 linhas) -> tratado como 'outra' com grupo desconhecido. OBI nao publica rede.
    "medalhistas": {"F": ("publica", "federal"), "E": ("publica", "estadual"), "M": ("publica", "municipal"),
                    "P": ("privada", "privada"), "C": (None, "outra")},
}
BASES = {"saeb": "saeb", "ideb": "ideb", "medalhistas": "medalhistas"}


def _dict_map(s: pd.Series, mapa: dict) -> tuple[pd.Series, pd.Series]:
    g = s.map(lambda v: mapa.get(v, (None, None))[0])
    d = s.map(lambda v: mapa.get(v, (None, None))[1])
    return g, d


def aplicar_rede(df: pd.DataFrame, base: str) -> pd.DataFrame:
    """Anexa rede_grupo e rede_detalhe. base: 'saeb' (col rede), 'ideb' (col rede), 'medalhistas' (col rede),
    'enem' (cols tp_dependencia_adm_esc e tp_escola; dependencia tem prioridade)."""
    out = df.copy()
    if base == "enem":
        g1, d1 = _dict_map(out["tp_dependencia_adm_esc"], MAPAS["enem_dependencia"])
        g2, d2 = _dict_map(out["tp_escola"], MAPAS["enem_tp_escola"]) if "tp_escola" in out else (g1 * 0, d1 * 0)
        out["rede_grupo"] = g1.where(g1.notna(), g2)
        out["rede_detalhe"] = d1.where(g1.notna(), d2)
    else:
        out["rede_grupo"], out["rede_detalhe"] = _dict_map(out["rede"], MAPAS[BASES[base]])
    return out


def sql_rede_enem(dep: str = "tp_dependencia_adm_esc", esc: str = "tp_escola") -> tuple[str, str]:
    """Expressoes SQL (rede_grupo, rede_detalhe) para o ENEM, equivalentes a aplicar_rede(df, 'enem')."""
    def case(col, mapa, i):
        ws = " ".join(f"WHEN {k} THEN " + (f"'{v[i]}'" if v[i] else "NULL") for k, v in mapa.items())
        return f"CASE {col} {ws} END"
    g = f"COALESCE({case(dep, MAPAS['enem_dependencia'], 0)}, {case(esc, MAPAS['enem_tp_escola'], 0)})"
    d = (f"CASE WHEN {dep} IS NOT NULL THEN {case(dep, MAPAS['enem_dependencia'], 1)} "
         f"ELSE {case(esc, MAPAS['enem_tp_escola'], 1)} END")
    return g, d


def filtrar_publica(df: pd.DataFrame, col: str = "rede_grupo") -> pd.DataFrame:
    """Escola publica (exclui privada e desconhecida)."""
    return df[df[col] == "publica"]
