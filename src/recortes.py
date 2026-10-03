"""T2.7 - Recortes EF2/EM. Configuracao em config/recortes.yaml."""
from pathlib import Path

import pandas as pd
import yaml

from caminhos import RAIZ  # noqa: E402  (ACHE_RAIZ configura a raiz)
CFG = yaml.safe_load((RAIZ / "config/recortes.yaml").read_text(encoding="utf-8"))
ESCOPO = set(CFG["escopo"])
ENEM_TP_ST = CFG["enem"]["tp_st_conclusao_incluidos"]


def etapa_medalhista(olimpiada: str, modalidade, nivel) -> str | None:
    """etapa a partir de (olimpiada, modalidade, nivel); None se nao mapeado."""
    c = CFG["medalhistas"]
    nivel = None if nivel is None or pd.isna(nivel) else str(nivel)
    if olimpiada == "OBMEP":
        return (c["OBMEP"].get(nivel) or {}).get("etapa")
    if olimpiada == "OBI":
        mod = (modalidade or "").replace("CF-OBI ", "")
        if mod == "Universitária":
            return c["OBI"]["Universitária"]["etapa"]
        return (c["OBI"].get(mod, {}).get(nivel) or {}).get("etapa")
    return None


def anexar_etapa(med: pd.DataFrame) -> pd.DataFrame:
    """Anexa `etapa` e `no_escopo_ef2_em` a um DataFrame com olimpiada, modalidade, nivel."""
    out = med.copy()
    out["etapa"] = [etapa_medalhista(o, m, n) for o, m, n in zip(out["olimpiada"], out["modalidade"], out["nivel"])]
    out["no_escopo_ef2_em"] = out["etapa"].isin(ESCOPO)
    return out


def sql_enem_em(col: str = "tp_st_conclusao") -> str:
    """Predicado SQL do recorte EM do ENEM (origens com tp_st_conclusao: microdados/participantes)."""
    return f"{col} IN ({', '.join(map(str, ENEM_TP_ST))})"
