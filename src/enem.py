"""T1.1-T1.3 - ENEM: CSV bruto (ISO-8859-1, ';') -> data/interim/enem_{ano}.parquet via DuckDB.

O layout muda entre anos:
  * 2023: arquivo unico MICRODADOS (notas, escola, perfil e questionario na mesma linha).
  * 2024+: PARTICIPANTES (perfil, Q001-Q023, sem escola/notas) e RESULTADOS (notas, escola),
    NAO relacionaveis entre si (NU_SEQUENCIAL != NU_INSCRICAO, ver dicionario oficial).
    Por isso cada ano 2024+ gera linhas de duas "origens" no mesmo parquet.
  * CO_ESCOLA mascarado (prefixo 6) para escolas com < 10 participantes -> co_escola_mascarado.
  * Renda familiar: Q006 em 2023; Q007 a partir de 2024 (Q006 virou "possui renda?").
Saida: esquema unico (SAIDA_COLS); colunas inexistentes na origem ficam nulas.
"""
from pathlib import Path

import duckdb

from caminhos import RAIZ  # noqa: E402  (ACHE_RAIZ configura a raiz)
RAW = RAIZ / "data/raw/inep"
INTERIM = RAIZ / "data/interim"
ANOS_ALVO = range(2016, 2027)  # 2026+: acrescente o ano aqui e confira o layout (FONTES)

# coluna de saida -> (expressao SQL sobre as colunas brutas, tipo)
_TXT = lambda c: f"NULLIF(TRIM({c}), '')"  # noqa: E731
_COD = lambda c, n: f"LPAD({_TXT(c)}, {n}, '0')"  # noqa: E731
_NUM = lambda c, t: f"TRY_CAST({_TXT(c)} AS {t})"  # noqa: E731

SAIDA_COLS = {
    "ano": "INTEGER", "origem": "VARCHAR", "co_escola": "VARCHAR", "co_escola_mascarado": "BOOLEAN",
    "co_municipio_esc": "VARCHAR", "sg_uf_esc": "VARCHAR",
    "co_municipio_prova": "VARCHAR", "sg_uf_prova": "VARCHAR",
    "tp_escola": "TINYINT", "tp_sexo": "VARCHAR", "tp_st_conclusao": "TINYINT",
    "tp_dependencia_adm_esc": "TINYINT",
    "nu_nota_cn": "DOUBLE", "nu_nota_ch": "DOUBLE", "nu_nota_lc": "DOUBLE",
    "nu_nota_mt": "DOUBLE", "nu_nota_redacao": "DOUBLE",
    "q005": "SMALLINT", "q006": "VARCHAR", "renda_familiar_faixa": "VARCHAR",
}

_ESCOLA = {
    "co_escola": lambda: _COD("CO_ESCOLA", 8),
    "co_municipio_esc": lambda: _COD("CO_MUNICIPIO_ESC", 7), "sg_uf_esc": lambda: _TXT("SG_UF_ESC"),
    "tp_dependencia_adm_esc": lambda: _NUM("TP_DEPENDENCIA_ADM_ESC", "TINYINT"),
}
_PROVA = {
    "co_municipio_prova": lambda: _COD("CO_MUNICIPIO_PROVA", 7), "sg_uf_prova": lambda: _TXT("SG_UF_PROVA"),
}
_NOTAS = {f"nu_nota_{a}": (lambda a=a: _NUM(f"NU_NOTA_{a.upper()}", "DOUBLE"))
          for a in ("cn", "ch", "lc", "mt", "redacao")}
_PERFIL = {
    "tp_sexo": lambda: _TXT("TP_SEXO"), "tp_st_conclusao": lambda: _NUM("TP_ST_CONCLUSAO", "TINYINT"),
    "q005": lambda: _NUM("Q005", "SMALLINT"),
}

# ano -> lista de (origem, arquivo relativo a RAW/microdados_enem_{ano}/.../DADOS, mapeamento, coluna da renda)
FONTES = {
    2023: [("microdados", "MICRODADOS_ENEM_2023.csv",
            {**{k: v for k, v in _ESCOLA.items() if k != "co_escola"},  # 2023 nao tem CO_ESCOLA
             **_PROVA, **_NOTAS, **_PERFIL, "tp_escola": lambda: _NUM("TP_ESCOLA", "TINYINT")},
            "Q006")],
}
for _a in (2024, 2025, 2026):  # 2026: ASSUME o mesmo layout de 2024-25; confira o dicionario quando sair
    FONTES[_a] = [
        ("participantes", f"PARTICIPANTES_{_a}.csv", {**_PROVA, **_PERFIL}, "Q007"),
        ("resultados", f"RESULTADOS_{_a}.csv", {**_ESCOLA, **_PROVA, **_NOTAS}, None),
    ]


def localizar(ano: int, arquivo: str) -> Path | None:
    achados = list((RAW / f"microdados_enem_{ano}").rglob(arquivo))
    return achados[0] if achados else None


def anos_presentes() -> dict[int, list[str]]:
    """Anos do alvo com todos os CSVs esperados no disco."""
    return {a: [f[1] for f in FONTES[a]] for a in ANOS_ALVO
            if a in FONTES and all(localizar(a, f[1]) for f in FONTES[a])}


def _select(ano: int, origem: str, csv: Path, mapa: dict, col_renda: str | None) -> str:
    cols = []
    for nome, tipo in SAIDA_COLS.items():
        if nome == "ano":
            expr = str(ano)
        elif nome == "origem":
            expr = f"'{origem}'"
        elif nome == "q006":
            expr = _TXT("Q006") if origem != "resultados" else "NULL"
        elif nome == "renda_familiar_faixa":
            expr = _TXT(col_renda) if col_renda else "NULL"
        elif nome == "co_escola_mascarado":
            # INEP substitui o codigo por mascara 6xxxxxxx quando a escola tem < 10 participantes
            expr = f"(LEFT({_TXT('CO_ESCOLA')}, 1) = '6')" if "co_escola" in mapa else "NULL"
        elif nome in mapa:
            expr = mapa[nome]()
        else:
            expr = "NULL"
        cols.append(f"CAST({expr} AS {tipo}) AS {nome}")
    leitura = (f"read_csv('{csv}', delim=';', header=true, all_varchar=true, "
               f"encoding='latin-1', strict_mode=false)")
    return f"SELECT {', '.join(cols)} FROM {leitura}"


def converter_ano(ano: int, con: duckdb.DuckDBPyConnection | None = None) -> Path:
    con = con or duckdb.connect()
    con.execute("SET preserve_insertion_order=false")
    partes = []
    for origem, arquivo, mapa, col_renda in FONTES[ano]:
        csv = localizar(ano, arquivo)
        if csv is None:
            raise FileNotFoundError(f"{arquivo} ausente em microdados_enem_{ano}")
        partes.append(_select(ano, origem, csv, mapa, col_renda))
    destino = INTERIM / f"enem_{ano}.parquet"
    INTERIM.mkdir(parents=True, exist_ok=True)
    con.execute(f"COPY ({' UNION ALL '.join(partes)}) TO '{destino}' (FORMAT parquet, COMPRESSION zstd)")
    return destino


def consolidar(anos: list[int]) -> Path:
    destino = INTERIM / "enem_all.parquet"
    arqs = ", ".join(f"'{INTERIM / f'enem_{a}.parquet'}'" for a in anos)
    duckdb.connect().execute(
        f"COPY (SELECT * FROM read_parquet([{arqs}])) TO '{destino}' (FORMAT parquet, COMPRESSION zstd)")
    return destino


def main(anos: list[int] | None = None) -> None:
    """Converte os anos presentes em disco (todos, ou so os de `anos`) e consolida enem_all.parquet com todos os anos ja convertidos."""
    presentes = {a: v for a, v in anos_presentes().items() if anos is None or a in anos}
    for ano in presentes:
        print(f"convertendo {ano} ...", flush=True)
        converter_ano(ano)
    todos = sorted(int(p.stem.split("_")[1]) for p in INTERIM.glob("enem_20??.parquet"))
    consolidar(todos)
    print("anos convertidos:", list(presentes), "| enem_all:", todos)


if __name__ == "__main__":
    main()
