"""T2.5 - Proxy de renda per capita <= 1,5 SM (ENEM). Config: config/renda.yaml; doc: docs/renda_proxy.md.

Formula: renda_pc_sm = ponto_medio_faixa(SM) / q005 (moradores). Intervalo: [lim_inf/q005, lim_sup/q005].
Classes: 'certamente_le' (max_pc <= limite), 'acima' (min_pc >= limite), senao 'possivelmente'.
"""
from pathlib import Path

import yaml

from caminhos import RAIZ  # noqa: E402  (ACHE_RAIZ configura a raiz)
CFG = yaml.safe_load((RAIZ / "config/renda.yaml").read_text(encoding="utf-8"))
LIMITE = CFG["limite_per_capita_sm"]


def faixas_values_sql() -> str:
    """Tabela VALUES (faixa, lim_inf, lim_sup, ponto_medio) para uso em joins DuckDB (lim_sup NULL = aberto)."""
    linhas = []
    for f, v in CFG["faixas"].items():
        sup = "NULL" if v["lim_sup"] is None else v["lim_sup"]
        linhas.append(f"('{f}', {v['lim_inf']}, {sup}, {v['ponto_medio']})")
    return "(VALUES " + ", ".join(linhas) + ") AS fx(faixa, lim_inf, lim_sup, pm)"


def sm_reais_sql(col_ano: str = "ano") -> str:
    ws = " ".join(f"WHEN {a} THEN {v}" for a, v in CFG["salario_minimo_reais"].items())
    return f"CASE {col_ano} {ws} END"


# colunas calculadas sobre o join com fx (q005 > 0)
EXPR_PC_PM = "fx.pm / q005"
EXPR_PC_MIN = "fx.lim_inf / q005"
EXPR_PC_MAX = "fx.lim_sup / q005"  # NULL = aberto (faixa Q)
EXPR_CLASSE = (f"CASE WHEN fx.lim_sup IS NOT NULL AND fx.lim_sup / q005 <= {LIMITE} THEN 'certamente_le' "
               f"WHEN fx.lim_inf / q005 >= {LIMITE} THEN 'acima' ELSE 'possivelmente' END")
